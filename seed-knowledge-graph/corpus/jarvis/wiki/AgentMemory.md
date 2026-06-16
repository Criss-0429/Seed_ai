# AgentMemory

**Ultimo Aggiornamento:** 2026-05-19  
**Rilevanza per JARVIS:** Media/Alta - Possibile sidecar di memoria per coding agents, MCP e hook, subordinato alla memoria personale JARVIS.

AgentMemory e' un sistema di memoria persistente per agenti di coding. Dichiara supporto per Claude Code, Cursor, Gemini CLI, Codex CLI, pi, OpenCode e client MCP. Il README lo posiziona come implementazione del pattern LLM Wiki con confidence, lifecycle, knowledge graph e hybrid search.

## 1. Valore Principale

- MCP server con molte tool di memoria e ricerca.
- Hook per agenti di sviluppo.
- Viewer e API REST.
- Hybrid search e knowledge graph.
- Policy di audit/delete dichiarata.
- Nessun database esterno obbligatorio secondo il README.

## 2. Uso Possibile In JARVIS

AgentMemory e' piu interessante come memoria per agenti di sviluppo che come memoria personale completa:

- ricordare bug, decisioni di codice, pattern di repo e regressioni;
- condividere contesto tra Codex, Jules, OpenCode, Hermes/OpenClaw worker;
- ridurre ripetizione durante refactor lunghi;
- alimentare search contestuale per PR review e CI debugging.

## 3. Rischi

- Potrebbe duplicare LLM Wiki, Raw Episodes, Entity Graph e Retrieval Store.
- Hook automatici possono scrivere memoria senza review se non governati.
- Per dati personali serve suppression/delete/audit compatibile con JARVIS.
- Prima di installare va passato da [[Skill_Security_Audit]] e capability registry.

## 4. Raccomandazione

Valutare in sandbox come **Coding Memory Sidecar**, non come memoria utente primaria. Primo esperimento possibile:

1. repo-only memory, nessun dato personale;
2. read/search attivo, writeback manuale;
3. MCP tool filtrati;
4. audit delete verificato;
5. confronto contro LLM Wiki + retrieval JARVIS.

## Relazioni

- [[Agentic_Runtime_Options_2026_05]]
- [[LLM_Wiki_v2]]
- [[M3_Memory]]
- [[Skill_Security_Audit]]
- [[Jarvis_Memory_Architecture]]

**Fonti:** `https://github.com/rohitg00/agentmemory`, `raw/scouting_2026_05_19_agentic_runtime_sources.md`.
