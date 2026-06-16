"""Legge un file di testo (sola lettura) e ne ritorna il contenuto troncato.
Il riassunto vero lo fa il runtime via LLM (dopo privacy gate)."""

import json
import sys
from pathlib import Path

MAX_CHARS = 8000
DENY_TOKENS = (
    "\\windows",
    "\\program files",
    "ntuser.dat",
    ".ssh",
    "appdata\\roaming\\microsoft",
    ".env",
    "login data",
)


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    if payload.get("__dry_run__"):
        print(json.dumps({"ok": True, "dry_run": True}))
        return
    raw = (payload.get("path") or "").strip()
    low = raw.lower()
    if any(tok in low for tok in DENY_TOKENS):
        print(json.dumps({"error": "percorso non consentito"}))
        return
    p = Path(raw)
    if not p.is_file():
        print(json.dumps({"error": "file inesistente"}))
        return
    if p.stat().st_size > 5_000_000:
        print(json.dumps({"error": "file troppo grande (>5MB)"}))
        return
    try:
        text = p.read_text(encoding="utf-8", errors="replace")[:MAX_CHARS]
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        return
    print(
        json.dumps(
            {"ok": True, "name": p.name, "content": text, "truncated": p.stat().st_size > MAX_CHARS}
        )
    )


main()
