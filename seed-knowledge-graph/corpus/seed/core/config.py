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
    elevenlabs_api_key: str = ""   # VUOTA: STT/TTS restano disattivi
    voice_id: str = ""
    enabled: bool = False          # l'utente la attiva dall'app, se la key esiste


@dataclass
class PrivacyConfig:
    opf_checkpoint: str = ""       # vuoto = default ~/.opf/privacy_filter
    recall_bias: bool = True       # preset recall-oriented
    fail_closed: bool = True       # se il gate non e' pronto, NIENTE esce verso l'API


@dataclass
class WatcherConfig:
    enabled: bool = True
    poll_seconds: int = 5
    process_scan_seconds: int = 60
    excluded_apps: list[str] = field(default_factory=list)


@dataclass
class EvolutionConfig:
    enabled: bool = True               # False = istanza baseline per il controllo
    max_mutations_per_night: int = 2
    trait_cooldown_days: int = 2
    capability_dormant_days: int = 4
    capability_prune_days: int = 7


@dataclass
class SeedConfig:
    user_alias: str = "utente"     # alias scelto dall'utente, NON il nome reale
    llm: LLMConfig = field(default_factory=LLMConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    watcher: WatcherConfig = field(default_factory=WatcherConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)

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
            "evolution": {"enabled": self.evolution.enabled},
        }


def _from_dict(d: dict) -> SeedConfig:
    cfg = SeedConfig()
    cfg.user_alias = d.get("user_alias", cfg.user_alias)
    for section, cls_field in (("llm", cfg.llm), ("voice", cfg.voice),
                               ("privacy", cfg.privacy), ("watcher", cfg.watcher),
                               ("evolution", cfg.evolution)):
        for k, v in d.get(section, {}).items():
            if hasattr(cls_field, k):
                setattr(cls_field, k, v)
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
