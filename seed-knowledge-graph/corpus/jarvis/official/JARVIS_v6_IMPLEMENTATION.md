# J.A.R.V.I.S. v6.3 - Piano d'Implementazione

> **Ultimo aggiornamento:** 1 maggio 2026
> **Stato:** Documento operativo - Architettura di produzione

Questo piano recepisce cinque decisioni canoniche:
- JARVIS deve essere **conversation-first**
- il routing deve essere **multi-lane e cost-aware**
- le nuove capacita devono poter essere **aggiunte in modo modulare e con minimo downtime**
- la conoscenza dell'utente deve essere **evidence-based e ontologica**
- la proattivita deve essere **pensata, non generica**

---

## 1. Decisioni Architetturali Bloccanti

### 1.1 UX conversation-first

La UX non e un effetto collaterale del backend. E una responsabilita architetturale.

Ogni richiesta deve generare:
1. un ack immediato;
2. uno o piu update intermedi;
3. una risposta finale forte.

### 1.2 Gateway cloud unico

**OpenRouter** resta il gateway principale perche consente cambio modello rapido, fallback e controllo costi.

### 1.3 Search layer esterno

La ricerca web standard non deve vivere dentro il modello premium.

Scelta canonica:
- **Tavily** per la ricerca standard;
- **Exa** per ricerche piu profonde o orientate a docs/coding;
- provider-native search solo se giustificata.

### 1.4 Lanes canoniche

| Lane | Stack canonico |
|---|---|
| `privacy` | OpenAI Privacy Filter locale |
| `chat` | Gemini 3.1 Flash Lite |
| `research_fast` | gpt-oss-120b |
| `docs` | gpt-oss-120b |
| `coding` | Qwen3-Coder-Next |
| `coding_premium` | Kimi K2.5 |
| `fallback` | Llama 4 Scout |
| `manual_premium` | Claude Sonnet 4 |

### 1.5 Capability evolution live

Nuovi workflow, skill, parser, connettori e operatori devono poter essere aggiunti tramite moduli ricaricabili. Gli harness esterni servono a costruire queste capacita, non a sostituire il loop pubblico.

### 1.6 Task Graph interno

Ispirazione forte da `microsoft/JARVIS`:
- il piano non deve vivere solo come testo;
- deve poter essere serializzato in nodi con dipendenze;
- deve poter alimentare UI, audit, retry e capability forge.

### 1.7 User Knowledge Ontology

La conoscenza dell'utente non deve essere una lista di esempi hardcoded.

JARVIS deve distinguere:

- fatti;
- stati;
- routine;
- pattern;
- preferenze;
- relazioni;
- eccezioni;
- ipotesi;
- confini.

Questa conoscenza alimenta routing, memoria, tono, proattivita, routine e automazioni.

### 1.8 Proattivita e ambient intelligence

La proattivita nasce da salienza, evidenza e policy.

Azioni ambientali reversibili come luci o musica possono essere candidate all'autonomia graduale; azioni sociali, esterne, distruttive o sensibili restano sotto approval.

---

## 2. Componenti Da Stabilizzare

### 2.1 Interaction Plane

- frontend React/Electron
- status stream conversazionale
- audio in/out
- timeline di avanzamento

### 2.2 Control Plane

- n8n come orchestratore eventi e cron
- OpenClaw come cervello di routing e delega
- PostgreSQL per audit trail, workflow state e capability registry

### 2.3 Execution Plane

- Ollama
- Whisper
- Kokoro
- M3 Memory
- LLM Wiki
- Neural Composer
- filesystem locale

### 2.4 External API Plane

- OpenRouter
- Tavily
- Exa
- provider premium opzionali

### 2.5 User Knowledge Plane

- ontology store
- pattern evidence accumulator
- salience engine
- observation maturation
- proactivity queue interna
- privacy/confidence metadata

### 2.6 Ambient Plane

- Home Assistant/MQTT/Matter opzionali
- telefono/mobile presence
- music/scene adapters
- voice I/O
- routine and calendar signals

---

## 3. Roadmap Operativa

### Fase 1 - Conversation Shell e Routing Base

- [ ] trasformare gli stati tecnici in messaggi conversazionali canonici
- [ ] introdurre ack immediato separato dal task specialistico
- [ ] sostituire il vecchio routing lineare con lanes esplicite
- [ ] introdurre una rappresentazione `Task Graph IR` con `task`, `args`, `dep`, `lane`, `status`
- [ ] aggiornare `MODEL_MAP` sui modelli canonici
- [ ] aggiungere log dei costi per lane

### Fase 2 - Search Layer e Retrieval Pulito

- [ ] integrare Tavily come search standard
- [ ] predisporre Exa come search premium
- [ ] separare `search -> extract -> summarize -> answer`
- [ ] evitare che il modello premium faccia da search engine implicito
- [ ] introdurre endpoint o stream admin stile `/tasks` e `/results` per piano ed esecuzione

### Fase 3 - Coding e Document Workflows

- [ ] fissare `coding` su Qwen3-Coder-Next
- [ ] fissare `coding_premium` su Kimi K2.5
- [ ] introdurre lane `docs` per documentazione, report e preventivi
- [ ] aggiungere criteri oggettivi di escalation

### Fase 4 - Capability Forge

- [ ] introdurre un registro delle capacita installate
- [ ] definire cartelle target per workflow, operatori, connector e prompt pack
- [ ] consentire hot-load dei moduli non core
- [ ] definire rollback rapido dei moduli nuovi
- [ ] far produrre al forge anche descrizioni tool concise in stile EasyTool
- [ ] preparare suite di verifica capability ispirate a TaskBench

### Fase 5 - Governance e Sicurezza

- [ ] agganciare ogni nuova capacita al Trust Engine
- [ ] definire budget caps mensili e per lane
- [ ] collegare capability writeback a wiki e memoria
- [ ] limitare auto-modifica e self-hacking con canary e approval

### Fase 6 - User Knowledge e Proattivita

- [ ] definire schema `UserKnowledgeItem`
- [ ] introdurre tipi: fact, state, routine, pattern, preference, relationship, exception, hypothesis, boundary
- [ ] creare salience engine deterministico
- [ ] creare evidence accumulator per pattern ricorrenti
- [ ] distinguere ipotesi da fatti confermati
- [ ] introdurre observation maturation
- [ ] creare proactivity queue interna con reason/evidence/confidence/timing
- [ ] aggiungere suppression learning quando l'utente ignora o rifiuta proposte

### Fase 7 - Ambient e Life Context

- [ ] definire adapter policy per ambiente fisico autorizzato
- [ ] classificare azioni ambientali per rischio e reversibilita
- [ ] predisporre Home Assistant/MQTT come layer opzionale
- [ ] usare calendario/mobile/presenza come segnali, non come verita assoluta
- [ ] modellare scene: coding, sculpt, university, recovery, away-home, night-watch
- [ ] garantire opt-in, audit e correzione per dati sensibili

---

## 4. Capability Forge: cosa deve essere hot-reloadable

### Hot-reload consentito

- workflow n8n
- operatori OpenClaw
- prompt pack
- skill markdown
- parser ed extractor
- wrapper MCP
- connector esterni
- automazioni e scheduler

### Rolling restart accettabile

- nuove route backend
- cambio provider client
- moduli runtime Python/Node condivisi
- update del router

### Maintenance window richiesta

- migrazioni database distruttive
- refactor profondi di trust engine
- cambi al protocollo tra piani
- cambi a storage/secret layer

---

## 5. Harness e loro uso corretto

Gli harness esterni non sono tutti "il cervello". Devono essere usati per responsabilita diverse:

- **OpenClaw**: runtime operativo primario
- **n8n**: scheduler, workflow, automazioni, approval loop
- **Hermes**: harness opzionale per laboratori di skill, backend remoti e task procedurali avanzati
- **OpenCode**: harness open-source per capability prototyping e code tasks locali
- **Codex / Claude Code**: harness premium per sviluppo e manutenzione amministrativa
- **Jules**: harness cloud opzionale per code execution su repo grandi e workflow GitHub-centric

Dettaglio completo:
`JARVIS_v6_AGENT_ECOSYSTEM.md`

---

## 6. Esempio Canonico: "Impara a leggere le mie mail"

Quando l'admin chiede:
**"Voglio che tu impari a leggere le mie mail e ricordalo da oggi in poi."**

JARVIS deve:

1. chiarire il perimetro e i permessi;
2. generare una capability spec;
3. scegliere l'harness giusto per costruire il connector;
4. implementare parser, workflow e memoria associata;
5. testare in staging;
6. registrare la nuova capacita;
7. hot-caricare la capability;
8. continuare a restare operativo;
9. ricordare nella wiki come quella capacita si usa e dove vive.

Questo e il comportamento desiderato. 
Non un aggiornamento manuale "spegni, modifica codice, riavvia".

---

## 7. Rischi da tenere sotto controllo

| Rischio | Mitigazione |
|---|---|
| premium usato troppo spesso | guardrail per lane e cooldown |
| troppa ricerca nativa del modello | search layer esterno come default |
| prompt troppo grandi | retrieval mirato e compressione contesto |
| auto-modifica incontrollata | canary, rollback, trust engine |
| UX silenziosa | ack immediato e progress narration obbligatori |
| memoria incoerente | writeback strutturato su wiki, M3 e capability registry |
| inferenze personali sbagliate | distinguere ipotesi/fatto, chiedere conferma, mantenere confidenza |
| proattivita invadente | salience gate, cooldown, suppression learning, diritto al silenzio |
| automazioni ambientali rischiose | policy per rischio/reversibilita e approval dove serve |

---

## 8. Esito Atteso

Alla fine di questo piano, JARVIS deve risultare:
- naturale in conversazione;
- potente su task reali;
- sostenibile nei costi;
- espandibile per moduli;
- amministrabile senza downtime pesante per ogni nuova capacita;
- capace di conoscere l'utente senza trasformare ogni esempio in feature rigida;
- capace di estendersi all'ambiente fisico autorizzato con confini chiari.
