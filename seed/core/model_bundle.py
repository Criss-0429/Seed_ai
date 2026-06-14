"""Resolve ML checkpoints bundled beside the onedir runtime."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MODEL_DIRS = {
    "privacy_filter": "privacy-filter",
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
    if bundle_root() is None:
        return False
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    return True
