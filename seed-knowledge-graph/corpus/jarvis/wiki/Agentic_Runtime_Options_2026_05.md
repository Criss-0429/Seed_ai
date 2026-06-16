# Agentic Runtime Options 2026-05

**Ultimo Aggiornamento:** 2026-05-25  
**Rilevanza per JARVIS:** Alta - Scouting architetturale per decidere se continuare con OpenClaw, integrare Hermes/OpenHuman pattern o ridefinire il control/execution split.

Questa pagina sintetizza il confronto tra [[OpenClaw]], [[Hermes_Agent]], [[OpenHuman]], [[AgentMemory]], [[GStack]], [[Verdent_Manager_Harness]], [[OpenHarness]], [[MSA_Memory_Sparse_Attention]], [[Wan2GP]] e [[GLM_5]] come input per future decisioni JARVIS. Non promuove alcuna fonte a canonica.

## 1. Principio Decisionale

JARVIS non deve restare vincolato a OpenClaw se emerge una soluzione migliore. La regola pratica e':

- mantenere il Core JARVIS come owner di conversation-first UX, trust, privacy, audit, costi, device routing e capability registry;
- trattare OpenClaw/Hermes/OpenHuman/agentmemory come moduli o pattern da integrare selettivamente;
- evitare un "big bang replacement" se il nuovo sistema duplica memoria, provider, routing e execution senza rispettare i gate JARVIS;
- accettare refactor anche su codice gia' scritto quando abbassa rischio, costo o complessita operativa.

## 2. Matrice Sintetica

| Opzione | Valore migliore | Rischio | Uso consigliato |
|---|---|---|---|
| [[OpenClaw]] | runtime 24/7, execution gateway, daemon private | tende a diventare orchestratore troppo ampio | worker governato dietro capability registry |
| [[Hermes_Agent]] | provider routing, MCP filtering, gateway chat, memory providers, Home Assistant integration | sostituzione integrale duplicativa e invasiva | reference per adapter, routing e tool gateway |
| [[OpenHuman]] | onboarding memoria rapido, OAuth connectors, Memory Trees, TokenJuice | beta, GPL, forte lock-in di architettura memoria | pattern per ingest personale e memory UX |
| [[AgentMemory]] | MCP memory server condiviso, hooks, hybrid search, audit delete | duplicazione con memoria JARVIS Phase 27 | candidato laboratorio per coding memory |
| [[GStack]] | disciplina di delivery agentica, review, QA, release, retrospective | skill pack per coding, non runtime personale | workflow layer per agenti di sviluppo |
| [[Verdent_Manager_Harness]] | manager/executor, task board, parallel workers, workspace isolation | prodotto esterno/cloud e memoria non canonica | pattern per Task Graph IR, review queue e forge |
| [[OpenHarness]] | harness open-source con tools, skills, memory, governance, dry-run, swarm | tool/shell/memory ampi se installato senza sandbox | sandbox/reference per capability forge e dry-run |
| [[MSA_Memory_Sparse_Attention]] | direzione long-context 100M token end-to-end | richiede modello/infra, non plug-and-play | watchlist research per deep memory |
| [[Wan2GP]] | generazione video low VRAM | dominio media separato dal Core | futura media lane locale |
| [[GLM_5]] | agentic engineering e coding model refresh | modello enorme/cloud, deployment costoso | benchmark provider/model refresh |

## 3. Raccomandazione Per JARVIS

La soluzione piu conveniente non e' scegliere un solo framework. E' una composizione:

1. **Core JARVIS come governatore**: user intent, ack, status, final, trust/privacy, audit, model policy, cost policy, device routing.
2. **OpenClaw come worker privato**: inizialmente `openclaw.runtime_status` e poi capability singole READ/WRITE_SAFE allowlistate.
3. **Hermes come reference di tool gateway**: provider routing, MCP filtering, fallback, messaging gateway, Home Assistant toolset.
4. **OpenHuman come reference di memory onboarding**: compressione, sync locale, wiki/Memory Tree e OAuth connectors.
5. **AgentMemory come possibile coding-memory sidecar**: solo se non duplica la memoria personale e se passa governance/delete/audit.
6. **gstack come processo per agenti di sviluppo**: review, QA, browser checks, release discipline.
7. **Verdent/OpenHarness come harness pattern**: manager/executor, worktree isolation, permission hooks e dry-run entrano nel forge, non nel Core utente.

## 4. Decisioni Provvisorie

- Non mergiare PR OpenClaw che chiama il runtime remoto per ogni richiesta.
- Il primo gate OpenClaw deve restare READ-only e capability-specific.
- Le idee OpenHuman sono piu forti nella memoria che nell'execution: importare pattern, non runtime.
- Hermes e' piu maturo come integration catalog di OpenClaw, ma integrare Hermes intero ora rischia di spostare il centro di gravita fuori da JARVIS.
- agentmemory ha forte valore per coding agents, ma per dati personali deve restare subordinato al modello JARVIS di provenance, salience, suppression e writeback.
- Verdent conferma che task board, worker paralleli e review queue servono, ma JARVIS deve mantenerli dietro Task Graph IR, trust engine e audit.
- OpenHarness conferma il valore di dry-run, permission hooks e skill loading on demand; ogni import deve essere JARVIS-native o sandboxato.

## 5. Open Questions

- OpenClaw e Hermes possono convivere come worker distinti dietro lo stesso capability registry?
- OpenHuman puo' fornire solo il memory-ingest layer senza imporre il proprio assistant stack?
- AgentMemory puo' essere usato solo per coding memory, lasciando User Knowledge Store e Raw Episodes a JARVIS?
- Serve una fase dedicata "Runtime Option Benchmark" prima di attivare nuove capability reali.
- Serve una feature dedicata `FORGE-HARNESS-*` per confrontare Verdent/OpenHarness/GStack su fixture prima di affidare repo reali a worker paralleli?

## Relazioni

- [[OpenClaw]]
- [[Hermes_Agent]]
- [[OpenHuman]]
- [[AgentMemory]]
- [[GStack]]
- [[Verdent_Manager_Harness]]
- [[OpenHarness]]
- [[Jarvis_Agentic_Architecture]]
- [[Jarvis_Memory_Architecture]]
- [[Skill_Security_Audit]]

**Fonti:** `raw/scouting_2026_05_19_agentic_runtime_sources.md`; `raw/scouting_2026_05_25_harness_emotion_sources.md`.
