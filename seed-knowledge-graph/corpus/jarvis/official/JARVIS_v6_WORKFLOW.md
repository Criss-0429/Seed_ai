# J.A.R.V.I.S. v6.3 - Workflow Operativo

> **Ultimo aggiornamento:** 1 maggio 2026
> **Stato:** Documento operativo canonico

Questo workflow sostituisce il modello "ricevo la richiesta, lavoro in silenzio, poi rispondo" con un comportamento conversation-first.

**Regola canonica: JARVIS deve sempre sembrare presente.**

Nota v6.3:
questa regola vale per i task iniziati dall'utente. Nei processi interni di conoscenza, osservazione e proattivita', JARVIS deve anche saper tacere.

---

## 1. Obiettivo del Workflow

Ogni richiesta deve produrre tre risultati contemporanei:

1. **presenza conversazionale immediata**
2. **esecuzione specialistica accurata**
3. **tracciabilita di costi, decisioni e memoria**
4. **aggiornamento della conoscenza utente quando rilevante**

---

## 2. Ciclo di Vita Canonico di una Richiesta

### Fase 1 - Ricezione Input

JARVIS riceve testo, audio o altro payload da:
- frontend React/Electron;
- Telegram;
- trigger n8n;
- operatori interni;
- API admin.

### Fase 2 - Ack Immediato

Prima di fare lavoro pesante, JARVIS deve rispondere subito con una frase breve e naturale.

Esempi validi:
- "Certo, controllo subito."
- "Va bene, faccio una verifica accurata e ti aggiorno man mano."
- "Mi metto subito al lavoro; intanto raccolgo le fonti principali."

Questa fase usa:
- un path locale economico, oppure
- il lane `chat` a basso costo

**Non deve usare un modello premium.**

### Fase 3 - Privacy Gate

Il testo passa dal filtro locale:
- rilevazione PII;
- routing locale obbligatorio se compaiono file o dati sensibili;
- eventuale redazione/offuscamento;
- tagging della richiesta per il router.

### Fase 4 - Intent e Lane Selection

OpenClaw classifica la richiesta in una delle corsie canoniche:
- `chat`
- `research_fast`
- `docs`
- `coding`
- `coding_premium`
- `fallback`
- `manual_premium`

Qui vengono letti anche:
- budget lane;
- complessita stimata;
- stato memoria;
- urgenza;
- bisogno di search o tool.

### Fase 4.5 - User Knowledge Context

Prima del lavoro specialistico, JARVIS valuta se la richiesta o l'evento tocca conoscenza personale:

- fatti;
- stati;
- routine;
- pattern;
- preferenze;
- relazioni;
- eccezioni;
- ipotesi;
- confini.

Questa fase non deve produrre dashboard o notifiche. Produce contesto interno, salienza e possibili job di apprendimento.

Esempi:

- "sta saltando palestra" non e subito un fatto: puo essere una ipotesi;
- "lunedi' mattina universita" puo essere una routine se confermata;
- "dopo palestra risponde meno" puo diventare pattern solo dopo piu evidenze;
- "fidanzato/famiglia/amici" sono relazioni sensibili e richiedono prudenza.

### Fase 5 - Task Graph Compilation

Per le richieste semplici questa fase puo essere minima. Per le richieste complesse, OpenClaw deve compilare una rappresentazione esplicita del lavoro, ispirata al pattern di `microsoft/JARVIS`:
- `task`
- `args`
- `dep`
- `status`
- `lane`

Questo non serve solo al debug. Serve a:
- spiegare il lavoro all'admin;
- pilotare i progress update;
- riavviare singoli task senza rifare tutto;
- salvare il piano come artefatto del capability forge.

### Fase 6 - Retrieval e Search Planning

Prima del modello specialistico:
- lettura di `index.md` e pagine wiki rilevanti;
- query su M3 Memory;
- query sul knowledge graph;
- eventuale ricerca web via Tavily o Exa;
- compressione del contesto.

JARVIS deve inviare al modello solo il contesto che serve davvero.

### Fase 7 - Esecuzione Specialistica

Ora parte il lavoro vero:
- `chat`: risposta diretta o coordinamento;
- `research_fast`: confronto fonti e reasoning;
- `docs`: strutturazione di documento, stima, preventivo;
- `coding`: analisi, patch, test, refactor;
- `coding_premium`: refactor o progettazione tecnica piu difficile.

### Fase 8 - Progress Narration

Se il task supera la soglia rapida, JARVIS non resta muto.

Durante il lavoro deve emettere piccoli update:
- "Sto confrontando due fonti ufficiali."
- "Ho finito la raccolta delle fonti, ora sto sintetizzando."
- "Sto verificando il lato costi prima di chiudere."
- "Sto preparando una patch e poi controllo i test."

Questi aggiornamenti possono essere:
- testuali nella UI;
- vocali se il canale e audio-first;
- eventi di stato in `status` o `response_chunk`.

Per gli ambienti admin/debug e consigliata anche una vista stile:
- **task graph**
- **stage results**
- **final answer**

### Fase 9 - Trust Engine

Ogni azione passa nel filtro di sicurezza:

| Classe | Comportamento |
|---|---|
| **READ** | esecuzione automatica |
| **WRITE-SAFE** | esecuzione con audit trail |
| **PRIVACY** | redazione obbligatoria prima del cloud |
| **DESTRUCTIVE** | pausa + richiesta conferma |
| **CRITICAL** | bloccata o demandata all'admin |

### Fase 10 - Final Synthesis

Il risultato specialistico viene trasformato in risposta finale:
- coerente con il tono di JARVIS;
- leggibile;
- con conclusione chiara;
- con riferimenti o fonti se utili;
- senza metacommenti inutili.

### Fase 11 - Memory Writeback

Dopo la risposta:
- la cronologia utile entra in M3 Memory;
- eventuali nuove conoscenze vanno in wiki/grafo;
- le decisioni operative possono essere annotate in log o capability register.
- eventuali conoscenze personali entrano nella User Knowledge Ontology con tipo, evidenza, confidenza e confini.

### Fase 12 - Background Cognition

Dopo il turno utente, JARVIS puo' attivare processi interni:

- deduplica;
- collegamento grafo;
- pattern evidence accumulation;
- observation maturation;
- routine update;
- proactivity candidate generation;
- suppression learning;
- cost/security review.

Questi processi non parlano automaticamente all'utente. Producono azione solo se passano salience gate, privacy gate e timing gate.

---

## 3. Pattern Operativi Canonici

### 3.1 Richiesta di Ricerca

1. Ack immediato
2. Search planning
3. Task graph minimale
4. Tavily o Exa
5. Reasoning via `research_fast`
6. Update intermedi
7. Sintesi finale
8. Eventuale archiviazione in wiki

### 3.2 Richiesta di Coding

1. Ack immediato
2. Query su knowledge/code search
3. Task graph tecnico
4. Lane `coding`
5. Escalation a `coding_premium` solo se serve
6. Update intermedi
7. Patch/test/review
8. Risposta finale con esito e rischi

### 3.3 Richiesta di Documento o Preventivo

1. Ack immediato
2. Recupero contesto e vincoli
3. Task graph documentale
4. Ricerca se necessaria
5. Lane `docs`
6. Finitura opzionale
7. Output finale in formato pratico

### 3.4 Evento Ambientale o Routine

1. Evento ricevuto: luce, presenza, calendario, telefono, app attiva o routine.
2. Salience scoring deterministico.
3. Verifica privacy/autonomia.
4. Confronto con user knowledge.
5. Azione reversibile, richiesta conferma o silenzio.
6. Eventuale writeback come stato, routine, eccezione o ipotesi.

Esempio:
luce camera accesa + telefono fuori casa + calendario universita' attivo non significa "certezza"; significa probabile dimenticanza con confidenza calcolabile.

---

## 4. Esperienza Conversazionale Attesa

JARVIS deve:
- sembrare presente;
- sembrare al lavoro;
- non sembrare bloccato;
- non riversare addosso log tecnici inutili;
- non attendere la fine di tutto per parlare.

Formula pratica:

**ack breve -> lavoro visibile -> risultato forte**

---

## 5. Implicazioni Tecniche

Il backend deve supportare:
- stream di `status` conversazionale, non solo tecnico;
- chunk testuali brevi mentre il task e in corso;
- separazione tra lane veloce e lane specialistica;
- timeouts e fallback per evitare silenzi lunghi;
- logging dei costi per lane.

Il frontend deve supportare:
- badge di stato comprensibili;
- timeline dei progress update;
- eventuale lettura vocale dei passaggi importanti;
- continuita del thread anche mentre operano sub-agenti.
- superfici di audit/correzione per memoria e proattivita, non dashboard obbligatorie.

---

## 6. Implicazioni sui Costi

Questo workflow migliora la UX senza far esplodere il budget se:
- l'ack usa lane economico;
- i progress update non usano modelli premium;
- il lavoro pesante resta confinato alla fase specialistica.

Il costo non sta nel "parlare subito".
Il costo sta nel **quale cervello fai lavorare davvero**.

---

## 7. Collegamenti Canonici

- `../OVERVIEW.md`
- `JARVIS_v6_STACK.md`
- `JARVIS_v6_IMPLEMENTATION.md`
- `JARVIS_v6_AGENT_ECOSYSTEM.md`

Questo workflow formalizza il comportamento piu importante emerso dalla conversazione progettuale: **JARVIS deve essere insieme naturale, presente e tecnicamente stratificato**.
