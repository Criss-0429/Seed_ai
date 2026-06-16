"""P7.6 Connection Broker + Credential Vault, P7.7 Activation Authority (doc 19).

Sicurezza: token e credenziali vivono SOLO nel vault cifrato; ai tool/builder/
reviewer/MCP si espongono solo handle tipizzati, mai il token (no passthrough).
L'OAuth reale e' iniettato (PKCE/state/audience), non importato qui. L'attivazione
automatica e' una authority SEPARATA e fail-closed: mai auto-espansione di
autorita', effetti irreversibili sempre a conferma contestuale.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import capability_forge as cf


# ==========================================================================
# P7.6 — Credential Vault (cifrato, handle-only, niente passthrough)
# ==========================================================================
class VaultError(cf.ForgeError):
    pass


class ConnectionError_(cf.ForgeError):
    pass


@dataclass
class CredentialVault:
    """Custodisce token cifrati. Cipher iniettato (DPAPI in produzione, reversibile
    nei test). Espone SOLO handle opachi: il token non lascia mai il vault verso
    builder, reviewer, descendant o MCP generati."""
    encrypt: object = None    # callable(str)->bytes
    decrypt: object = None    # callable(bytes)->str
    _store: dict[str, dict] = field(default_factory=dict)

    def _enc(self, s: str):
        return self.encrypt(s) if self.encrypt else s.encode("utf-8")

    def _dec(self, b):
        return self.decrypt(b) if self.decrypt else b.decode("utf-8")

    def put(self, connection_id: str, token: str, *, expires_at: float | None = None) -> str:
        """Salva un token cifrato e ritorna un HANDLE opaco (mai il token)."""
        if not connection_id or not token:
            raise VaultError("connection_id e token obbligatori")
        handle = f"handle:{connection_id}"
        self._store[connection_id] = {"enc": self._enc(token), "expires_at": expires_at,
                                      "handle": handle}
        return handle

    def handle(self, connection_id: str) -> str | None:
        rec = self._store.get(connection_id)
        if rec is None:
            return None
        if rec["expires_at"] is not None and time.time() > rec["expires_at"]:
            return None
        return rec["handle"]

    def _resolve_token(self, connection_id: str) -> str:
        """USO INTERNO del broker per chiamare il servizio. NON esposto ai tool."""
        rec = self._store.get(connection_id)
        if rec is None:
            raise VaultError("nessuna credenziale")
        if rec["expires_at"] is not None and time.time() > rec["expires_at"]:
            raise VaultError("credenziale scaduta")
        return self._dec(rec["enc"])

    def revoke(self, connection_id: str) -> bool:
        return self._store.pop(connection_id, None) is not None


# Campi obbligatori che un flusso OAuth deve esporre (OAuth 2.1 + PKCE).
_OAUTH_REQUIRED = ("access_token", "code_verifier", "state", "audience")


@dataclass
class ConnectionBroker:
    """Trasforma requisiti tecnici in richieste comprensibili e gestisce il
    collegamento. Mantiene la capability in `awaiting_connection` quando non esiste
    un flusso affidabile. Non espone mai il token: solo handle tipizzati."""
    vault: CredentialVault
    audit: object = None

    def _emit(self, kind, payload):
        if self.audit:
            self.audit(kind, payload)

    def describe(self, req: cf.ConnectionRequirement) -> str:
        """Richiesta in linguaggio comprensibile (non token/scope OAuth)."""
        req.validate()
        eff = ", ".join(req.allowed_effects) or "solo lettura"
        denied = ", ".join(req.denied_effects) or "nessun effetto non dichiarato"
        return (f"{req.human_reason} SEED potra: {eff}. Non potra: {denied}. "
                f"I dati restano {req.retention}. Revoca: {req.revocation_path}.")

    def connect(self, req: cf.ConnectionRequirement, *, oauth_flow,
                granted_authority: cf.AuthorityEnvelope) -> dict:
        """Esegue il flusso OAuth INIETTATO e conserva il token nel vault. Fail-closed
        se il flusso non e' affidabile o non espone PKCE/state/audience."""
        req.validate()
        if oauth_flow is None:
            self._emit("forge_awaiting_connection", {"connection_id": req.connection_id})
            return {"state": "awaiting_connection", "reason": "no_reliable_flow"}
        result = oauth_flow(req)
        missing = [k for k in _OAUTH_REQUIRED if not (result or {}).get(k)]
        if missing:
            return {"state": "awaiting_connection", "reason": f"oauth_incomplete:{missing}"}
        handle = self.vault.put(req.connection_id, result["access_token"],
                                expires_at=result.get("expires_at"))
        self._emit("forge_connected", {"connection_id": req.connection_id})
        # ritorna l'handle e l'autorita' concessa, MAI il token.
        return {"state": "connected", "handle": handle,
                "granted_authority": granted_authority}

    def typed_handle(self, connection_id: str) -> dict | None:
        h = self.vault.handle(connection_id)
        return None if h is None else {"connection_id": connection_id, "handle": h}

    def revoke(self, connection_id: str) -> bool:
        ok = self.vault.revoke(connection_id)
        self._emit("forge_connection_revoked", {"connection_id": connection_id, "ok": ok})
        return ok


# ==========================================================================
# P7.7 — Activation Authority + autopilot (separata, fail-closed)
# ==========================================================================
class ActivationError(cf.ForgeError):
    pass


@dataclass
class ActivationAuthority:
    """Autorita' di attivazione SEPARATA da builder/connector/reviewer/evaluator.
    Auto-attiva solo se TUTTI i gate sono verdi e l'autorita' richiesta e'
    sottoinsieme di quella concessa. Nuova autorita' -> `awaiting_connection`.
    Effetti irreversibili/alto impatto -> sempre conferma contestuale, mai auto."""
    auto_activation_enabled: bool = False
    audit: object = None

    def _emit(self, kind, payload):
        if self.audit:
            self.audit(kind, payload)

    def decide(self, *, report: cf.CapabilityEvaluationReport,
               manifest: cf.CapabilityManifestV2,
               granted_authority: cf.AuthorityEnvelope,
               shadow_ok: bool, canary_ok: bool,
               connector_drift: bool = False,
               has_irreversible: bool = False) -> dict:
        report.validate()
        manifest.validate()
        blockers: list[str] = []
        if not report.passed:
            blockers.append("eval_not_passed")
        if report.manifest_digest != manifest.build_digest:
            blockers.append("digest_mismatch")
        if connector_drift:
            blockers.append("connector_drift")
        if not shadow_ok:
            blockers.append("shadow_not_green")
        if not canary_ok:
            blockers.append("canary_not_green")

        subset = cf.authority_subset(manifest.requested_authority, granted_authority)
        if not subset["within_authority"]:
            # nuova autorita' richiesta: attende consenso umano, mai auto-espansione.
            self._emit("forge_awaiting_connection",
                       {"capability_id": manifest.capability_id,
                        "escalations": subset["escalations"]})
            return {"state": "awaiting_connection", "auto_activated": False,
                    "reason": "authority_escalation", "escalations": subset["escalations"]}

        if has_irreversible:
            # mai automatico: conferma contestuale obbligatoria.
            return {"state": "shadow", "auto_activated": False,
                    "reason": "irreversible_requires_confirmation"}

        if blockers:
            return {"state": "shadow", "auto_activated": False,
                    "reason": "open_blockers", "blockers": sorted(blockers)}

        if not self.auto_activation_enabled:
            return {"state": "canary", "auto_activated": False,
                    "reason": "auto_activation_disabled"}

        self._emit("forge_activated", {"capability_id": manifest.capability_id})
        return {"state": "active", "auto_activated": True,
                "reason": "within_authority_all_green"}

    def confirm_irreversible(self, *, owner_confirmed: bool) -> dict:
        """Conferma contestuale per un effetto irreversibile/alto impatto. Non
        delegabile permanentemente: vale per la singola azione."""
        return {"allowed": bool(owner_confirmed),
                "reason": "owner_confirmed" if owner_confirmed else "confirmation_required"}
