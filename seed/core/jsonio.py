"""Scrittura JSON atomica (tmp + replace), unica implementazione.

Lo stesso pattern era ripetuto in provider_hub, voice_credentials, config e
runtime_bench. `replace` e' atomico sullo stesso filesystem: niente file
mezzo-scritti se il processo muore a meta'.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path | str, data: Any, *,
                      ensure_ascii: bool = True, indent: int = 2) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=ensure_ascii, indent=indent),
                   encoding="utf-8")
    tmp.replace(path)
    return path
