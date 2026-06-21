from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import model_bundle  # noqa: E402


def test_model_bundle_resolves_known_models_and_offline_is_opt_in(tmp_path, monkeypatch):
    root = tmp_path / "models"
    for name in ("privacy-filter", "emotion-wav2vec2", "embedding-mpnet"):
        (root / name).mkdir(parents=True)
    monkeypatch.setenv("SEED_MODEL_BUNDLE", str(root))
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("SEED_FORCE_OFFLINE", raising=False)

    assert model_bundle.resolve("privacy_filter") == str(root / "privacy-filter")
    assert model_bundle.resolve("superb/wav2vec2-base-superb-er") == str(
        root / "emotion-wav2vec2")
    # bundle presente -> True, ma offline NON forzato di default
    assert model_bundle.enforce_offline_if_bundled() is True
    assert "HF_HUB_OFFLINE" not in os.environ
    monkeypatch.setenv("SEED_FORCE_OFFLINE", "1")
    assert model_bundle.enforce_offline_if_bundled() is True
    assert os.environ["HF_HUB_OFFLINE"] == "1"


def test_unknown_model_is_not_rewritten(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_MODEL_BUNDLE", str(tmp_path))
    assert model_bundle.resolve("custom/model") == "custom/model"
