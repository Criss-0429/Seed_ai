"""Test S10.4 benchmark harness: metriche per-ruolo, ruoli non configurati
saltati, token aggregati. Offline contro fake."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.model_bench import run_benchmark  # noqa: E402
from seed.core.model_router import (  # noqa: E402
    ROLE_CONVERSATION,
    ROLE_DESIGN_REVIEWER,
    ROLE_TOOL_BUILDER,
    ModelRouter,
)


class CorpusClient:
    """Risponde in modo plausibile per ruolo guardando il modello richiesto."""

    has_key = True

    def chat(self, messages, *, model=None, **kw):
        if model == "reviewer":
            text = json.dumps({"verdict": "pass", "violations": []})
        elif model == "builder":
            text = json.dumps({"name": "tool"})
        else:
            text = "Fa 4."
        return LLMResponse(text=text, usage={"total_tokens": 3})


def _full_router():
    return ModelRouter(CorpusClient(), {
        ROLE_CONVERSATION: "conv",
        ROLE_TOOL_BUILDER: "builder",
        ROLE_DESIGN_REVIEWER: "reviewer",
    })


def test_benchmark_all_roles_pass():
    out = run_benchmark(_full_router())
    assert out["skipped_roles"] == []
    for role in (ROLE_CONVERSATION, ROLE_TOOL_BUILDER, ROLE_DESIGN_REVIEWER):
        m = out["roles"][role]
        assert m["tasks"] == 1
        assert m["passed"] == 1
        assert m["pass_rate"] == 1.0
        assert m["tokens"] == 3


def test_unconfigured_roles_are_skipped():
    router = ModelRouter(CorpusClient(), {ROLE_CONVERSATION: "conv"})
    out = run_benchmark(router)
    assert ROLE_CONVERSATION in out["roles"]
    assert ROLE_TOOL_BUILDER in out["skipped_roles"]
    assert ROLE_DESIGN_REVIEWER in out["skipped_roles"]


def test_no_content_in_metrics():
    out = run_benchmark(_full_router())
    blob = json.dumps(out)
    assert "Fa 4" not in blob          # nessun contenuto risposta
    assert "verdict" not in blob
