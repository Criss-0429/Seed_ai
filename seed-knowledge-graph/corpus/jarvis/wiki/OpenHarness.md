# OpenHarness

**Ultimo Aggiornamento:** 2026-05-25
**Rilevanza per JARVIS:** Alta - reference open-source per agent harness, governance, skills, hooks, memory e swarm coordination.

OpenHarness e' un harness agentico Python con tool-use, skills, memoria, governance e coordinamento multi-agent. Include `ohmo`, un personal agent su canali chat. Per JARVIS e' utile come reference architetturale e benchmark, non come sostituzione del Core.

## 1. Core Value / Funzione Principale

OpenHarness mostra che un agente utile richiede infrastruttura intorno al modello:

- loop tool-call streaming;
- retry/backoff e parallel tool execution;
- tool file/shell/search/web/MCP;
- skill markdown caricate on demand;
- memory e session resume;
- permission modes e path/command rules;
- PreToolUse/PostToolUse hooks;
- approval dialog;
- subagent spawning, team registry e lifecycle background task;
- dry-run statico prima di esecuzione live.

## 2. Pattern Tecnici Da Estrarre

| Area | Pattern OpenHarness | Uso JARVIS |
|---|---|---|
| Tool surface | Toolkit ampio dietro harness | JARVIS deve esporre meta-tool e registry, non tool raw al modello |
| Skills | Markdown skills on demand | Skill JARVIS importate solo dopo audit e promozione |
| Governance | permission modes, command/path rules, hooks | Trust engine + capability policy + approval |
| Memory | MEMORY/session resume | Subordinata a Memory Plus: provenance, confidence, retention, delete |
| Swarm | subagent spawning e task lifecycle | Specialist Executor governato, no agente libero |
| Dry-run | readiness senza modello/tool/subagents | Preflight deterministico per capability forge e runtime |
| Channels | ohmo su Slack/Telegram/Discord/Feishu | JARVIS channel adapters privati, con stessa memoria/trust |

## 3. Integrazione con JARVIS

**Stato consigliato:** `sandbox-reference`.

Uso corretto:

- studiare struttura di harness e dry-run;
- confrontare con JARVIS `Capability Registry`, `Task Graph IR`, `Approval Loop`, `Audit Store`;
- importare idee, non pacchetti globali o hook senza security audit;
- usare come benchmark per agenti coding/forge, non per dati personali.

Uso da evitare:

- sostituire il Core JARVIS con `ohmo`;
- dare a un harness terzo accesso diretto a file personali o canali privati;
- duplicare memory store;
- abilitare shell/file tools generici senza allowlist.

## 4. Candidate Backlog

- `FORGE-HARNESS-002`: dry-run preflight per agenti coding, con output `ready/warning/blocked`.
- `FORGE-HARNESS-003`: permission hooks JARVIS-native per file/shell/tool.
- `FORGE-HARNESS-004`: team registry per worker/reviewer/verifier, ma con capability allowlist e budget.

## 5. Rischi

- Install script e agenti con shell/file access sono high-risk su repo reali.
- Memory/hook esterni possono persistere dati sensibili fuori dalla policy JARVIS.
- Chat-agent sempre attivo puo' bypassare approval se non integrato nel trust engine.
- Tool/MCP ampi aumentano superficie d'attacco e richiedono sandbox.

## Relazioni

- [[Verdent_Manager_Harness]] - pattern manager/executor e task board.
- [[Agent_Harness_Best_Practices]] - disciplina operativa agenti.
- [[Agentic_Runtime_Options_2026_05]] - valutazione runtime/harness.
- [[Skill_Security_Audit]] - gate obbligatorio prima di installare skill/hook/plugin.
- [[OpenClaw]] - worker privato candidato dietro capability registry.

**Fonti:** `raw/scouting_2026_05_25_harness_emotion_sources.md`; https://github.com/HKUDS/OpenHarness

