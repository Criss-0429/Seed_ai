"""Caricamento e validazione config. Le API key NON vengono mai loggate.

Ordine di ricerca:
  1. SEED_CONFIG (env, per dev/test)
  2. %LOCALAPPDATA%/SEED/core_config/config.json (installazione reale)
  3. ./config/config.json relativo alla repo (dev mode)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import forbidden

_REPO_CONFIG = Path(__file__).resolve().parents[2] / "config" / "config.json"
_REPO_TEMPLATE = Path(__file__).resolve().parents[2] / "config" / "config.example.json"


@dataclass
class LLMConfig:
    base_url: str = ""          # es. https://openrouter.ai/api/v1 | https://ai-gateway.vercel.sh/v1 | http://localhost:11434/v1
    api_key: str = ""           # VUOTA nel template — la riempie Cristian per-utente
    model_runtime: str = ""     # modello economico per il loop quotidiano
    model_reflection: str = ""  # modello frontier per il reflection notturno
    max_tokens: int = 2048
    monthly_budget_warn_usd: float = 10.0


@dataclass
class VoiceConfig:
    elevenlabs_api_key: str = ""   # VUOTA: STT/TTS restano disattivi. SOLO core_config.
    enabled: bool = False          # l'utente la attiva dall'app, se la key esiste
    # S11: modelli verificati con la key 2026-06-12.
    stt_model: str = "scribe_v1"
    tts_model: str = "eleven_v3"               # espressivo, audio tag [laughs]/[sigh]/...
    tts_fallback_model: str = "eleven_multilingual_v2"
    voice_id_female: str = "21m00Tcm4TlvDq8ikWAM"   # premade, swappabile
    voice_id_male: str = "pNInz6obpgDQGcFmaJgB"
    active_voice: str = "female"   # female | male
    voice_id: str = ""             # override esplicito: se valorizzato vince sul gender
    persist_audio: bool = False    # retention minima: niente audio su disco
    persist_transcript: bool = False
    monthly_char_cap: int = 100000 # budget TTS: cap caratteri sintetizzati
    max_audio_bytes: int = 25_000_000  # cap STT: dimensione audio in ingresso
    timeout_s: int = 60
    emotion_enabled: bool = False  # S11.2 SER (wav2vec2), SOLO pannello voce
    emotion_model: str = "superb/wav2vec2-base-superb-er"


@dataclass
class PrivacyConfig:
    opf_checkpoint: str = ""       # vuoto = default ~/.opf/privacy_filter
    recall_bias: bool = True       # preset recall-oriented
    fail_closed: bool = True       # se il gate non e' pronto, NIENTE esce verso l'API
    backend: str = "opf"           # opf (2.7GB, max) | gliner (~300MB) | regex
    lite_mode: bool = False        # True = solo regex, niente modello ML (~2.7GB)
    opf_idle_unload_s: int = 120   # scarica il filtro ML dopo N s idle (0 = mai)


@dataclass
class WatcherConfig:
    enabled: bool = True
    poll_seconds: int = 5
    process_scan_seconds: int = 60
    excluded_apps: list[str] = field(default_factory=list)


@dataclass
class ResearchConfig:
    enabled: bool = True
    provider: str = "exa"          # provider primario: exa | tavily
    exa_api_key: str = ""          # VUOTA nel template — solo in core_config
    tavily_api_key: str = ""       # VUOTA nel template — solo in core_config
    fallback: bool = True          # se il primario fallisce, prova l'altro
    max_results: int = 5           # pagine per ricerca normale (tier basic)
    max_results_quick: int = 3     # query corte/fattuali (tier quick)
    max_results_deep: int = 10     # "approfondisci ..." (tier deep)
    timeout_s: int = 20
    daily_call_cap: int = 40       # rate/budget cap: chiamate remote al giorno


@dataclass
class ModelPolicyConfig:
    # S10: ruoli che falliscono chiusi (output invalido -> inconclusive, mai pass)
    fail_closed_roles: list[str] = field(default_factory=lambda: ["design_reviewer"])
    record_model_per_call: bool = True          # audit ruolo+modello per chiamata
    allow_automatic_premium_escalation: bool = False
    # S10.5 owner gate: review su candidate REALI disattivata finche' l'owner non
    # la abilita. Shadow su candidate sintetiche sempre permesso.
    design_reviewer_real_enabled: bool = False


@dataclass
class ModelsConfig:
    """S10 Model Role Separation. Un solo provider OpenAI-compatible: i ruoli
    cambiano SOLO il nome del modello per chiamata. base_url/api_key vuoti
    ereditano da `llm`. Le key restano solo in core_config, mai in audit."""
    provider: str = ""             # informativo: ollama | openrouter | vercel
    base_url: str = ""             # vuoto -> eredita llm.base_url
    api_key: str = ""              # vuoto -> eredita llm.api_key
    roles: dict = field(default_factory=dict)   # role -> model id
    policy: ModelPolicyConfig = field(default_factory=ModelPolicyConfig)
    # M3: embedder locale per il vector stream del retrieval. Opt-in: di default
    # OFF (retrieval su lexical+graph, nessun download). Attivato esplicitamente
    # scarica il modello multilingue al primo uso.
    embedding_enabled: bool = False
    embedding_model: str = "paraphrase-multilingual-mpnet-base-v2"


@dataclass
class ProviderHubConfig:
    """P0: BYOK obbligatorio nelle installazioni tester.

    Default Python ``False`` mantiene compatibili harness/test che costruiscono
    ``SeedConfig()`` direttamente. Il template distribuito imposta ``True``.
    """
    required: bool = False


@dataclass
class EvolutionConfig:
    enabled: bool = True               # False = istanza baseline per il controllo
    max_mutations_per_night: int = 2
    trait_cooldown_days: int = 2
    capability_dormant_days: int = 4
    capability_prune_days: int = 7
    lifecycle_enabled: bool = True
    tool_builder_enabled: bool = False
    canary_context: str = "desktop-session"


@dataclass
class DaemonConfig:
    """D1: daemon di background, SOLO in-process (vive dentro SEED supervisionato
    e muore alla terminazione completa). NON e' un servizio OS. L'app puo essere
    avviata al login solo con consenso per-utente. Default silenzio + cooldown."""
    enabled: bool = True            # daemon in-process; nessun servizio OS
    heartbeat_seconds: int = 60     # battito reviewable entro la sessione
    cooldown_seconds: int = 1800    # >=30 min tra due emit: niente raffica
    min_net_value: float = 0.0      # silenzio di default: deve SUPERARE il costo


@dataclass
class WorkerConfig:
    """D2: worker adapter READ-only. Allowlist esplicita delle azioni; in D2 solo
    `worker.runtime_status`. Nessuna scrittura, shell o file reale (D3+/D4).

    D4 WRITE_SAFE: default OFF. Le write reversibili allowlistate richiedono
    approval owner + dry-run + rollback + observation (gate D3)."""
    enabled: bool = True
    allowed_actions: list[str] = field(
        default_factory=lambda: ["worker.runtime_status"])
    write_safe_enabled: bool = False               # D4: default OFF
    write_safe_actions: list[str] = field(default_factory=list)  # default vuoto


@dataclass
class ObservationConfig:
    """D-OBS: observation lane READ-only. Default OFF + consenso per-classe (la UI
    abilita ogni classe). Sensibile escluso. Mai azione, solo candidate redatte."""
    enabled: bool = False               # default OFF: nessuna osservazione
    sensitive_excluded: bool = True     # salute/finanza/relazioni fuori
    min_salience: float = 0.5           # soglia perche' diventi candidate
    poll_seconds: int = 15


@dataclass
class SkillsConfig:
    """D5: skills procedurali + delega. Default OFF. Nessun self-install: install
    richiede audit + reviewer + owner gate. Delega a sub-agenti isolati gated."""
    enabled: bool = False
    allowed_capabilities: list[str] = field(default_factory=list)
    delegation_enabled: bool = False
    isolation_available: bool = False    # legacy compatibility; rilevato a runtime
    isolation_backend: str = "process"


@dataclass
class WebRenderConfig:
    """P6 Adaptive Web Rendering. Default OFF. La fase fondazionale P6.0 NON tocca
    la rete o il browser: solo contratti, sanitizzazione e gate locali. Le fasi
    con acquisizione reale (P6.1+) restano separate e owner-gated."""
    enabled: bool = False               # default OFF: nessun renderer attivo
    network_acquisition_enabled: bool = False   # P6.1+, mai attivo in P6.0
    browser_bridge_enabled: bool = False        # P6.1+, opt-in revocabile


@dataclass
class CapabilityForgeConfig:
    """P7 Selective Capability Forge. Default OFF. P7.0 = solo contratti, policy,
    lifecycle e migrazione conservativa V1: NESSUN cambiamento di runtime. Le fasi
    P7.1+ (evidence, fitness, connector vetting, builder, evaluator, connection
    broker, activation authority) restano gate separati e owner-gated."""
    enabled: bool = False
    auto_activation_enabled: bool = False        # mai auto-espansione di autorita'
    observation_min_occurrences: int = 3
    observation_min_sessions: int = 2
    sensitive_min_occurrences: int = 5
    sensitive_min_sessions: int = 3


@dataclass
class MaintenanceConfig:
    """Retention conservativa di artefatti locali recuperabili."""
    enabled: bool = True
    keep_versions: int = 10        # active/rollback/known-good sempre protette
    keep_backups: int = 5          # solo automatici; manuali sempre protetti
    keep_runtime_backups: int = 2  # backup directory creati dagli update
    keep_update_history: int = 20  # marker applied/failed per directory
    keep_lab_runs: int = 20        # solo candidate terminali
    trace_days: int = 30


@dataclass
class SeedConfig:
    user_alias: str = "utente"     # alias scelto dall'utente, NON il nome reale
    llm: LLMConfig = field(default_factory=LLMConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)
    provider_hub: ProviderHubConfig = field(default_factory=ProviderHubConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    watcher: WatcherConfig = field(default_factory=WatcherConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    worker: WorkerConfig = field(default_factory=WorkerConfig)
    observation: ObservationConfig = field(default_factory=ObservationConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    web_render: WebRenderConfig = field(default_factory=WebRenderConfig)
    capability_forge: CapabilityForgeConfig = field(default_factory=CapabilityForgeConfig)
    maintenance: MaintenanceConfig = field(default_factory=MaintenanceConfig)

    def redacted_summary(self) -> dict:
        """Versione loggabile: key sostituite da presenza/assenza."""
        return {
            "llm": {
                "base_url": self.llm.base_url,
                "api_key": "set" if self.llm.api_key else "EMPTY",
                "model_runtime": self.llm.model_runtime,
                "model_reflection": self.llm.model_reflection,
            },
            "voice": {"enabled": self.voice.enabled,
                      "elevenlabs_api_key": "set" if self.voice.elevenlabs_api_key else "EMPTY"},
            "watcher": {"enabled": self.watcher.enabled},
            "daemon": {"enabled": self.daemon.enabled,
                       "heartbeat_seconds": self.daemon.heartbeat_seconds},
            "worker": {"enabled": self.worker.enabled,
                       "allowed_actions": list(self.worker.allowed_actions)},
            "observation": {"enabled": self.observation.enabled,
                            "sensitive_excluded": self.observation.sensitive_excluded},
            "skills": {"enabled": self.skills.enabled,
                       "delegation_enabled": self.skills.delegation_enabled},
            "web_render": {"enabled": self.web_render.enabled,
                           "network_acquisition_enabled":
                               self.web_render.network_acquisition_enabled},
            "capability_forge": {"enabled": self.capability_forge.enabled,
                                 "auto_activation_enabled":
                                     self.capability_forge.auto_activation_enabled},
            "evolution": {"enabled": self.evolution.enabled},
            "research": {
                "enabled": self.research.enabled,
                "provider": self.research.provider,
                "exa_api_key": "set" if self.research.exa_api_key else "EMPTY",
                "tavily_api_key": "set" if self.research.tavily_api_key else "EMPTY",
            },
            "models": {
                "provider": self.models.provider,
                "api_key": "set" if self.models.api_key else "inherit",
                "roles": dict(self.models.roles),   # model id non e' segreto
            },
            "provider_hub": {"required": self.provider_hub.required},
        }


def _from_dict(d: dict) -> SeedConfig:
    cfg = SeedConfig()
    cfg.user_alias = d.get("user_alias", cfg.user_alias)
    for section, cls_field in (("llm", cfg.llm), ("voice", cfg.voice),
                               ("privacy", cfg.privacy), ("watcher", cfg.watcher),
                               ("evolution", cfg.evolution),
                               ("research", cfg.research), ("daemon", cfg.daemon),
                               ("worker", cfg.worker),
                               ("observation", cfg.observation),
                               ("skills", cfg.skills),
                               ("web_render", cfg.web_render),
                               ("capability_forge", cfg.capability_forge),
                               ("maintenance", cfg.maintenance),
                               ("provider_hub", cfg.provider_hub)):
        for k, v in d.get(section, {}).items():
            if hasattr(cls_field, k):
                setattr(cls_field, k, v)
    # models: sezione annidata (roles + policy), gestita a parte
    m = d.get("models")
    if isinstance(m, dict):
        cfg.models.provider = m.get("provider", cfg.models.provider)
        cfg.models.base_url = m.get("base_url", cfg.models.base_url)
        cfg.models.api_key = m.get("api_key", cfg.models.api_key)
        cfg.models.embedding_enabled = bool(
            m.get("embedding_enabled", cfg.models.embedding_enabled))
        cfg.models.embedding_model = m.get("embedding_model", cfg.models.embedding_model)
        if isinstance(m.get("roles"), dict):
            cfg.models.roles = dict(m["roles"])
        pol = m.get("policy")
        if isinstance(pol, dict):
            for k, v in pol.items():
                if hasattr(cfg.models.policy, k):
                    setattr(cfg.models.policy, k, v)
    return cfg


def config_path() -> Path:
    env = os.environ.get("SEED_CONFIG")
    if env:
        return Path(env)
    installed = forbidden.core_config_dir() / "config.json"
    if installed.exists():
        return installed
    return _REPO_CONFIG


def load() -> SeedConfig:
    path = config_path()
    if not path.exists():
        # primo avvio: copia il template nella posizione installata
        target = forbidden.core_config_dir() / "config.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if _REPO_TEMPLATE.exists():
            target.write_text(_REPO_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            path = target
        else:
            return SeedConfig()
    with open(path, encoding="utf-8") as f:
        return _from_dict(json.load(f))


def scrub_legacy_provider_keys(path: Path | None = None) -> bool:
    """Rimuove key single-provider in chiaro dopo migrazione al Provider Hub.

    Opera solo sul config installato sotto ``core_config``; non modifica template
    o config repository di sviluppo.
    """
    target = (path or config_path()).resolve()
    root = forbidden.core_config_dir().resolve()
    if target.parent != root or not target.exists():
        return False
    data = json.loads(target.read_text(encoding="utf-8"))
    changed = False
    for section in ("llm", "models"):
        value = data.get(section)
        if isinstance(value, dict) and value.get("api_key"):
            value["api_key"] = ""
            changed = True
    if not changed:
        return False
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    temp.replace(target)
    return True
