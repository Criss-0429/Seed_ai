"""Formatta il riepilogo giornata dai dati aggregati passati dal runtime."""

import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    if payload.get("__dry_run__"):
        print(json.dumps({"ok": True, "dry_run": True}))
        return
    try:
        usage = json.loads(payload.get("usage_json") or "{}")
    except json.JSONDecodeError:
        usage = {}
    if not usage:
        print(json.dumps({"ok": True, "digest": "Oggi non ho osservato attivita'."}))
        return
    lines = [
        f"- {cat}: {hours}h" for cat, hours in sorted(usage.items(), key=lambda kv: -float(kv[1]))
    ]
    print(
        json.dumps(
            {"ok": True, "digest": "La tua giornata:\n" + "\n".join(lines)}, ensure_ascii=False
        )
    )


main()
