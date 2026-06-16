# 15 - Cognitive User Knowledge Plan

> **Stato:** K1-K4 implementate e verificate; K2/K3 approvate verbalmente owner
> dopo reflection/report reali. Gate owner e checkbox invariati. La feature
> attiva e' ora D0 nel piano agentic daemon.

## Perche' e' il cuore del progetto

SEED non costruisce una copia dell'utente: costruisce una **personalita'
compatibile** = identita' SEED + **modello dell'utente** + storia della relazione
+ modalita' contestuale + self-narrative/counterpoint (README FrameworkUtenti,
`09_Personalita_Compatibile.md`). Il modello dell'utente e' quindi il punto
centrale, non un'aggiunta.

La memoria (M1-M4 in doc 14) e' il **substrato**: salva, recupera, consolida.
La **Cognitive User Knowledge (CUK)** e' il layer che trasforma quel substrato in
una comprensione governata dell'utente: chi e', cosa preferisce, come collabora,
dove SEED potrebbe leggerlo male — sempre con provenienza, confidenza,
correggibilita' e distinzione netta ipotesi/fatto.

## Fonti canoniche (LLM Wiki JARVIS, subordinate ai doc SEED)

- `Jarvis_User_Knowledge_Ontology.md` - ontologia aperta dei tipi di conoscenza;
  regola "usa la conoscenza solo quando rilevante"; "ipotesi != fatto"; sicurezza
  cognitiva.
- `Jarvis_Cognitive_User_Model_Execution_Harness.md` - loop osserva/pesa/capisce/
  dubita/corregge/tace-parla; claim tipizzati con valid-time; salienza; living
  profile rigenerato; counterpoint; predict-calibrate; determinismo prima del
  modello; "LLM non scrive fatti direttamente".
- `Jarvis_Memory_Architecture.md` - memoria biografica/relazione/routine/pattern/
  osservazione come modello dell'utente, non solo documenti.

## Principi non negoziabili (sicurezza cognitiva)

1. **Ipotesi != fatto.** Conoscenza inferita resta candidate, a bassa confidenza,
   con provenienza e controevidenza; non entra mai come istruzione di sistema.
2. **Routine != obbligo. Pattern != diagnosi.** Nessun profiling clinico.
3. **Usa la conoscenza solo quando rilevante**, e in forma spiegabile.
4. **Sensibile -> chiedi conferma.** Dati su salute, relazioni intime, confini
   personali non vengono usati per proattivita' senza consenso esplicito.
5. **La correzione dell'utente prevale** su qualunque inferenza, e cambia il
   grafo (supersession), non solo la risposta corrente.
6. **Determinismo prima del modello.** L'LLM propone candidate; l'harness
   promuove solo con evidenza, confidenza, scope e audit.
7. **Tutto locale, redatto, revocabile, esportabile.** Nessun profilo lascia il
   dispositivo.

## Relazione con le feature esistenti

- estende **S7 Onboarding** (raccolta iniziale redatta) e **S8 Compatible
  Personality** (identita' distinta, preferenze, storia relazionale aggregata,
  counterpoint): CUK rende il "modello dell'utente" evidence-based e longitudinale
  invece che limitato a onboarding + preferenze esplicite;
- consuma il substrato memoria: claim tipizzati (M2), edge semantici e retrieval
  pesato (M3), consolidamento sleep-time (M4);
- non anticipa i segnali affettivi vocali (S11 voice, opt-in): fuori scope qui.

## Fasi

### K1 - User Knowledge Ontology

Specializza i claim tipizzati di M2 al **modello dell'utente**. Dominio aperto
(identita'/situazione, luoghi/mobilita', relazioni, studio/lavoro, routine,
energia, preferenze, vincoli, valori) — gli esempi NON sono feature hardcoded.

Tipi: fatto, stato, routine, pattern, preferenza, relazione, eccezione, ipotesi,
confine. Ogni claim utente:

```text
claim_id, claim_type, subject, value, scope, sensitivity,
confidence, confidence_source, valid_from/valid_to, provenance(episode_ids),
lifecycle_state, review_state
```

Estrazione candidate-only dalla conversazione redatta; promozione governata;
ipotesi a bassa confidenza separate dai fatti. Contradiction check + supersession
bi-temporale (anti-staleness, vedi doc 14).

### K2 - Living Profile + Counterpoint

- **Living profile**: vista del modello utente **rigenerata** dai claim attivi
  (non patchata incrementalmente -> evita drift), versionata e reviewable;
  alimenta la "storia relazionale" del system prompt S8 al posto del riassunto
  statico attuale;
- **Counterpoint**: frammento esplicito su dove SEED potrebbe leggere male
  l'utente (pattern deboli, ipotesi non confermate), usato per restare prudente e
  per il dissenso motivato S8;
- le ipotesi non diventano mai istruzioni di personalita' (regola S7/S8 mantenuta).

### K3 - Salience / Awareness

- scoring di salienza **deterministico** (recurrence, duration, deviation dal
  baseline, recency, novelty, sensitivity penalty, stale/contradiction penalty)
  che decide cosa entra nel contesto e cosa resta "remember silently";
- governa la rilevanza del retrieval (si integra con M3) e, in prospettiva, la
  proattivita' (parla/chiedi/taci) — con default **silenzio** e costo di
  interruzione;
- output spiegabile: ogni elemento selezionato dichiara il motivo.

### K4 - Predict-Calibrate + safety gates

- ogni pattern maturo deve **predire** qualcosa (orizzonte, finestra di
  osservazione, costo se sbagliato); le predizioni vengono calibrate contro le
  osservazioni (Brier/ECE); pattern smentito -> confidenza giu', counterpoint su;
- gate anti-confabulazione: unknown/contradiction/stale/scope/privacy/sensitivity
  check; output del dubbio = answer/ask/verify/hold/silence;
- la correzione dell'utente esegue supersession + stale cascade.

## Contratti minimi

- `UserClaim` (sopra), append-only con supersession bi-temporale;
- `LivingProfile{version, generated_at, sections, source_claim_ids}`;
- `CounterpointFragment{topic, reason, confidence, source_claim_ids}`;
- `SalienceDecision{item_ref, score, reasons, action}`;
- audit locale aggregato; nessun testo del turno oltre la provenienza redatta.

## Acceptance per fase

- K1: claim utente tipizzati con provenienza/confidenza/valid-time; ipotesi mai
  promosse a fatto in automatico; correzione fa supersession; LLM non scrive
  fatti diretti.
- K2: living profile rigenerato dai claim (non patchato), versionato; counterpoint
  presente; le ipotesi non entrano nel prompt come istruzioni.
- K3: salienza deterministica e spiegabile; entra solo conoscenza rilevante;
  niente dump.
- K4: ogni pattern predice ed e' calibrato; sensibile -> chiede conferma;
  correzione prevale; nessun profiling clinico.

## Metriche

grounded accuracy, over-inference rate, source-missing rate, scope-violation
rate, stale-recall rate, prediction calibration (Brier/ECE), correction latency.

## Non-goals

- diagnosi o profiling clinico; tratti psicometrici stabili;
- segnali affettivi vocali (S11, opt-in, separato);
- proattivita' invasiva o non revocabile;
- profilo che lascia il dispositivo;
- promozione automatica di conoscenza sensibile.
