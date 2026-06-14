"""Apre un'app per nome. Eseguito in sandbox; il permesso 'execute' e' gia'
stato concesso dal broker per questa app (scope = nome app)."""
import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    if payload.get("__dry_run__"):
        print(json.dumps({"ok": True, "dry_run": True})); return
    app = (payload.get("app") or "").strip().lower()
    if not app or any(c in app for c in r'\/:*?"<>|'):
        print(json.dumps({"error": "nome app non valido"})); return
    # 'start' di Windows risolve nome/alias senza path arbitrari
    import os
    if os.name != "nt":
        print(json.dumps({"error": "solo Windows"})); return
    rc = os.system(f'start "" "{app}"')  # noqa: S605 — app validata, scope autorizzato
    print(json.dumps({"ok": rc == 0, "app": app}))


main()
