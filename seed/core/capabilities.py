"""Capability registry: action contract, validazione manifest, esposizione al modello.

Il modello PROPONE l'invocazione (tool calling); il registry DECIDE se invocarla:
manifest valido + audit passato + permesso concesso. Mai tool call libero.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from . import forbidden, sandbox
from .permissions import FORBIDDEN_RISK_CLASSES, RISK_CLASSES

log = logging.getLogger("seed.capabilities")

_REQUIRED_MANIFEST_KEYS = {"capability_id", "description", "input_schema",
                           "risk_class", "origin"}


@dataclass
class Capability:
    capability_id: str
    directory: Path
    manifest: dict
    state: str  # active | proposed | dormant

    @property
    def risk_class(self) -> str:
        return self.manifest.get("risk_class", "safe")

    @property
    def reason(self) -> str:
        return self.manifest.get("reason", self.manifest.get("description", ""))


def validate_manifest(manifest: dict) -> list[str]:
    errors = []
    missing = _REQUIRED_MANIFEST_KEYS - set(manifest)
    if missing:
        errors.append(f"campi mancanti: {sorted(missing)}")
    rc = manifest.get("risk_class")
    if rc in FORBIDDEN_RISK_CLASSES:
        errors.append(f"risk_class vietata: {rc}")
    elif rc not in RISK_CLASSES:
        errors.append(f"risk_class sconosciuta: {rc}")
    if manifest.get("origin") not in ("builtin", "generated"):
        errors.append("origin deve essere builtin|generated")
    return errors


class CapabilityRegistry:
    def __init__(self, memory, broker, builtin_dir: Path | None = None):
        self._memory = memory
        self._broker = broker
        self.builtin_dir = builtin_dir or (
            Path(__file__).resolve().parents[1] / "capabilities_builtin")
        self.generated_dir = forbidden.seed_data_dir() / "capabilities"
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self._caps: dict[str, Capability] = {}
        self.reload()

    # ------------------------------------------------------------------
    def reload(self) -> None:
        self._caps.clear()
        for base, origin in ((self.builtin_dir, "builtin"), (self.generated_dir, "generated")):
            if not base.exists():
                continue
            for d in sorted(p for p in base.iterdir() if p.is_dir()):
                self._load_one(d, origin)

    def _load_one(self, directory: Path, origin: str) -> None:
        mf_path = directory / "manifest.json"
        if not mf_path.exists():
            return
        try:
            manifest = json.loads(mf_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            log.error("manifest corrotto %s: %s", directory, exc)
            return
        errors = validate_manifest(manifest)
        if errors:
            log.error("manifest rifiutato %s: %s", directory, errors)
            return
        if origin == "generated":
            audit_path = directory / "AUDIT.json"
            if not audit_path.exists() or not json.loads(
                    audit_path.read_text(encoding="utf-8")).get("passed"):
                log.error("capability generata senza audit pass: %s", directory)
                return
        state = manifest.get("state", "active")
        cap = Capability(manifest["capability_id"], directory, manifest, state)
        self._caps[cap.capability_id] = cap

    # ------------------------------------------------------------------
    def active(self) -> list[Capability]:
        return [c for c in self._caps.values() if c.state == "active"]

    def get(self, capability_id: str) -> Capability | None:
        return self._caps.get(capability_id)

    def to_openai_tools(self) -> list[dict]:
        tools = []
        for cap in self.active():
            props = {k: {"type": "string", "description": str(v)}
                     for k, v in (cap.manifest.get("input_schema") or {}).items()}
            tools.append({
                "type": "function",
                "function": {
                    "name": cap.capability_id,
                    "description": cap.manifest.get("description", ""),
                    "parameters": {"type": "object", "properties": props,
                                   "required": list(props)},
                },
            })
        return tools

    # ------------------------------------------------------------------
    def invoke(self, capability_id: str, arguments: dict) -> dict:
        """Gate completo: registrata -> permesso -> sandbox -> stats. """
        cap = self._caps.get(capability_id)
        if cap is None or cap.state not in ("active", "proposed"):
            return {"error": f"capability non registrata: {capability_id}"}

        scope = arguments.get("path") or arguments.get("app") or cap.risk_class
        if not self._broker.authorize(capability_id, cap.risk_class, str(scope), cap.reason):
            self._memory.bump_capability(capability_id, success=False)
            return {"error": "permesso negato dall'utente", "denied": True}

        # capability proposte si attivano al primo uso autorizzato
        if cap.state == "proposed":
            cap.state = "active"
            cap.manifest["state"] = "active"
            (cap.directory / "manifest.json").write_text(
                json.dumps(cap.manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        result = sandbox.run_tool(cap.directory,
                                  arguments,
                                  timeout=int(cap.manifest.get("timeout", 30)))
        self._memory.bump_capability(capability_id, success=result.ok)
        self._memory.add_event("capability_invoked", {
            "capability": capability_id, "ok": result.ok, "timed_out": result.timed_out})
        if not result.ok:
            return {"error": result.stderr or "esecuzione fallita"}
        return result.output

    # ------------------------------------------------------------------
    # Forge: registrazione di una capability generata (chiamata da evolution)
    # ------------------------------------------------------------------
    def register_generated(self, manifest: dict, code: str) -> tuple[bool, list[str]]:
        errors = validate_manifest(manifest)
        if manifest.get("origin") != "generated":
            errors.append("origin deve essere 'generated'")
        if errors:
            return False, errors

        audit = sandbox.static_audit(code, needs_network=bool(manifest.get("needs_network")))
        target = self.generated_dir / manifest["capability_id"]
        if not audit.passed:
            return False, audit.violations

        target.mkdir(parents=True, exist_ok=True)
        (target / "tool.py").write_text(code, encoding="utf-8")
        manifest = {**manifest, "state": "proposed", "registered_at": time.time()}
        (target / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        dry = sandbox.dry_run(target, manifest)
        audit_record = {"passed": audit.passed and dry.ok,
                        "violations": audit.violations,
                        "dry_run_ok": dry.ok, "dry_run_stderr": dry.stderr,
                        "at": time.time()}
        (target / "AUDIT.json").write_text(
            json.dumps(audit_record, ensure_ascii=False, indent=2), encoding="utf-8")

        if not dry.ok:
            shutil.rmtree(target, ignore_errors=True)
            return False, [f"dry-run fallito: {dry.stderr}"]

        self.reload()
        self._memory.add_event("capability_forged", {"capability": manifest["capability_id"]})
        return True, []

    def prune(self, capability_id: str) -> bool:
        cap = self._caps.get(capability_id)
        if cap is None or cap.manifest.get("origin") != "generated":
            return False  # le builtin non si potano, al massimo dormono
        shutil.rmtree(cap.directory, ignore_errors=True)
        self._memory.add_event("capability_pruned", {"capability": capability_id})
        self.reload()
        return True

    def set_state(self, capability_id: str, state: str) -> None:
        cap = self._caps.get(capability_id)
        if cap and state in ("active", "dormant", "proposed"):
            cap.state = state
            cap.manifest["state"] = state
            (cap.directory / "manifest.json").write_text(
                json.dumps(cap.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
