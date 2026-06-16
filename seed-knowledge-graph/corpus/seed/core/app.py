"""Orchestratore: collega tutti i moduli core e gestisce il loop di chat.

Flusso di una richiesta (doc 01, aggiornato v0.2):
input → privacy gate (redazione) → ROUTER DETERMINISTICO (puro Python) →
[se non e' un comando] contesto selezionato → LLM (tool calling) →
[permission broker → sandbox] → risposta → re-idratazione → UI + trace.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from . import config as config_mod
from . import forbidden
from .capabilities import CapabilityRegistry
from .design_review import DesignReviewer
from .evolution import EvolutionEngine
from . import calibration
from . import shadow_review
from .knowledge import KnowledgeExtractor, KnowledgeStore
from .living_profile import LivingProfileBuilder
from .llm import LLMClient
from .memory import Memory
from .model_router import ModelRouter, RolePolicy, resolve_roles
from .onboarding import OnboardingEngine
from .personality import PersonalityDecision, PersonalityRuntime
from .permissions import PermissionBroker
from .privacy import GateResult, PrivacyGate
from . import retrieval
from . import user_knowledge
from .embeddings import LocalEmbedder
from .emotion import EmotionRecognizer, label_key
from .research import ResearchLane
from .router import CommandRouter, Intent
from . import salience
from . import runtime_bench
from .daemon import BackgroundDaemon
from . import worker as worker_mod
from . import worker_sandbox
from . import write_safe as write_safe_mod
from .skills import SkillRegistry
from .gateway import CrossSurfaceGateway
from .observation import ObservationLane
from .scheduler import Scheduler
from .telemetry import Telemetry
from .voice import VoiceEngine
from .watcher import ActivityWatcher

log = logging.getLogger("seed.app")

_MAX_TOOL_ROUNDS = 4


def normalize_repl_command(text: str) -> str:
    stripped = text.strip().lower()
    return ":" + stripped.lstrip(":") if stripped.startswith(":") else ""


class SeedApp:
    def __init__(self, cfg: config_mod.SeedConfig | None = None):
        self.cfg = cfg or config_mod.load()
        log.info("config: %s", self.cfg.redacted_summary())

        forbidden.seed_data_dir().mkdir(parents=True, exist_ok=True)
        forbidden.workspace_dir().mkdir(parents=True, exist_ok=True)

        self.memory = Memory()
        self.gate = PrivacyGate(self.memory,
                                opf_checkpoint=self.cfg.privacy.opf_checkpoint,
                                recall_bias=self.cfg.privacy.recall_bias,
                                fail_closed=self.cfg.privacy.fail_closed)
        self.broker = PermissionBroker(self.memory)
        self.registry = CapabilityRegistry(self.memory, self.broker)
        # S10: un solo client OpenAI-compatible; i ruoli cambiano solo il modello
        # per chiamata. models.base_url/api_key, se presenti, hanno precedenza su
        # llm.* (stesso provider per tutti i ruoli, es. Ollama Cloud).
        self.llm = LLMClient(
            self.cfg.models.base_url or self.cfg.llm.base_url
            or "https://openrouter.ai/api/v1",
            self.cfg.models.api_key or self.cfg.llm.api_key,
            self.cfg.llm.model_runtime,
            max_tokens=self.cfg.llm.max_tokens)
        self.models = ModelRouter(
            self.llm,
            roles=resolve_roles(self.cfg.models, self.cfg.llm),
            policy=RolePolicy(
                fail_closed_roles=tuple(self.cfg.models.policy.fail_closed_roles),
                record_model_per_call=self.cfg.models.policy.record_model_per_call,
                allow_automatic_premium_escalation=(
                    self.cfg.models.policy.allow_automatic_premium_escalation),
            ),
            audit=lambda ev, payload: self.memory.add_event(ev, payload),
        )
        # Viste legate al ruolo: drop-in per i moduli che ricevevano `self.llm`.
        self._conversation = self.models.bind("conversation")
        self._tool_builder = self.models.bind("tool_builder")
        self.onboarding = OnboardingEngine(self.memory, self._conversation)
        self.personality = PersonalityRuntime(self.memory)
        self.evolution = EvolutionEngine(self.cfg, self.memory, self.gate,
                                         self._tool_builder, self.registry)
        # S10.3: design reviewer read-only. Evidenza nel lineage, mai promotion.
        # S10.5: owner gate — review reale disattivata finche' l'owner non apre.
        self.design_reviewer = DesignReviewer(
            lineage=getattr(self.evolution, "lineage", None),
            reviews_root=forbidden.seed_data_dir() / "lab" / "design_reviews",
            audit=lambda ev, payload: self.memory.add_event(ev, payload),
            real_enabled=self.cfg.models.policy.design_reviewer_real_enabled,
        )
        self.evolution.set_design_reviewer(self.design_reviewer, self.models)
        # M2: store conoscenza tipata (supersession/contradiction) + estrattore
        # candidate-only. L'estrazione gira sleep-time (vedi scheduler), non per
        # turno: l'LLM propone candidate, l'harness promuove.
        self.knowledge_store = KnowledgeStore(self.memory)
        self.knowledge_extractor = KnowledgeExtractor()
        self.living_profile = LivingProfileBuilder(self.memory)
        # M3: embedder locale per il vector stream del retrieval (opt-in, lazy).
        self.embedder = (
            LocalEmbedder(self.cfg.models.embedding_model)
            if self.cfg.models.embedding_enabled and self.cfg.models.embedding_model
            else None)
        self.telemetry = Telemetry(self.memory, self.evolution)
        self.voice = VoiceEngine(
            self.cfg.voice,
            audit=lambda ev, payload: self.memory.add_event(ev, payload))
        # S11.2: emotion recognizer (SER) per-turno, opt-in, SOLO pannello voce.
        self.emotion = (
            EmotionRecognizer(self.cfg.voice.emotion_model)
            if self.cfg.voice.emotion_enabled else None)
        self.watcher = ActivityWatcher(self.memory, self.gate,
                                       poll_seconds=self.cfg.watcher.poll_seconds,
                                       excluded_apps=self.cfg.watcher.excluded_apps)
        self.watcher.set_onboarding_blocked(not self.onboarding.complete)
        if not self.cfg.watcher.enabled:
            self.watcher.pause(minutes=-1)
        self.scheduler = Scheduler(
            self.watcher,
            self.evolution,
            can_reflect=lambda: self.onboarding.complete,
            on_consolidate=self.consolidate_memory,
        )
        # D1: daemon di background SOLO in-process (parte con SEED, muore alla
        # chiusura; nessun servizio OS, nessun always-on). Heartbeat reviewable,
        # coda di proattivita' persistente con cooldown/suppression/silenzio di
        # default. ZERO azioni agentiche: non riceve registry/broker/sandbox,
        # quindi per costruzione non puo' eseguire capability, shell o file.
        self.daemon = BackgroundDaemon(
            self.memory,
            enabled=self.cfg.daemon.enabled,
            heartbeat_seconds=self.cfg.daemon.heartbeat_seconds,
            cooldown_seconds=self.cfg.daemon.cooldown_seconds,
            min_net_value=self.cfg.daemon.min_net_value,
            audit=lambda ev, payload: self.memory.add_event(ev, payload),
            can_run=lambda: self.onboarding.complete,
        )
        # D2: worker adapter READ-only dietro permission broker + audit. Riceve
        # SOLO un provider di stato aggregato (review del daemon), mai config/key
        # o memoria grezza: per costruzione non puo' scrivere o leggere file/shell.
        self.worker = (
            worker_mod.build_runtime_status_worker(
                broker=self.broker,
                status_provider=self.daemon.review,
                audit=lambda ev, payload: self.memory.add_event(ev, payload),
                allowed_actions=tuple(self.cfg.worker.allowed_actions),
            )
            if self.cfg.worker.enabled else None)
        # D-OBS: observation lane READ-only. Default OFF + consenso per-classe;
        # produce SOLO candidate-ipotesi redatte a bassa confidenza (mai fatti,
        # mai azioni). Alimenta la conoscenza tipata (M2) via KnowledgeStore.
        self.observation = ObservationLane(
            self.memory, self.knowledge_store,
            enabled=self.cfg.observation.enabled,
            sensitive_excluded=self.cfg.observation.sensitive_excluded,
            min_salience=self.cfg.observation.min_salience,
            audit=lambda ev, payload: self.memory.add_event(ev, payload))
        # D4: worker WRITE_SAFE. Default OFF; write reversibili allowlistate dietro
        # gate D3 (approval owner + dry-run + rollback + observation). Critiche
        # vietate. Nessuna shell, scrittura solo entro il workspace.
        self.write_safe = write_safe_mod.build_workspace_note_worker(
            broker=self.broker,
            enabled=self.cfg.worker.write_safe_enabled,
            allowed_actions=tuple(self.cfg.worker.write_safe_actions),
            audit=lambda ev, payload: self.memory.add_event(ev, payload))
        # D5: skills procedurali + delega. Default OFF; nessuna skill attiva senza
        # audit + reviewer + owner gate (mai self-install). Delega a sub-agenti
        # isolati gated (isolamento reale = futuro).
        self.skills = SkillRegistry(
            enabled=self.cfg.skills.enabled,
            allowed_capabilities=tuple(self.cfg.skills.allowed_capabilities),
            audit=lambda ev, payload: self.memory.add_event(ev, payload))
        # D6: gateway cross-surface opzionale. Default OFF; consenso per-superficie
        # + privacy gate obbligatorio; nessun invio reale (owner). Riusa il gate.
        self.gateway = CrossSurfaceGateway(
            self.memory, self.gate,
            enabled=self.cfg.gateway.enabled,
            audit=lambda ev, payload: self.memory.add_event(ev, payload))
        self.router = CommandRouter(self.memory, llm=self._conversation,
                                    runtime_model=None)  # modello dal ruolo
        self.research = ResearchLane(self.memory, self.gate, self.cfg.research)
        self.router.register_intent(Intent(
            "research_search",
            "cercare informazioni aggiornate online (arg = cosa cercare)",
            [r"\b(?:cerca|ricerca)\s+(?:online|sul web|su internet|in rete)\s+(?P<arg>.+)$",
             r"\b(?:cerca|ricerca)\s+(?P<arg>.+?)\s+(?:online|sul web|su internet|in rete)$",
             r"\bsearch\s+(?:online|the web)\s+(?:for\s+)?(?P<arg>.+)$"],
            local_handler=self._research_handler, arg_name="query"))
        self.router.register_intent(Intent(
            "research_deep",
            "ricerca approfondita online (arg = cosa approfondire)",
            [r"\b(?:approfondisci|ricerca approfondita(?:\s+su)?)\s+(?P<arg>.+)$"],
            local_handler=self._research_deep_handler, arg_name="query"))
        self.router.register_intent(Intent(
            "research_more_sources",
            "allargare le prossime ricerche online (piu' fonti)",
            [r"\b(?:analizza|usa|considera|voglio|preferisco)\s+piu\s+fonti\b",
             r"\bpiu\s+fonti\s+nelle\s+ricerche\b"],
            local_handler=lambda _a: self._breadth_response(+1)))
        self.router.register_intent(Intent(
            "research_fewer_sources",
            "restringere le prossime ricerche online (meno fonti, minimo 3)",
            [r"\b(?:analizza|usa|considera|voglio|preferisco)\s+meno\s+fonti\b",
             r"\bmeno\s+fonti\s+nelle\s+ricerche\b"],
            local_handler=lambda _a: self._breadth_response(-1)))
        self.router.register_intent(Intent(
            "research_sources_reset",
            "tornare al numero standard di fonti nelle ricerche",
            [r"\bfonti\s+(?:standard|normali|di default)\b"],
            local_handler=lambda _a: self._breadth_response(0)))
        # K1: recall ESPLICITO del modello utente (comando, non indovinato).
        self.router.register_intent(Intent(
            "list_knowledge",
            "rileggere cosa SEED ha memorizzato esplicitamente sull'utente",
            [r"\bcosa sai (?:di|su di) me\b", r"\bche cosa sai di me\b",
             r"\bcosa (?:ti ricordi|hai capito) di me\b",
             r"\bcosa hai memorizzato su di me\b"],
            local_handler=lambda _a: self._knowledge_recall()))
        self.router.register_intent(Intent(
            "show_living_profile",
            "mostrare la versione candidata o approvata del living profile",
            [r"\bmostrami il mio profilo(?: vivente)?\b"],
            local_handler=lambda _a: self._show_living_profile()))
        self.router.register_intent(Intent(
            "show_profile_counterpoint",
            "mostrare i dubbi separati sul modello utente",
            [r"\bmostrami (?:il )?counterpoint(?: del profilo)?\b"],
            local_handler=lambda _a: self._show_profile_counterpoint()))
        self.router.register_intent(Intent(
            "approve_living_profile",
            "approvare l'ultima versione del living profile",
            [r"\bapprova (?:il )?profilo(?: vivente)?\b"],
            local_handler=lambda _a: self._approve_living_profile()))
        self.router.register_intent(Intent(
            "approve_profile_counterpoint",
            "approvare l'ultima versione del counterpoint",
            [r"\bapprova (?:il )?counterpoint(?: del profilo)?\b"],
            local_handler=lambda _a: self._approve_profile_counterpoint()))
        # M1: ricarica la cronologia conversazionale dalle sessioni precedenti,
        # cosi' SEED non riparte amnesico a ogni avvio.
        self._history: list[dict] = self.memory.recent_chat(limit=20)

    # ------------------------------------------------------------------
    def _research_handler(self, args: dict) -> str:
        return self._run_research(args, depth="basic")

    def _research_deep_handler(self, args: dict) -> str:
        return self._run_research(args, depth="deep")

    def _run_research(self, args: dict, depth: str) -> str:
        query = (args.get("query") or "").strip()
        if not query:
            return "Cosa vuoi che cerchi online?"
        outcome = self.research.search(query, depth=depth)
        return self.research.answer(
            outcome, llm=self._conversation, runtime_model=None)

    def _breadth_response(self, delta: int) -> str:
        value = self.research.adjust_breadth(delta)
        counts = self.research.tier_counts()
        label = {-1: "Restringo", 0: "Torno allo standard", 1: "Allargo"}[delta]
        return (f"{label}: da ora analizzo {counts['quick']} fonti per le "
                f"ricerche rapide, {counts['basic']} per quelle normali e "
                f"{counts['deep']} per gli approfondimenti. "
                "Sotto 3 non scendo mai: una fonte sola non basta per fidarsi.")

    # ------------------------------------------------------------------
    def start_background(self) -> None:
        self.gate.init_opf()
        self.scheduler.start()
        # D1: il daemon vive SOLO qui, nel processo SEED supervisionato.
        self.daemon.start()

    def shutdown(self) -> None:
        # D1: termina con SEED; a processo chiuso non resta nulla in esecuzione.
        self.daemon.stop()
        self.scheduler.stop()
        self.memory.close()

    # ------------------------------------------------------------------
    def _system_prompt(self, decision: PersonalityDecision, user_text: str = "",
                       affect=None) -> str:
        # M1+M2: i fatti entrano per RILEVANZA alla richiesta corrente, non con
        # un taglio cieco. Candidati = fatti legacy + conoscenza tipata ATTIVA
        # (solo claim espliciti/promossi; le ipotesi candidate NON entrano come
        # fatti — ipotesi != fatto). Le preferenze hanno gia' un canale S8.
        candidates = [{"statement": f["statement"], "created_at": None, "kid": None,
                       "fact_id": f["id"], "confidence": f["confidence"]}
                      for f in self.memory.active_facts()]
        for c in self.memory.active_knowledge():
            # K1: le preferenze hanno il canale S8; i claim SENSIBILI non entrano
            # nel contesto per default (consenso/rilevanza esplicita richiesti).
            if c["claim_type"] == "preference" or c["sensitivity"] == "sensitive":
                continue
            candidates.append({"statement": f"{c['subject']}: {c['value']}",
                               "created_at": c["created_at"], "kid": c["id"],
                               "claim_type": c["claim_type"],
                               "confidence": c["confidence"],
                               "provenance": c["provenance"],
                               "sensitivity": c["sensitivity"],
                               "lifecycle_state": c["lifecycle_state"],
                               "superseded_at": c["superseded_at"]})
        # M3: retrieval triple-stream (lexical + vector opzionale + graph) fuso RRF.
        edges = self.memory.all_edges()
        ranked = retrieval.rank_candidates(
            user_text, candidates, edges=self.memory.all_edges(),
            embedder=self.embedder, k=len(candidates))
        relevant, decisions = salience.select_context(
            user_text, ranked, edges=edges)
        for item in decisions:
            self.memory.add_salience_decision(
                item_ref=item.item_ref, action=item.action, score=item.score,
                reasons=list(item.reasons), factors=item.factors)
        selected_ids = {
            item["kid"] for item in relevant if item.get("kid") is not None
        }
        profile, counterpoint = self.living_profile.approved_context(
            source_claim_ids=selected_ids)
        counterpoint = salience.select_counterpoint(user_text, counterpoint)
        prompt = self.personality.system_prompt(
            decision, [c["statement"] for c in relevant],
            living_profile=profile, profile_counterpoint=counterpoint)
        # S11.2: segnale affettivo del turno (solo voce, temporaneo). Influenza il
        # tono, MAI memorizzato, MAI diagnosi; la correzione esplicita prevale.
        if affect is not None and not affect.expired():
            prompt += ("\nSEGNALE AFFETTIVO DEL TURNO (solo voce, temporaneo, NON "
                       "un fatto ne' una diagnosi): " + affect.tone_hint() +
                       " La correzione esplicita dell'utente prevale su questo segnale.")
        return prompt

    def _knowledge_recall(self) -> str:
        """K1: recall esplicito del modello utente. Raggruppa per tipo, esclude i
        claim sensibili, ri-idrata i placeholder. Solo da comando esplicito."""
        claims = [c for c in self.memory.active_knowledge()
                  if c["sensitivity"] != "sensitive"]
        if not claims:
            return "Non ho ancora memorizzato nulla di esplicito su di te."
        labels = {"fact": "Fatti", "state": "Stato", "routine": "Routine",
                  "pattern": "Pattern", "preference": "Preferenze",
                  "relation": "Relazioni/contesto", "exception": "Eccezioni",
                  "hypothesis": "Ipotesi", "boundary": "Confini"}
        by_type: dict[str, list[str]] = {}
        for c in claims:
            by_type.setdefault(c["claim_type"], []).append(f"{c['subject']}: {c['value']}")
        lines = ["Ecco cosa ho memorizzato esplicitamente su di te:"]
        for claim_type, items in by_type.items():
            lines.append(f"\n{labels.get(claim_type, claim_type)}:")
            lines.extend(f"- {it}" for it in items[:10])
        return self.gate.rehydrate("\n".join(lines))

    def learn_from_recent(self, limit: int = 12) -> int:
        """M2: estrazione candidate-only dalla conversazione recente (sleep-time).
        L'LLM propone claim tipizzati, l'harness li registra come candidate/attivi
        con supersession. Nessuna scrittura diretta di fatti dal modello."""
        history = self.memory.recent_chat_records(limit=limit)
        if not history:
            return 0
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        provenance = [m["id"] for m in history if m["role"] == "user"]
        claims = self.knowledge_extractor.extract(
            transcript, self._conversation, provenance=provenance)
        recorded = 0
        for claim in claims:
            outcome = self.knowledge_store.record(claim)
            if outcome["action"] in ("added", "superseded"):
                recorded += 1
        return recorded

    def consolidate_memory(self) -> int:
        """M2+K2 sleep-time: estrae claim, poi rigenera i derivati reviewable."""
        repaired = 0
        active = self.memory.active_knowledge()
        for row in active:
            if not row["provenance"]:
                episode_id = self.memory.find_user_chat_episode_containing(row["value"])
                if episode_id is not None:
                    self.memory.set_knowledge_provenance(row["id"], [episode_id])
                    row["provenance"] = [episode_id]
            for claim in user_knowledge.repair_compound_claims([row]):
                outcome = self.knowledge_store.record(claim)
                if outcome["action"] in ("added", "superseded"):
                    repaired += 1
        learned = self.learn_from_recent()
        changed = self.living_profile.rebuild()
        # K4: ogni pattern apre una predizione calibrabile (sleep-time).
        predictions_opened = calibration.register_predictions(self.memory)
        report = calibration.calibration_report(self.memory)
        # M4: digest reviewable del dream cycle (solo conteggi, mai testo).
        self.memory.add_event("dream_cycle", {
            "repaired": repaired, "learned": learned,
            "profile_changed": int(changed["profile_changed"]),
            "counterpoint_changed": int(changed["counterpoint_changed"]),
            "predictions_opened": predictions_opened,
            "calibration_brier": report.brier,
        })
        return (repaired + learned + int(changed["profile_changed"])
                + int(changed["counterpoint_changed"]) + predictions_opened)

    # ------------------------------------------------------------------
    # S11 voce: STT/TTS opt-in. Audio non persistito; transcript passa dal
    # privacy gate dentro handle_message prima di raggiungere l'LLM.
    def grant_voice_consent(self, granted: bool = True) -> bool:
        self.memory.set_voice_consent(granted)
        return self.memory.voice_consent()

    def voice_ready(self) -> bool:
        return self.voice.enabled and self.memory.voice_consent()

    def voice_message(self, audio_bytes: bytes, mime: str = "audio/webm") -> dict:
        """STT -> normale pipeline (con privacy gate). Ritorna transcript +
        risposta. L'audio non viene salvato."""
        if not self.voice.enabled:
            return {"error": "voce non attiva: configura la key in core_config."}
        if not self.memory.voice_consent():
            return {"error": "consenso voce non concesso."}
        stt = self.voice.transcribe(audio_bytes, mime)
        transcript = stt["text"]
        if not transcript.strip():
            return {"transcript": "", "answer": "Non ho capito l'audio. Riprova."}
        # S11.2: segnale affettivo del turno (solo pannello voce). Mai memoria,
        # mai diagnosi; audit solo aggregato (label + bucket confidenza).
        affect = None
        if self.emotion is not None:
            suffix = "." + (mime.split("/")[-1] or "wav")
            affect = self.emotion.recognize(audio_bytes, suffix=suffix)
            if affect is not None:
                self.memory.add_event("voice_affect", {
                    "label": label_key(affect.label),
                    "confidence_bucket": round(float(affect.confidence), 1)})
        answer = self.handle_message(transcript, affect=affect)
        result = {"transcript": transcript, "language": stt["language"],
                  "answer": answer}
        if affect is not None:
            result["affect"] = {"label": label_key(affect.label),
                                "confidence": round(float(affect.confidence), 2)}
        return result

    def voice_reply_audio(self, text: str, *, gender: str | None = None) -> bytes:
        """TTS della risposta testuale gia' mostrata. Richiede consenso voce."""
        if not self.voice_ready():
            raise RuntimeError("voce non pronta (key o consenso mancante)")
        return self.voice.speak(text, gender=gender)

    def run_shadow_review(self) -> dict:
        """S10.5: shadow review su candidate sintetiche. Nessun effetto su
        candidate reali/promotion. Evidenza registrata, marcata shadow."""
        return shadow_review.run_shadow_review(self.design_reviewer, self.models)

    def run_daemon_review(self) -> dict:
        """D1: snapshot aggregato e rivedibile del daemon (stato, conteggi coda,
        flag dei confini). Nessun dato personale; non esegue azioni."""
        return self.daemon.review()

    # --- UI surfaces (U2/U3) -------------------------------------------
    def ui_user_model(self) -> list[dict]:
        """U2 Modello Utente: claim K1 ATTIVI non sensibili con provenance,
        per la superficie "cosa penso di sapere di te". Le ipotesi candidate e i
        sensibili non entrano. Mai un fatto presentato come certo se inferito."""
        out = []
        for row in self.memory.active_knowledge():
            if row["sensitivity"] == "sensitive":
                continue
            out.append({
                "id": row["id"], "claim_type": row["claim_type"],
                "value": self.gate.rehydrate(row["value"]),
                "confidence": round(row["confidence"], 2),
                "source": row["confidence_source"],
                "provenance": row["provenance"],
                "review_state": row["review_state"],
            })
        return out

    def ui_correct_claim(self, claim_id: int, is_true: bool,
                         new_value: str = "") -> dict:
        """U2: "e' vero" -> conferma; "non e' cosi'" -> corregge (supersession).
        La correzione dell'utente prevale (K1/M2)."""
        if is_true:
            self.memory.set_knowledge_review(int(claim_id), "confirmed")
            return {"ok": True, "action": "confirmed"}
        self.memory.set_knowledge_review(int(claim_id), "corrected")
        self.memory.supersede_knowledge(int(claim_id))
        return {"ok": True, "action": "corrected"}

    def ui_explain_last(self) -> str:
        """U2 "perche'?": spiegazione deterministica dell'ultima decisione di
        personalita' (modalita' + ragioni), senza testo del turno. Mai LLM."""
        decisions = self.memory.personality_decisions()
        if not decisions:
            return ("Rispondo con la mia identita' stabile: diretto, onesto "
                    "sull'incertezza, senza compiacenza.")
        last = decisions[0] if isinstance(decisions, list) and decisions else None
        if not last:
            return "Nessuna decisione di personalita' registrata per l'ultimo turno."
        mode = last.get("mode", "informativa")
        reasons = ", ".join(last.get("reasons", []) or []) or "identita' stabile"
        cp = " (valutazione indipendente)" if last.get("counterpoint_required") else ""
        return f"Modalita': {mode}{cp}. Motivi: {reasons}."

    def ui_permissions(self) -> dict:
        """U2 Permessi e Privacy: cosa SEED osserva + stato watcher."""
        return {
            "observation": self.observation.review(),
            "watcher_paused": self.watcher.paused,
            "daemon": self.daemon.review(),
        }

    def ui_set_observation_consent(self, obs_class: str, enabled: bool) -> dict:
        self.observation.set_consent(obs_class, bool(enabled))
        return self.observation.review()

    def ui_revoke_observations(self) -> dict:
        purged = self.observation.revoke_all()
        return {"purged": purged, "observation": self.observation.review()}

    def run_worker_status(self) -> dict:
        """D2: invoca la capability worker READ-only `worker.runtime_status`
        dietro permission broker + audit. Ritorna stato runtime aggregato."""
        if self.worker is None:
            return {"error": "worker disabilitato"}
        result = self.worker.run(
            worker_mod.WorkerRequest(action="worker.runtime_status"))
        return {
            "action": result.action, "ok": result.ok,
            "output": result.output, "observed": result.observed,
            "audit": result.audit, "error": result.error,
        }

    def run_runtime_benchmark(self) -> dict:
        """D0: benchmark sintetico locale; non avvia runtime esterni."""
        target = runtime_bench.write_runtime_benchmark(
            forbidden.seed_data_dir() / "lab" / "runtime_bench")
        report = runtime_bench.build_runtime_benchmark()
        return {
            "report": str(target),
            "report_hash": report["report_hash"],
            "recommendation": report["recommendation"],
        }

    def _show_living_profile(self) -> str:
        profile = self.memory.latest_living_profile()
        if profile is None:
            return "Nessun living profile disponibile. Esegui prima :reflect."
        return self.gate.rehydrate(json.dumps({
            "version": profile["version"], "review_state": profile["review_state"],
            "delta": profile["delta"], "sections": profile["sections"],
        }, ensure_ascii=False, indent=2))

    def _show_profile_counterpoint(self) -> str:
        counterpoint = self.memory.latest_counterpoint()
        if counterpoint is None:
            return "Nessun counterpoint disponibile. Esegui prima :reflect."
        return self.gate.rehydrate(json.dumps({
            "version": counterpoint["version"],
            "review_state": counterpoint["review_state"],
            "fragments": counterpoint["fragments"],
        }, ensure_ascii=False, indent=2))

    def _approve_living_profile(self) -> str:
        profile = self.memory.latest_living_profile()
        if profile is None:
            return "Nessun living profile da approvare."
        self.memory.set_living_profile_review(profile["version"], "approved")
        return f"Living profile v{profile['version']} approvato."

    def _approve_profile_counterpoint(self) -> str:
        counterpoint = self.memory.latest_counterpoint()
        if counterpoint is None:
            return "Nessun counterpoint da approvare."
        self.memory.set_counterpoint_review(counterpoint["version"], "approved")
        return f"Counterpoint v{counterpoint['version']} approvato."

    def export_report(self):
        """Esporta uno snapshot coerente, mai a meta' reflection."""
        self.scheduler.wait_for_reflection()
        return self.telemetry.export_report()

    # ------------------------------------------------------------------
    def handle_message(self, user_text: str, *, affect=None) -> str:
        """Entry point della chat (UI o REPL).

        Prima il ROUTER DETERMINISTICO (puro Python, zero token): se il
        messaggio e' un comando noto, si esegue senza nemmeno toccare l'API.
        Solo se non e' un comando si passa al flusso conversazionale LLM."""
        # I comandi REPL utili al pilot devono funzionare anche dalla UI/EXE.
        # Non diventano messaggi chat e non possono essere interpretati dall'LLM.
        command = normalize_repl_command(user_text)
        if command == ":reflect":
            return json.dumps(
                self.scheduler.force_reflection(), ensure_ascii=False, indent=2)
        if command == ":report":
            return f"Report aggregato esportato in:\n{self.export_report()}"
        if command == ":shadowreview":
            return json.dumps(self.run_shadow_review(), ensure_ascii=False, indent=2)
        if command == ":runtimebench":
            return json.dumps(self.run_runtime_benchmark(), ensure_ascii=False, indent=2)
        if command == ":daemon":
            return json.dumps(self.run_daemon_review(), ensure_ascii=False, indent=2)
        if command == ":worker":
            return json.dumps(self.run_worker_status(), ensure_ascii=False, indent=2)
        if command == ":observation":
            return json.dumps(self.observation.review(), ensure_ascii=False, indent=2)
        if command == ":sandbox":
            return json.dumps(worker_sandbox.review_matrix(), ensure_ascii=False, indent=2)
        if command == ":writesafe":
            return json.dumps(self.write_safe.review(), ensure_ascii=False, indent=2)
        if command == ":skills":
            return json.dumps(self.skills.review(), ensure_ascii=False, indent=2)
        if command == ":gateway":
            return json.dumps(self.gateway.review(), ensure_ascii=False, indent=2)

        t0 = time.time()
        state_before = self.onboarding.state
        onboarding_pending = state_before["phase"] != "complete"
        local_memory_allowed = bool(
            state_before.get("consent", {}).get("local_memory")
        )
        collection_allowed = (
            local_memory_allowed and state_before["phase"] != "paused"
        )
        # Prima del consenso l'onboarding non chiama provider e non deve
        # nemmeno creare il mapping locale persistente usato dalla redazione.
        red = (
            self.gate.redact(
                user_text,
                purpose="llm",
                persist_mapping=not onboarding_pending,
            )
            if collection_allowed or not onboarding_pending
            else GateResult(text=user_text)
        )
        episode_id = None
        if onboarding_pending and collection_allowed:
            episode_id = self.memory.add_episode(
                "chat", {"role": "user", "text": red.text}, category="onboarding"
            )
        onboarding = self.onboarding.handle(red.text, episode_id=episode_id)
        if onboarding.consumed:
            answer = onboarding.text
            self.watcher.set_onboarding_blocked(not self.onboarding.complete)
            state_after = self.onboarding.state
            if (
                state_after.get("consent", {}).get("local_memory")
                and state_after["phase"] != "paused"
            ):
                self.memory.add_episode(
                    "chat",
                    {"role": "assistant", "text": answer},
                    category="onboarding",
                )
            self._write_trace(
                {
                    "onboarding": self.onboarding.state["phase"],
                    "llm_used": onboarding.llm_used,
                    "latency_s": round(time.time() - t0, 2),
                }
            )
            return self.gate.rehydrate(answer)
        episode_id = self.memory.add_episode(
            "chat", {"role": "user", "text": red.text}, category="chat"
        )
        self.router.capture_explicit_preference(red.text)
        self.personality.capture_explicit_correction(red.text)
        # K1: cattura deterministica di claim espliciti dalla chat (zero token).
        # Una ri-dichiarazione con valore nuovo supera il vecchio (correzione).
        for claim in user_knowledge.capture_explicit(
                red.text, provenance=[episode_id]):
            self.knowledge_store.record(claim)
        control = self.personality.control_response(red.text)
        if control is not None:
            self.memory.add_episode(
                "chat", {"role": "assistant", "text": control}, category="chat"
            )
            self._write_trace(
                {
                    "personality_control": True,
                    "llm_used": False,
                    "latency_s": round(time.time() - t0, 2),
                }
            )
            return control
        conversation_text, explicit_mode = self.personality.prepare_text(red.text)

        route = self.router.try_route(conversation_text)
        if route is not None:
            answer = self.router.execute(route, self.registry)
            self.memory.add_episode("chat", {"role": "assistant", "text": answer},
                                    category="chat")
            self.memory.add_event("routed_command", {
                "intent": route.intent, "source": route.source,
                "llm_used": route.source == "llm"})
            self._write_trace({"routed": route.intent, "source": route.source,
                               "llm_used": route.source == "llm",
                               "latency_s": round(time.time() - t0, 2)})
            return answer

        decision = self.personality.plan(conversation_text, explicit_mode)
        self._history.append({"role": "user", "content": conversation_text})
        trace = {
            "redactions": red.replacements,
            "tool_calls": [],
            "personality": decision.trace_summary(),
        }
        messages = [
            {"role": "system", "content": self._system_prompt(decision, conversation_text, affect)}
        ] + self._history[-20:]
        tools = self.registry.to_openai_tools()

        try:
            answer = self._converse(messages, tools, trace, decision)
        except Exception as exc:
            log.exception("handle_message")
            answer = f"Errore: {exc}"

        self._history.append({"role": "assistant", "content": answer})
        self.memory.add_episode("chat", {"role": "assistant", "text": answer},
                                category="chat")
        trace["latency_s"] = round(time.time() - t0, 2)
        self._write_trace(trace)
        return self.gate.rehydrate(answer)

    def _converse(
        self,
        messages: list[dict],
        tools: list[dict],
        trace: dict,
        decision: PersonalityDecision,
    ) -> str:
        for _ in range(_MAX_TOOL_ROUNDS):
            resp = self._conversation.chat(messages, tools=tools or None, redacted=True)
            if not resp.tool_calls:
                answer, violations, repaired = self.personality.review_and_repair(
                    resp.text, decision, self._conversation, privacy_gate=self.gate
                )
                trace["personality"]["violations"] = violations
                trace["personality"]["repaired"] = repaired
                return answer
            messages.append({"role": "assistant", "content": resp.text or None,
                             "tool_calls": [{"id": tc["id"], "type": "function",
                                             "function": {"name": tc["name"],
                                                          "arguments": json.dumps(tc["arguments"])}}
                                            for tc in resp.tool_calls]})
            for tc in resp.tool_calls:
                result = self.registry.invoke(tc["name"], tc["arguments"])
                trace["tool_calls"].append({"name": tc["name"],
                                            "ok": "error" not in result})
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                 "content": json.dumps(result, ensure_ascii=False)[:4000]})
        return "Mi sono fermato: troppi passaggi di tool per una sola richiesta."

    def _write_trace(self, trace: dict) -> None:
        traces = forbidden.seed_data_dir() / "data" / "traces"
        traces.mkdir(parents=True, exist_ok=True)
        day_file = traces / f"{time.strftime('%Y-%m-%d')}.jsonl"
        with open(day_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), **trace}, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    # REPL di sviluppo (senza webview)
    # ------------------------------------------------------------------
    def repl(self) -> None:
        ui = self.evolution.ui_manifest()
        print(f"SEED v0.2 — {ui['persona']['greeting']}  (:q esce, :reflect forza il pass)")
        if not self.onboarding.complete:
            print(self.onboarding.opening_prompt())
        self.start_background()
        try:
            while True:
                try:
                    text = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                command = normalize_repl_command(text)
                if command in (":q", ":quit", ":exit"):
                    break
                if command == ":reflect":
                    print(json.dumps(self.scheduler.force_reflection(),
                                     ensure_ascii=False, indent=2))
                    continue
                if command == ":report":
                    print("report:", self.telemetry.export_report())
                    continue
                if not text:
                    continue
                print(self.handle_message(text))
        finally:
            self.shutdown()
