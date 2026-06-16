# SEED Knowledge Graph

Specific graph corpus for SEED, connected to selected canonical JARVIS
documentation and subordinate LLM Wiki pages.

Generated artifacts live in `graphify-out/`:

- `graph.json`
- `GRAPH_REPORT.md`
- `graph.html`
- `jarvis-seed-merged.json` - merged with existing JARVIS application graph

Corpus source copies live in `corpus/`. They intentionally exclude secrets,
runtime data, logs, builds and unrelated JARVIS code.

The SEED-specific graph is also registered in Graphify global graph as
`seed-specific`, enabling cross-project traversal.

Regenerate using Ollama Cloud without writing the key to disk:

```powershell
$env:OLLAMA_BASE_URL = "https://ollama.com/v1"
$env:OLLAMA_MODEL = "gemma4:31b"
graphify extract corpus --backend ollama --model gemma4:31b --mode deep --out .
```
