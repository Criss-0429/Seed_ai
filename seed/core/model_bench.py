"""S10.4 Benchmark riproducibile per ruolo.

SEED seleziona i modelli con un benchmark riproducibile, non per impressione
(doc `13`). Stesso corpus e budget per i candidati; nessun modello giudica se
stesso. Questo modulo e' il harness: un corpus minimo di task per ruolo con
validatori deterministici locali, eseguito tramite il `ModelRouter`. Funziona
offline contro fake; l'esecuzione con modelli reali (latenza/costo reali) resta
un'attivita' owner manuale.

Le metriche sono aggregate e per-ruolo: task, pass, errori, token. Nessun
contenuto delle risposte viene conservato.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from .llm import parse_json_object
from .model_router import (
    ROLE_CONVERSATION,
    ROLE_DESIGN_REVIEWER,
    ROLE_TOOL_BUILDER,
)


@dataclass
class BenchTask:
    role: str
    name: str
    messages: list[dict]
    check: Callable[[str], bool]
    response_json: bool = False


def _has_digit_four(text: str) -> bool:
    return "4" in text or "quattro" in text.lower()


def _is_json_object(text: str) -> bool:
    try:
        parse_json_object(text)
        return True
    except Exception:
        return False


def _has_verdict(text: str) -> bool:
    try:
        return parse_json_object(text).get("verdict") in {"pass", "fail", "inconclusive"}
    except Exception:
        return False


# Corpus minimo (doc `13`): conversazione fattuale, costruzione tool come JSON,
# review che deve emettere un verdict valido. Esteso dall'owner per i benchmark
# reali (conversazione ambigua, multi-file, injection, timeout...).
DEFAULT_CORPUS: tuple[BenchTask, ...] = (
    BenchTask(ROLE_CONVERSATION, "fattuale_diretto",
              [{"role": "user", "content": "Quanto fa 2+2? Rispondi col numero."}],
              _has_digit_four),
    BenchTask(ROLE_TOOL_BUILDER, "tool_contract_json",
              [{"role": "user", "content": "Restituisci SOLO un oggetto JSON con un campo 'name'."}],
              _is_json_object, response_json=True),
    BenchTask(ROLE_DESIGN_REVIEWER, "review_verdict_json",
              [{"role": "user", "content": "Rispondi con un oggetto JSON che contiene 'verdict'."}],
              _has_verdict, response_json=True),
)


@dataclass
class RoleMetrics:
    tasks: int = 0
    passed: int = 0
    errors: int = 0
    tokens: int = 0
    fallbacks: int = 0

    def as_dict(self) -> dict:
        return {
            "tasks": self.tasks, "passed": self.passed, "errors": self.errors,
            "tokens": self.tokens, "fallbacks": self.fallbacks,
            "pass_rate": round(self.passed / self.tasks, 3) if self.tasks else None,
        }


def run_benchmark(models, corpus: tuple[BenchTask, ...] = DEFAULT_CORPUS) -> dict:
    """Esegue il corpus tramite il ModelRouter. Salta i ruoli non configurati
    (li marca `skipped`). Ritorna metriche per-ruolo, mai contenuto."""
    metrics: dict[str, RoleMetrics] = {}
    skipped: list[str] = []
    for task in corpus:
        if not models.role_configured(task.role):
            if task.role not in skipped:
                skipped.append(task.role)
            continue
        m = metrics.setdefault(task.role, RoleMetrics())
        m.tasks += 1
        fb_before = models.fallbacks_used
        try:
            resp = models.invoke(task.role, task.messages,
                                 redacted=True, response_json=task.response_json)
            text = (getattr(resp, "text", "") or "")
            if task.check(text):
                m.passed += 1
            usage = getattr(resp, "usage", None)
            if isinstance(usage, dict):
                m.tokens += int(usage.get("total_tokens") or 0)
        except Exception:
            m.errors += 1
        m.fallbacks += models.fallbacks_used - fb_before
    return {
        "corpus_size": len(corpus),
        "roles": {role: m.as_dict() for role, m in metrics.items()},
        "skipped_roles": skipped,
    }
