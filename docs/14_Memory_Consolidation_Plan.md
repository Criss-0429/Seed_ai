# 14 - Memory Consolidation Plan

> **Stato:** M1-M4 implementati e verificati; consolidamento sleep-time
> integrato con K4 Calibrazione. Gate owner invariati. La feature attiva e'
> ora D0 nel piano agentic daemon.

## Problema osservato

Smoke reale di Cristian (2026-06-12):

1. **Recall che dumpa il database.** Alla domanda "come sai che io corrisponda
   agli accelerazionisti?" SEED ha risposto con l'elenco esatto di tutte le
   preferenze. Causa: il normalizzatore LLM del command router classificava una
   domanda come intent `list_preferences` e ne imparava un alias permanente.
   **Gia' corretto** (fix bug): il recall parte solo da comando esplicito, mai
   indovinato dall'LLM; gli alias di recall appresi male vengono ripuliti
   all'avvio.
2. **Memoria non funzionante turno-su-turno e tra sessioni.** La cronologia chat
   (`_history`) vive solo in RAM: a ogni riavvio SEED dimentica la conversazione.
   La conoscenza dell'utente non viene estratta dalla conversazione (solo
   onboarding e reflection scrivono fatti), e i fatti entrano nel prompt con un
   taglio cieco `[:20]`, non per rilevanza.

## Relazione con la conoscenza cognitiva dell'utente

Questo piano e' il **substrato** (salva/recupera/consolida). Il modello cognitivo
dell'utente — cuore filosofico del progetto — vive in
`15_Cognitive_User_Knowledge_Plan.md` e si costruisce su questo substrato: i
claim tipizzati (M2), gli edge semantici e il retrieval pesato (M3) e il
consolidamento (M4) alimentano living profile, salienza e counterpoint.

## Fonti canoniche (LLM Wiki JARVIS)

Subordinate ai documenti SEED, ma autorevoli sul design memoria:

- `Jarvis_Memory_Architecture.md` - layer memoria, distinzione documenti vs
  modello dell'utente, tipi di memoria (biografica, relazione, routine, pattern,
  osservazione).
- `Jarvis_User_Knowledge_Ontology.md` - ontologia aperta: tipi di conoscenza
  (fatto, stato, routine, pattern, preferenza, relazione, eccezione, ipotesi,
  segnale affettivo, confine); regola "usa la conoscenza solo quando rilevante";
  "ipotesi != fatto".
- `Jarvis_Cognitive_User_Model_Execution_Harness.md` - claim tipizzati con
  provenance/confidence/valid-time; edge cognitivi tipati pesati temporali;
  retrieval relevance-scored ed esplicabile; determinismo prima del modello;
  "LLM non scrive fatti direttamente" (candidate -> review -> active);
  metacognitive budget (recall = depth 2, comando esplicito).

## Principi (non negoziabili per la memoria)

1. **Recall esplicito.** Una rilettura esatta del database avviene solo su
   comando esplicito dell'utente, mai come effetto collaterale di una domanda.
2. **Rilevanza prima del volume.** Nel contesto entra solo conoscenza pertinente
   alla richiesta corrente, selezionata in modo deterministico e spiegabile.
   "Se manca spiegazione, non entra nel workspace."
3. **Ipotesi != fatto.** Conoscenza inferita resta candidate, a bassa confidenza,
   con provenance, separata dai fatti dichiarati. Promozione governata.
4. **Determinismo prima del modello.** Schema, scope, recency, supersession,
   match entita: codice. LLM solo per interpretazione semantica e wording.
5. **Bi-temporalita'.** Non si cancella: si supera (`valid_to`/`superseded_at`).
   Il contesto storico resta interrogabile ma attenuato.
6. **Locale e privacy-first.** Tutto su SQLite locale; ogni testo gia' redatto
   dal privacy gate; nessun aggregato esce senza consenso.

## Fasi

### M1 - Memoria conversazionale funzionante (pragmatica)

Obiettivo: SEED ricorda la conversazione (anche dopo riavvio) e usa la
conoscenza pertinente, non un dump.

- persistenza cross-sessione: la cronologia chat viene ricaricata dagli episodi
  all'avvio;
- selezione per rilevanza deterministica (lexical overlap + recency) dei fatti/
  preferenze che entrano nel prompt, al posto del taglio cieco `[:20]`;
- recall esplicito (gia' fatto nel fix bug);
- nessuna nuova tabella: usa episodi/fatti/preferenze esistenti.

### M2 - Ontologia tipata della conoscenza

- tabella `knowledge` con `claim_type` (fact/state/routine/pattern/preference/
  relation/exception/hypothesis/boundary), `subject`, `value`, `confidence`,
  `confidence_source`, `scope`, `sensitivity`, `valid_from`/`valid_to`,
  `provenance` (episode ids), `lifecycle_state`, `review_state`;
- estrazione candidate dalla conversazione: l'LLM propone claim tipizzati
  (candidate-only), l'harness promuove solo con evidenza e confidenza; ipotesi a
  bassa confidenza separate dai fatti;
- supersession: un nuovo claim chiude il valid-time del precedente.

### M3 - Collegamento semantico (edge) e retrieval pesato

- edge tipati pesati temporali: `supports`, `contradicts`, `supersedes`,
  `attenuates`, `activates`, `inhibits`, `predicts`, `explains`, `co_occurs`,
  `depends_on`; ogni edge con weight, confidence, valid-time, provenance;
- retrieval combinato ed esplicabile:
  `score = lexical + graph_proximity + recency + confidence + scope_fit
  - sensitivity - stale - contradiction`; output con motivo della selezione;
- context-change invalidation (es. "mi sono trasferito" attenua routine vecchie).

### M4 - Consolidamento sleep-time (dream cycle reviewable)

- night job: raccoglie episodi non processati, estrae candidate, collega entita,
  rileva contraddizioni, aggiorna/crea edge, calibra ipotesi (predict-calibrate),
  rigenera la vista profilo, produce un digest reviewable;
- nessuna auto-promozione di conoscenza sensibile; owner gate.

## Acceptance per fase

- M1: la conversazione persiste tra riavvii; il recall esatto solo da comando;
  i fatti entrano per rilevanza; nessuna regressione S8/S9/S10; suite verde.
- M2: claim tipizzati con provenance/confidence; ipotesi mai promosse a fatto
  automaticamente; supersession verificata; LLM non scrive fatti diretti.
- M3: edge tipati persistiti; retrieval ordina ed espone il motivo; context
  change attenua il vecchio senza cancellarlo.
- M4: dream cycle produce digest reviewable, zero auto-promozione sensibile.

## Riferimenti esterni e decisioni (mem0, agentmemory, graphify, odysseus)

Analisi del report `agentmemory_mem0.docx` (giugno 2026) e delle pagine wiki
`AgentMemory`, `M3_Memory`, `Graphify`, `Odysseus`, `Jarvis_Memory_Architecture`.

### Lezione critica: lo staleness uccide la memoria, non il benchmark

- Mem0 v3 e' passato a **ADD-only** (accumulo monotonico, niente UPDATE/DELETE):
  benchmark sintetici alti (93-94%) ma **49% di accuracy reale dopo 30 giorni**,
  38% staleness, ~33% dei fatti errati entro 90 giorni. "Preferisco dark mode"
  poi "passo a light mode" -> entrambi persistono, il retrieval deve indovinare.
- **Decisione SEED:** mai accumulo cieco. Ogni nuovo claim passa da contradiction
  check + supersession bi-temporale (`valid_to`/`superseded_at`). SEED ha gia' le
  basi (tabella `facts` bi-temporale): e' il nostro moat anti-staleness. La
  metrica da tracciare e' lo **staleness rate**, non il benchmark.

### Cosa prendere da agentmemory (segmento local-first, vicino a SEED)

- modello "zero-config, zero-cost, zero-ops" su SQLite locale + embedding locali
  (all-MiniLM-L6-v2, 384d): **identico alla filosofia SEED**. Conferma la scelta
  (locale, privacy gate) contro il segmento cloud/Docker di Mem0;
- consolidamento **a 4 tier** (working/episodic/semantic/procedural) con decay
  Ebbinghaus, auto-forget e contradiction detection -> alimenta M4 dream cycle;
- retrieval **triple-stream** BM25 + vector + graph fusi con **Reciprocal Rank
  Fusion (K=60)**; config a 6 segnali pesati: semantic 0.30, lexical 0.12,
  spreading-activation 0.18, graph 0.18, node-importance 0.10, temporal 0.12 ->
  blueprint diretto per il retrieval di M3;
- dedup SHA-256 con finestra temporale; privacy pre-filter (SEED usa il privacy
  gate OPF, piu' forte).
- **Non adottare come dipendenza:** bus factor 91% single-maintainer, coupling
  con iii-engine, focus coding-agent. Prendiamo le idee, non il codice.

### Cosa NON prendere da Mem0

- cloud/Docker/Neo4j multi-container, costo, ADD-only staleness, graph store
  rimosso dall'OSS. Fuori dal modello locale-first di SEED.

### CoALA (4 tipi di memoria) come framing M2

working = `_history`; episodic = `episodes`; semantic = ontologia tipata (M2);
procedural = alias router + capability. M2 formalizza il layer semantico.

### Graphify (tool nostro) per M3

`graph.json` con nodi/edge tipati e confidence tag (EXTRACTED/INFERRED/
AMBIGUOUS) e' un **riferimento per il data-model degli edge** di M3 (tipati,
pesati, con confidenza). Graphify resta orientato a codice/docs (tree-sitter),
non alla memoria episodica conversazionale: utile come modello e per il grafo
SEED docs, non come store runtime della memoria utente.

### Odysseus / MemPalace

Odysseus (PewDiePie) = shell workspace local-first; la memoria e' solo un
componente opencode/MCP, nessun protocollo profondo da copiare (e tool shell piu'
permissivi, da filtrare). MemPalace = gerarchia mnemonica spaziale sperimentale,
bassa priorita'.

### Sintesi operativa per le fasi

- M2: ontologia tipata + **contradiction check + supersession** (anti-staleness).
- M3: retrieval triple-stream (lexical gia' in M1; +vector locale 384d +graph)
  fuso con RRF; edge tipati pesati temporali (taxonomy dell'harness cognitivo).
- M4: consolidamento 4-tier con decay/auto-forget reviewable.
- Metriche: staleness rate, contradiction rate, grounded accuracy, stale recall.

## Non-goals (in tutte le fasi salvo nota)

- profiling clinico o diagnosi; segnali affettivi vocali (appartengono a S11/
  voice e restano opt-in);
- upload cloud di memoria;
- promozione automatica di conoscenza sensibile;
- sostituire il privacy gate, il lineage o l'owner gate.
