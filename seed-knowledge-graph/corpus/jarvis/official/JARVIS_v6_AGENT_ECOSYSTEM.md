# J.A.R.V.I.S. v6.3 - Ecosistema Agenti e Capability Forge

> **Ultimo aggiornamento:** 1 maggio 2026
> **Stato:** Documento architetturale canonico

Questo documento spiega **come convivono OpenClaw, n8n, Hermes, Jules, OpenCode, Codex, Claude Code e gli altri harness** dentro l'ecosistema JARVIS.

Obiettivo:
JARVIS deve poter **ampliare le proprie capacita in modo fluido**, senza richiedere ogni volta un lungo fermo macchina.

---

## 1. Principio Base

JARVIS non deve essere pensato come "un solo agente gigantesco".

Deve essere pensato come:
- un **runtime pubblico stabile**;
- un **sistema misto di workflow e delega**;
- un **forge di capacità** che costruisce, aggiorna e monta nuovi moduli.

In pratica:
- alcuni agenti parlano con l'utente;
- altri orchestrano;
- altri ancora costruiscono codice, skill, parser o workflow.

---

## 2. Ruoli Canonici dei Componenti

### 2.1 Runtime Core

| Componente | Ruolo canonico | Sempre attivo? |
|---|---|---|
| **OpenClaw** | cervello operativo, router, delega, trust coordination | si |
| **n8n** | workflow engine, scheduler, integrazioni, approval loop | si |
| **MCP servers** | standard tool boundary tra agenti e strumenti | si |
| **Ollama** | modelli locali e privacy lane | si |
| **M3 Memory / Wiki / Graph** | memoria, retrieval e writeback | si |
| **User Knowledge Engine** | fatti, stati, routine, pattern, preferenze, relazioni, ipotesi e confini | si |
| **Salience Engine** | scoring deterministico per memoria, proattivita, routing e ambient signals | si |

### 2.2 Capability Forge Harness

| Componente | Ruolo canonico | Sempre attivo? |
|---|---|---|
| **OpenCode** | harness open-source per prototipi di skill, plugin e patch locali | no |
| **Codex** | harness premium per sviluppo, manutenzione e implementazioni guidate | no |
| **Claude Code** | harness premium per refactor, review, code reasoning difficile | no |
| **Jules** | harness cloud per repo grandi, code execution GitHub-centric, run isolate | no |
| **Hermes** | harness opzionale per skill procedurali, backend remoti, tool-heavy side jobs | no |
| **Pi** | harness/SDK sperimentale per sub-agent workflow e automazioni locali | no |
| **Warp** | terminale/ADE human-in-the-loop per sviluppo, debug e supervisione agentica | no |

### 2.3 Servizi di Supporto

| Componente | Ruolo canonico |
|---|---|
| **LiteLLM / OpenRouter** | gateway modelli e controllo costi |
| **Tavily / Exa** | search layer esterno |
| **Bitwarden / SOPS** | segreti e capability config |
| **PostgreSQL** | capability registry, audit, workflow state |
| **Repomix** | context packaging selettivo per review e agent onboarding |
| **Skill Security Audit** | gate di sicurezza per skill, hook, plugin, MCP config esterni |
| **Meta-tool Proxy** | interfaccia minima per cercare/invocare capability senza esporre ogni tool al modello |
| **Ambient Adapters** | Home Assistant/MQTT/Matter/mobile/voice quando autorizzati |

---

## 3. Chi parla con l'utente e chi no

### Parlano con l'utente

- interaction shell
- OpenClaw, tramite i canali utente
- eventuali operatori esposti esplicitamente da OpenClaw

### Non parlano direttamente con l'utente nel loop normale

- OpenCode
- Codex
- Claude Code
- Jules
- Hermes

Questi harness lavorano **dietro le quinte** come:
- specialisti tecnici;
- operai del capability forge;
- sidecar di implementazione;
- ambienti di test e staging.

---

## 4. Architettura a Sezioni dell'Ecosistema

### 4.1 Sezione A - Runtime Pubblico

Qui vive il JARVIS che l'utente usa ogni giorno.

Responsabilita:
- ricevere richieste;
- rispondere subito;
- orchestrare task;
- proteggere dati sensibili;
- aggiornare memoria.

Componenti:
- OpenClaw
- n8n
- Ollama
- TTS/STT
- wiki/memoria/grafo

### 4.2 Sezione B - Workflow e Automazioni

Qui vivono le routine:
- cron job;
- digest;
- sync;
- mail/calendar/CRM workflows;
- approval gates.

Componente principale:
- n8n

### 4.3 Sezione C - Capability Forge

Qui JARVIS costruisce nuove capacita.

Uso tipico:
- creare un parser email;
- aggiungere un connettore Gmail/IMAP;
- creare un workflow per leggere preventivi;
- aggiungere un operatore per fare review o report.

Componenti tipici:
- OpenCode
- Codex
- Claude Code
- Jules
- Hermes

### 4.4 Sezione D - Premium Specialist Harness

Questa sezione va usata solo quando il task tecnico lo giustifica.

Uso tipico:
- refactor grande;
- costruzione di una nuova skill;
- pipeline multi-file;
- analisi tecnica complessa;
- design di integrazioni.

### 4.5 Sezione E - Knowledge e Capability Memory

Ogni nuova capacita deve lasciare traccia in:
- wiki
- grafo
- registry tecnico
- policy di sicurezza

Se JARVIS impara qualcosa ma non lo registra, la capacita non è davvero integrata.

### 4.5.1 Skill Intake e Risk Review

Cataloghi come Awesome Skills, Awesome LLM Skills e collezioni Claude Skills servono come scouting, non come installazione automatica.

Ogni skill esterna deve essere classificata prima dell'uso:
- esegue codice?
- invia dati fuori dal sistema?
- legge credenziali?
- installa hook o MCP globali?
- usa auto-update?
- modifica istruzioni persistenti come `AGENTS.md`, `CLAUDE.md`, settings o config?

Decisioni possibili:
- `reject`
- `watch`
- `sandbox`
- `staging`
- `active`

La promozione ad `active` richiede owner, versione, approval level, rollback e memory writeback.

### 4.5.2 User Knowledge Memory

La conoscenza dell'utente e' un sottosistema cognitivo, non una vista da mostrare sempre.

Deve distinguere:

- fatti;
- stati;
- routine;
- pattern;
- preferenze;
- relazioni;
- eccezioni;
- ipotesi;
- confini.

Esempi come palestra, pasti, universita, famiglia, partner, amici, pendolarismo o luci accese sono istanze possibili, non feature hardcoded.

Il flusso corretto e:

```text
evento -> salienza -> evidenza -> ipotesi -> maturazione -> conferma/policy -> adattamento
```

JARVIS usa questa conoscenza per decidere:

- come rispondere;
- quando tacere;
- quando proporre;
- quando agire;
- quando chiedere conferma.

### 4.6 Sezione F - Task Graph and Execution Trace

Ispirata a `microsoft/JARVIS`, questa sezione logica non e un harness separato ma un artefatto interno del runtime:
- piano compilato in nodi;
- dipendenze esplicite;
- risultati intermedi;
- trace esecutiva riutilizzabile.

Serve per:
- progress narration;
- debug admin;
- retry selettivi;
- capability registration;
- osservabilita del forge.

### 4.7 Sezione G - Context Packaging

Quando un harness esterno deve analizzare JARVIS, non deve ricevere automaticamente accesso illimitato al workspace.

Pattern raccomandato:
1. selezionare i path necessari;
2. escludere segreti, `.env`, chiavi, cache, binari e dati personali;
3. generare uno snapshot con Repomix o strumento equivalente;
4. far analizzare lo snapshot;
5. registrare insight utili nella wiki o nel capability registry.

Questo riduce rischio, token e rumore.

### 4.8 Sezione H - Personal Operating Ecosystem

JARVIS deve poter estendere l'agency oltre il computer:

- computer e filesystem;
- shell, browser, IDE e GitHub;
- calendario e mail;
- voce e mobile;
- smart home autorizzata;
- musica e scene;
- presenza e routine;
- studio, lavoro, creativita e riposo.

Questa sezione non richiede implementazione immediata completa. Definisce il perimetro finale e le interfacce che il capability forge deve poter aggiungere in modo sicuro.

### 4.9 Sezione I - Meta-tool Proxy

Il modello non deve vedere centinaia di tool.

Interfaccia canonica proposta:

- `search_capabilities`
- `get_capability_help`
- `invoke_capability`
- `invoke_capability_batch`
- `request_approval`
- `record_outcome`

I tool reali restano nel capability registry con owner, namespace, schema, risk class, approval level, test e rollback.

---

## 5. Flusso Canonico di "Capability Learning"

Caso utente:
**"Voglio che tu impari a leggere le mie mail e ricordalo da oggi in poi."**

Il flusso corretto e:

### Step 1 - Intent e consenso

OpenClaw:
- capisce che non e una semplice query;
- riconosce che si tratta di nuova capacita;
- chiarisce permessi, provider e perimetro.

### Step 2 - Capability Spec

JARVIS produce una specifica:
- sorgente mail (`Gmail API`, `IMAP`, `Microsoft Graph`, ecc.)
- scope richiesto
- formato di estrazione
- memoria target
- frequenza di sync
- limiti di sicurezza

### Step 3 - Harness Selection

OpenClaw sceglie l'harness piu adatto:
- **OpenCode** per scaffolding locale rapido
- **Codex** o **Claude Code** per implementazioni piu robuste
- **Jules** per lavori cloud su repo o branch isolati
- **Hermes** se serve una pipeline tool-heavy o remota

### Step 4 - Build in Staging

La nuova capacita non va montata subito in produzione.

Si costruisce in staging:
- parser
- connector
- workflow n8n
- wrapper MCP
- prompt pack
- test di lettura

### Step 5 - Security and Quality Validation

Prima dell'attivazione:
- test smoke
- test permessi
- test trust engine
- verifica logs e fallback
- security audit di skill/plugin/hook coinvolti
- quality gate: test, lint, review, evidenza esecutiva

### Step 6 - Registration

Se passa i test, la capacita viene registrata:
- capability ID
- versione
- owner
- secret dependency
- lane associato
- policy di approvazione

### Step 7 - Hot Load / Rolling Activation

Se il modulo e hot-reloadable:
- viene caricato senza fermare il runtime principale

Se richiede rolling restart:
- si riavvia solo il servizio interessato

### Step 8 - Memory Writeback

JARVIS aggiorna:
- wiki tecnica
- capability registry
- log operativo
- grafo relazioni

### Step 9 - User Confirmation

Solo a questo punto risponde qualcosa come:
"Ho aggiunto una nuova capacita per leggere le mail. Da ora posso usarla secondo le regole che abbiamo definito."

---

## 6. Hot Reload vs Restart

### Hot-reloadable per design

- workflow n8n
- skill markdown
- operator metadata
- prompt pack
- parser modulari
- connettori MCP
- regole di classificazione non core

### Rolling restart accettabile

- nuovi moduli backend
- estensioni router
- sidecar locali
- worker specialistici

### Da evitare come update "live" totale

- migrazioni distruttive
- modifiche al protocollo tra componenti core
- stravolgimento del trust engine
- cambi profondi a storage e secret layer

---

## 7. Come usare Hermes, Jules, OpenCode e gli altri

### OpenClaw

Uso corretto:
- orchestratore centrale
- routing
- delega operatori
- coordinatore capability forge

Non deve essere sostituito da altri harness nel loop utente.

### n8n

Uso corretto:
- event bus pratico
- workflow automation
- scheduling
- approval flow
- integrazione con servizi esterni

### Hermes

Uso corretto:
- laboratorio di skill procedurali
- task con molti tool e backend remoti
- side jobs sperimentali
- ambienti dove serve procedural memory forte

Uso scorretto:
- metterlo come unico cervello user-facing senza governance

### OpenCode

Uso corretto:
- prototipi rapidi di capability
- scaffolding locale
- build/test loop controllato
- skill e plugin development

### Codex

Uso corretto:
- sviluppo del progetto JARVIS
- manutenzione assistita
- patch strutturate
- documentazione tecnica e refactor ragionati

### Claude Code

Uso corretto:
- review e refactor difficili
- code reasoning premium
- escalation tecnica

### Jules

Uso corretto:
- esecuzione cloud o GitHub-centric
- task grandi separati dal runtime locale
- lavori tecnici dove conviene una sandbox remota

Uso scorretto:
- usarlo come base del runtime continuo di JARVIS

---

## 8. Capability Registry Minimo

JARVIS deve mantenere un registro formale delle proprie capacita installate.

Campi minimi consigliati:

| Campo | Significato |
|---|---|
| `capability_id` | identificatore univoco |
| `name` | nome umano |
| `version` | versione capability |
| `status` | draft, staging, active, disabled |
| `owner` | admin, runtime, operator |
| `entrypoint` | workflow, operator, connector, skill |
| `requires_secrets` | si/no + riferimenti |
| `approval_level` | read, write-safe, privacy, destructive, critical |
| `memory_writeback` | dove salva cosa ha imparato |
| `rollback_target` | versione o modulo precedente |

---

## 9. Governance della Self-Evolution

Self-evolution non deve significare anarchia.

Regole canoniche:

1. nessuna auto-modifica di moduli critici senza canary o review;
2. ogni nuova capacita deve avere owner, versione e rollback;
3. i segreti non devono mai entrare in prompt o wiki;
4. capability build e capability activation sono due fasi diverse;
5. il runtime pubblico deve restare disponibile anche mentre il forge lavora.

---

## 10. Conclusione

JARVIS deve poter:
- parlare con naturalezza;
- continuare a servire l'utente;
- imparare nuove procedure;
- scrivere nuovo codice;
- integrare nuovi connettori;
- ricordare come usarli;
- farlo senza richiedere ogni volta spegnimento completo.

Questa e la differenza tra un assistente che usa tool e un ecosistema agentico e che **si estende in modo governato**.
