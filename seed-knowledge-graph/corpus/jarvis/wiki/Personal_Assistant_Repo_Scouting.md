# Personal Assistant Repo Scouting

**Ultimo Aggiornamento:** 2026-05-25  
**Rilevanza per JARVIS:** Alta - scouting da repository del topic GitHub `personal-assistant`.

Questa pagina sintetizza il report `personal-assistant-repos.md` spostato in raw. Lo scouting non serve a scegliere una base da copiare: serve a estrarre pattern utili per la visione completa di JARVIS.

## 1. Repository osservati

| Repo | Pattern utile per JARVIS |
|---|---|
| Leon | modalita operative, tool layering, context-first, memory-first, owner profile |
| MIRIX | memoria multimodale, procedural/resource/knowledge vault, BM25 + vector |
| Memoh | agenti isolati, ACL, memory UI/admin, hybrid retrieval, snapshot |
| PocketPaw | event bus, AgentBackend protocol, security stack, audit log |
| OwnPilot | meta-tool proxy, namespaces, autonomy budgets, command center |
| Dicio Android | mobile/on-device assistant, comandi deterministici, privacy |
| Kalliope | trigger -> action DSL, automazioni non-LLM |
| Mycroft Core | skill ecosystem, message bus, config layered, lezioni storiche |
| Mark XXXIX-OR | planner/executor, task queue, screen awareness, desktop control e OpenRouter fallback come case study high-risk |

## 2. Pattern principali

### 2.1 Meta-tool proxy

JARVIS non deve esporre centinaia di tool direttamente al modello. Deve esporre pochi meta-tool:

- `search_capabilities`;
- `get_capability_help`;
- `invoke_capability`;
- `invoke_capability_batch`;
- `request_approval`;
- `record_outcome`.

I tool reali vivono in un capability registry con namespace, risk class, schema, owner, test e policy.

### 2.2 Operating modes

Ogni input dovrebbe essere classificato prima del modello:

- direct;
- workflow;
- agent;
- background;
- forge;
- proactive;
- observe;
- repair;
- admin.

Questo impedisce di usare agent loop quando bastano regole o workflow.

### 2.3 Isolamento e audit

Pattern da adottare:

- workspace isolato per task/agente;
- snapshot/restore;
- audit append-only;
- tool policy;
- budget di autonomia;
- approval mode per azioni rischiose.

### 2.4 Retrieval ibrido

Il retrieval finale non deve essere solo vettoriale:

- BM25/sparse per stringhe, ID, nomi;
- dense vector per significato;
- graph edges per relazioni;
- reranking/MMR;
- compaction e dedup periodici.

## 3. Implicazioni per JARVIS

Questi pattern rafforzano la direzione:

- JARVIS come ecosistema operativo personale, non chatbot;
- tool registry governato;
- capability forge controllato;
- proattivita' come processo interno;
- memoria aperta e correggibile;
- agenti autonomi solo con confini.

### 3.1 Nota 2026-05-25: Mark XXXIX-OR

La nuova fonte [[Mark_XXXIX]] conferma che gli assistant desktop "Jarvis-like"
tendono a convergere su voce, visione, controllo OS, memoria personale e
azioni modulari. Per JARVIS questo e' utile come mappa di desideri utente, ma
rafforza anche i gate: desktop control, screen/camera e terminal commands sono
capability high-risk, non scorciatoie da importare.

## 4. Relazioni

- [[Jarvis_Final_Feature_Vision]]
- [[Agentic_OS_Tooling_Evaluation]]
- [[Agent_Harness_Best_Practices]]
- [[Skill_Security_Audit]]
- [[Jarvis_Agentic_Architecture]]
- [[Mark_XXXIX]]

**Fonte raw:** `raw/GiustoDev_architecture/personal-assistant-repos.md`
