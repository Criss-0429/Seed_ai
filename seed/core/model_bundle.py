"""Resolve ML checkpoints bundled beside the onedir runtime."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MODEL_DIRS = {
    "privacy_filter": "privacy-filter",
    "gliner_pii": "gliner-pii",            # backend privacy leggero (~300MB)
    "superb/wav2vec2-base-superb-er": "emotion-wav2vec2",
    "paraphrase-multilingual-mpnet-base-v2": "embedding-mpnet",
}


def bundle_root() -> Path | None:
    override = os.environ.get("SEED_MODEL_BUNDLE")
    if override:
        root = Path(override)
    elif getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent.parent / "models"
    else:
        return None
    return root if root.is_dir() else None


def resolve(model: str) -> str:
    root = bundle_root()
    dirname = MODEL_DIRS.get(model)
    if root is None or not dirname:
        return model
    target = root / dirname
    return str(target) if target.is_dir() else model


def enforce_offline_if_bundled() -> bool:
    """I modelli bundlati si caricano per path locale esplicito (vedi resolve),
    quindi NON serve forzare HuggingFace offline a livello globale: farlo
    impedirebbe il download on-demand dei modelli opzionali (embedding/emotion)
    non bundlati. L'offline duro resta attivabile via SEED_FORCE_OFFLINE=1."""
    bundled = bundle_root() is not None
    if bundled and os.environ.get("SEED_FORCE_OFFLINE") == "1":
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
    return bundled
