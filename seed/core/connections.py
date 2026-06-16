"""P3 conversational connections for governed runtime boundaries.

This module translates explicit natural-language requests into reviewable,
typed proposals. It never installs tools, promotes mutations, or executes a
task graph without a separate owner confirmation carrying the proposal id.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from .llm import parse_json_object
from .skills import DelegationRequest, SkillError, TaskGraph, TaskNode

_TOOL_REQUEST = re.compile(
    r"^\s*(?:crea|costruisci|genera)\s+(?:uno\s+)?(?:strumento|tool)\s+che\s+(.+)$",
    re.IGNORECASE,
)
_PLAN_REQUEST = re.compile(
    r"^\s*(?:pianifica|crea\s+un\s+piano\s+per)\s+(.+)$", re.IGNORECASE
)
_CONFIRM_TOOL = re.compile(r"^\s*conferma\s+tool\s+([a-z0-9_.-]+)\s*$", re.IGNORECASE)
_CONFIRM_PLAN = re.compile(r"^\s*(?:esegui|conferma)\s+piano\s+([a-z0-9_.-]+)\s*$",
                           re.IGNORECASE)
_CANARY_REQUEST = re.compile(r"^\s*avvia\s+canary\s+([a-z0-9_.-]+)\s*$", re.IGNORECASE)
_CONFIRM_CANARY = re.compile(r"^\s*conferma\s+canary\s+([a-z0-9_.-]+)\s*$",
                             re.IGNORECASE)
_HEARTBEAT = re.compile(
    r"^\s*(?:mostra\s+|qual\s+e\s+|dimmi\s+)?(?:lo\s+)?stato\s+(?:del\s+)?heartbeat\s*$",
    re.IGNORECASE,
)

_TOOL_SPEC_PROMPT = """Converti la richiesta redatta in una specifica tool sicura.
Rispondi SOLO JSON:
{"capability_id":"id.sicuro","description":"breve","input_schema":{"nome":"descrizione"},
"risk_class":"safe|read_sensitive|network|execute","needs_network":false}
Non generare codice. Non usare rischio destructive o critical."""

_TOOL_CODE_PROMPT = """Genera una tool Python isolabile dalla specifica.
Legge un oggetto JSON da stdin e scrive un oggetto JSON su stdout.
Supporta __dry_run__ senza effetti. Niente shell, subprocess, eval, exec o accesso
fuori workspace. Rispondi SOLO JSON: {"code":"..."}."""

_PLAN_PROMPT = """Converti la richiesta redatta in un Task Graph usando SOLO il catalogo.
Rispondi SOLO JSON:
{"nodes":[{"node_id":"n1","capability_id":"...","depends_on":[],
"arguments":{"campo":"valore"}}]}
Non inventare capability. Usa dipendenze acicliche."""


@dataclass
class ToolProposal:
    proposal_id: str
    request: str
    spec: dict


@dataclass
class PlanProposal:
    proposal_id: str
    graph: TaskGraph
    arguments: dict[str, dict]
    effects: tuple[str, ...]


class CoreConnections:
    def __init__(self, *, tool_llm, registry, tool_builder, subagent,
                 daemon_review, advance_canary, design_review=None, audit=None):
        self.tool_llm = tool_llm
        self.registry = registry
        self.tool_builder = tool_builder
        self.subagent = subagent
        self.daemon_review = daemon_review
        self.advance_canary = advance_canary
        self.design_review = design_review or (lambda _spec, _candidate: "inconclusive")
        self.audit = audit or (lambda kind, payload: None)
        self._tools: dict[str, ToolProposal] = {}
        self._plans: dict[str, PlanProposal] = {}
        self._canaries: set[str] = set()

    def handle(self, text: str) -> str | None:
        if _HEARTBEAT.match(text):
            self.audit("p3_heartbeat_review", {})
            return json.dumps(self.daemon_review(), ensure_ascii=False, indent=2)
        if match := _CONFIRM_TOOL.match(text):
            return self._confirm_tool(match.group(1))
        if match := _TOOL_REQUEST.match(text):
            return self._propose_tool(match.group(1))
        if match := _CONFIRM_PLAN.match(text):
            return self._execute_plan(match.group(1))
        if match := _PLAN_REQUEST.match(text):
            return self._propose_plan(match.group(1))
        if match := _CONFIRM_CANARY.match(text):
            return self._confirm_canary(match.group(1))
        if match := _CANARY_REQUEST.match(text):
            return self._propose_canary(match.group(1))
        return None

    @staticmethod
    def _id(prefix: str, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
        return f"{prefix}-{digest}"

    def _chat_json(self, system: str, user: str) -> dict:
        response = self.tool_llm.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            redacted=True, temperature=0.0, response_json=True)
        return parse_json_object(response.text)

    def _propose_tool(self, request: str) -> str:
        try:
            spec = self._chat_json(_TOOL_SPEC_PROMPT, request)
            manifest = {**spec, "origin": "generated"}
            errors = self.tool_builder.registry_validate(manifest)
            if errors:
                raise ValueError("; ".join(errors))
        except Exception as exc:
            return f"Tool non proposta: specifica non valida o provider indisponibile ({exc})."
        proposal_id = self._id("tool", json.dumps(spec, sort_keys=True))
        self._tools[proposal_id] = ToolProposal(proposal_id, request, spec)
        self.audit("p3_tool_proposed", {"proposal_id": proposal_id,
                                       "risk_class": spec.get("risk_class", "")})
        return (
            f"Specifica tool `{proposal_id}`:\n"
            f"{json.dumps(spec, ensure_ascii=False, indent=2)}\n"
            f"Nessun codice generato. Per confermare lo scope: conferma tool {proposal_id}"
        )

    def _confirm_tool(self, proposal_id: str) -> str:
        proposal = self._tools.pop(proposal_id, None)
        if proposal is None:
            return "Proposta tool inesistente o gia consumata."
        try:
            generated = self._chat_json(
                _TOOL_CODE_PROMPT, json.dumps(proposal.spec, ensure_ascii=False))
            candidate = self.tool_builder.stage(
                {**proposal.spec, "origin": "generated"}, str(generated["code"]))
        except Exception as exc:
            return f"Generazione isolata fallita: {exc}"
        design_verdict = self.design_review(proposal.spec, candidate)
        design_passed = design_verdict == "pass"
        review_path = candidate.candidate_dir / "REVIEW.json"
        if review_path.is_file():
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["design_review_passed"] = design_passed
            review["installation_proposed"] = design_passed
            review_path.write_text(
                json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
        self.audit("p3_tool_reviewed", {
            "proposal_id": proposal_id, "audit_passed": candidate.audit_passed,
            "test_passed": candidate.test_passed, "design_verdict": design_verdict,
        })
        return (
            f"Tool `{candidate.capability_id}` generata e testata in isolamento.\n"
            f"Audit: {candidate.audit_passed}; test: {candidate.test_passed}; "
            f"design review: {design_verdict}; violazioni: {list(candidate.violations)}.\n"
            "Non installata. L'installazione resta una proposta separata con approvazione owner."
        )

    def _propose_plan(self, request: str) -> str:
        allowed = frozenset(self.subagent.allowed)
        catalog = [
            {"capability_id": cap.capability_id, "description": cap.manifest.get("description", ""),
             "risk_class": cap.risk_class}
            for cap in self.registry.active() if cap.capability_id in allowed
        ]
        try:
            data = self._chat_json(
                _PLAN_PROMPT, json.dumps({"request": request, "catalog": catalog},
                                         ensure_ascii=False))
            nodes = tuple(TaskNode(
                str(item["node_id"]), str(item["capability_id"]),
                tuple(str(dep) for dep in item.get("depends_on", [])))
                for item in data.get("nodes", []))
            graph = TaskGraph(nodes)
            graph.validate(allowed_capabilities=allowed)
            arguments = {
                str(item["node_id"]): dict(item.get("arguments", {}))
                for item in data.get("nodes", [])
            }
            effects = tuple(self.registry.get(node.capability_id).risk_class for node in nodes)
            self._validate_effects(nodes)
        except Exception as exc:
            return f"Piano non proposto: {exc}"
        proposal_id = self._id("plan", json.dumps(data, sort_keys=True))
        self._plans[proposal_id] = PlanProposal(proposal_id, graph, arguments, effects)
        self.audit("p3_plan_proposed", {"proposal_id": proposal_id, "nodes": len(nodes)})
        preview = [{"node": node.node_id, "capability": node.capability_id,
                    "depends_on": list(node.depends_on)}
                   for node in nodes]
        return (
            f"Anteprima piano `{proposal_id}`:\n"
            f"{json.dumps(preview, ensure_ascii=False, indent=2)}\n"
            f"Effetti: {list(effects)}. Per approvare: esegui piano {proposal_id}"
        )

    def _validate_effects(self, nodes: tuple[TaskNode, ...]) -> None:
        for node in nodes:
            cap = self.registry.get(node.capability_id)
            if cap is None:
                raise SkillError(f"capability inesistente: {node.capability_id}")
            if cap.risk_class not in {"safe", "read_sensitive"}:
                raise SkillError(
                    "capability con effetti bloccata: adapter rollback verificato "
                    f"non disponibile per {node.capability_id}")

    def _execute_plan(self, proposal_id: str) -> str:
        proposal = self._plans.pop(proposal_id, None)
        if proposal is None:
            return "Piano inesistente o gia consumato."
        result = self.subagent.execute(
            DelegationRequest(proposal.graph, "process"), proposal.arguments,
            owner_approved=True)
        self.audit("p3_plan_executed", {
            "proposal_id": proposal_id, "ok": result.ok,
            "completed_nodes": len(result.output),
        })
        status = "verificato" if result.ok else f"fermato su errore: {result.error}"
        return f"Piano {status}. Nodi completati: {list(result.output)}."

    def _propose_canary(self, mutation_id: str) -> str:
        self._canaries.add(mutation_id)
        self.audit("p3_canary_proposed", {"mutation_id": mutation_id})
        return (
            f"Anteprima canary `{mutation_id}`: prima dell'avvio verifichera "
            "evidenza evaluator, contesto governato e rollback; non promuove.\n"
            f"Per approvare: conferma canary {mutation_id}"
        )

    def _confirm_canary(self, mutation_id: str) -> str:
        if mutation_id not in self._canaries:
            return "Canary non proposto o gia consumato."
        self._canaries.remove(mutation_id)
        actions = self.advance_canary(mutation_id)
        self.audit("p3_canary_confirmed", {"mutation_id": mutation_id,
                                          "actions": len(actions)})
        relevant = [item for item in actions if item.get("mutation_id") == mutation_id]
        return (
            f"Canary governato `{mutation_id}` elaborato. "
            f"Azioni: {json.dumps(relevant, ensure_ascii=False)}. "
            "Nessuna promotion automatica."
        )
