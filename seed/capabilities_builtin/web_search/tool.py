"""Ricerca DuckDuckGo HTML. needs_network=true nel manifest: l'import di rete
e' consentito dall'audit e il broker ha chiesto il consenso network."""

import json
import re
import sys
import urllib.parse
import urllib.request


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    if payload.get("__dry_run__"):
        print(json.dumps({"ok": True, "dry_run": True}))
        return
    query = (payload.get("query") or "").strip()
    if not query:
        print(json.dumps({"error": "query vuota"}))
        return
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SEED/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            html_text = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        return
    results = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_text):
        title = re.sub(r"<[^>]+>", "", m.group(2))
        results.append({"title": title.strip(), "url": m.group(1)})
        if len(results) >= 5:
            break
    print(json.dumps({"ok": True, "results": results}, ensure_ascii=False))


main()
