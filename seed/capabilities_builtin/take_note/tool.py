"""Note locali nel workspace della capability (CWD impostata dalla sandbox)."""
import json
import sys
from datetime import datetime
from pathlib import Path

NOTES = Path("notes.jsonl")


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    if payload.get("__dry_run__"):
        print(json.dumps({"ok": True, "dry_run": True})); return
    action = payload.get("action", "list")
    if action == "save":
        text = (payload.get("text") or "").strip()
        if not text:
            print(json.dumps({"error": "nota vuota"})); return
        with NOTES.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                                "text": text}, ensure_ascii=False) + "\n")
        print(json.dumps({"ok": True, "saved": True})); return
    notes = []
    if NOTES.exists():
        for line in NOTES.read_text(encoding="utf-8").splitlines()[-50:]:
            try:
                notes.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    print(json.dumps({"ok": True, "notes": notes}, ensure_ascii=False))


main()
