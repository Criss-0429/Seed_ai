"""Permission broker: nessuna azione rischiosa senza autorizzazione.

Classi di rischio (doc 04):
  safe | read_safe | read_sensitive | execute | network | write | destructive

`destructive` non e' instanziabile in v0.1: il registry rifiuta i manifest che
la dichiarano e il forge non puo' generarla.

La richiesta all'utente passa per una callback UI (dialog nella webview);
in dev mode la callback e' il prompt da console.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger("seed.permissions")

RISK_CLASSES = ("safe", "read_safe", "read_sensitive", "execute", "network", "write")
FORBIDDEN_RISK_CLASSES = ("destructive",)

# politiche: quando serve chiedere
_ASK_POLICY = {
    "safe": "never",
    "read_safe": "never",
    "read_sensitive": "per_scope",   # per cartella/file, memorizzabile
    "execute": "per_scope",          # per app, memorizzabile (allowlist incrementale)
    "network": "per_capability",     # una volta per capability, revocabile
    "write": "per_operation",        # ogni volta, tranne workspace
}


@dataclass
class PermissionRequest:
    capability_id: str
    risk_class: str
    scope: str           # path, nome app, "network"
    reason: str          # il "perche'" della capability, mostrato all'utente


class PermissionBroker:
    def __init__(self, memory, ask_callback: Callable[[PermissionRequest], dict] | None = None):
        """ask_callback(request) -> {"decision": "allow"|"deny", "remember": bool}"""
        self._memory = memory
        self._ask = ask_callback or self._console_ask

    def set_ask_callback(self, cb: Callable[[PermissionRequest], dict]) -> None:
        self._ask = cb

    # ------------------------------------------------------------------
    def authorize(self, capability_id: str, risk_class: str, scope: str, reason: str) -> bool:
        if risk_class in FORBIDDEN_RISK_CLASSES:
            log.error("risk_class vietata: %s (%s)", risk_class, capability_id)
            return False
        if risk_class not in RISK_CLASSES:
            log.error("risk_class sconosciuta: %s (%s)", risk_class, capability_id)
            return False

        policy = _ASK_POLICY[risk_class]
        if policy == "never":
            return True

        grant_scope = scope if policy in ("per_scope", "per_operation") else "capability"
        # grant memorizzato?
        if policy != "per_operation":
            prev = self._memory.find_grant(capability_id, grant_scope)
            if prev == "allow":
                return True
            if prev == "deny":
                log.info("negato da grant memorizzato: %s/%s", capability_id, grant_scope)
                return False

        req = PermissionRequest(capability_id, risk_class, scope, reason)
        answer = self._ask(req)
        decision = answer.get("decision", "deny")
        remember = bool(answer.get("remember", False)) and policy != "per_operation"
        self._memory.record_grant(capability_id, grant_scope, decision, remember)
        self._memory.add_event("permission", {
            "capability": capability_id, "risk": risk_class,
            "scope_kind": grant_scope if grant_scope == "capability" else "scoped",
            "decision": decision, "remembered": remember})
        return decision == "allow"

    # ------------------------------------------------------------------
    @staticmethod
    def _console_ask(req: PermissionRequest) -> dict:
        print(f"\n[PERMESSO RICHIESTO] {req.capability_id} ({req.risk_class})")
        print(f"  scope : {req.scope}")
        print(f"  motivo: {req.reason}")
        ans = input("  consenti? [s = solo stavolta / r = ricorda / N = nega] ").strip().lower()
        if ans == "s":
            return {"decision": "allow", "remember": False}
        if ans == "r":
            return {"decision": "allow", "remember": True}
        return {"decision": "deny", "remember": ans == "nr"}
