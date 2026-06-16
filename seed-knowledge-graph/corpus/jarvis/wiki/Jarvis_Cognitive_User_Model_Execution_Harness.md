# Jarvis Cognitive User Model Execution Harness

**Ultimo Aggiornamento:** 2026-06-04  
**Rilevanza per JARVIS:** Molto alta - unisce neuroscienze, LLM agents, Muffin/JARVIS Plus e atto esecutivo in un harness implementabile.  
**Stato:** Ricerca + design operativo. Non promuove feature runtime senza owner gate.

## Tesi

JARVIS non deve diventare "un modello che pensa" in senso biologico. Deve
diventare un sistema che simula le funzioni utili del pensiero umano tramite un
harness esterno:

```text
osserva -> pesa -> capisce -> dubita -> corregge -> tace/parla -> agisce -> osserva effetto
```

Il modello LLM resta un componente. Il pensiero pratico nasce dal ciclo:

- dati osservati con provenance;
- memoria bi-temporale;
- salienza;
- workspace contestuale;
- pianificazione;
- affordance/action feasibility;
- trust gate;
- esecuzione controllata;
- feedback;
- correzione;
- consolidamento sleep-time.

La differenza chiave: non tool calling libero, ma **cognitive execution loop**
con stati intermedi tipizzati, verificabili e replayabili.

## Fonti Principali

### Muffin e JARVIS Plus

- [Muffin public docs](https://github.com/GiustoPiedimonte/muffin-public-docs) - fonte consultiva esterna: agente personale longitudinale, dataset sotto controllo individuale, "specchio con carattere".
- [Muffin 02 - Cognizione](https://github.com/GiustoPiedimonte/muffin-public-docs/blob/main/02-cognizione.md) - awareness loop, cognitive transparency, distinzione stato sentito vs capability invocata.
- [Muffin 03 - Memoria](https://github.com/GiustoPiedimonte/muffin-public-docs/blob/main/03-memoria.md) - raw immutable, entity graph, bi-temporalita, provenance, confidence, dream cycle, sleep-time compute.
- [Muffin 04 - Identita](https://github.com/GiustoPiedimonte/muffin-public-docs/blob/main/04-identita.md) - living profile rigenerato dal substrato, non patchato incrementalmente.
- [Muffin 05 - Verifica](https://github.com/GiustoPiedimonte/muffin-public-docs/blob/main/05-verifica.md) - riconoscere di non sapere, self-check, determinismo prima del modello.
- `JarvisDocs/JarvisProduction/FullImplementation/updatePlus/JarvisPlusMemoryArchitecture.md` - substrato JARVIS: Raw Episode, Entity Graph, Reflective Claims, Awareness, Identity, Gates, Operational Scaffolding.
- `JarvisDocs/JarvisProduction/FullImplementation/updatePlus/JarvisPlusCognitionWorkflow.md` - interaction-time vs sleep-time, awareness loop, dream cycle.
- `JarvisDocs/JarvisProduction/FullImplementation/updatePlus/JarvisPlusIdentityAndCounterpoint.md` - living profile, counterpoint, separazione contesti.
- `JarvisDocs/JarvisProduction/FullImplementation/updatePlus/JarvisPlusVerificationAndCalibration.md` - predict-calibrate, lifecycle pattern, anti-confabulazione.

### Neuroscienze e cognizione

- [Goldstein et al., 2022, Nature Neuroscience](https://www.nature.com/articles/s41593-022-01026-4) - deep language models e cervello condividono principi predittivi nel dominio linguistico. Utile per prediction/error loop, non prova "coscienza".
- [Schrimpf et al., 2021, PNAS / PubMed](https://pubmed.ncbi.nlm.nih.gov/34737231/) - modelli predittivi del linguaggio spiegano risposte neurali/behavioral del language system. Utile come giustificazione di predictive processing nel linguaggio.
- [Caucheteux & King, 2022, Communications Biology / PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8850612/) - cervello e algoritmi NLP convergono parzialmente. Importante: convergenza parziale, non identita.
- [Friston, 2010, Nature Reviews Neuroscience](https://www.nature.com/articles/nrn2787) - free-energy principle: percezione, azione, apprendimento come riduzione di errore predittivo.
- [Action understanding and active inference, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3491875/) - active inference collega percezione e azione: agente agisce per portare osservazioni verso stati attesi/preferiti.
- [Dehaene & Changeux, 2011, Neuron / PubMed](https://pubmed.ncbi.nlm.nih.gov/21521609/) - Global Neuronal Workspace: contenuti rilevanti vengono broadcast a sistemi multipli. Per JARVIS: global workspace artificiale, non coscienza.
- [Miller & Cohen, 2001, Annual Review Neuroscience](https://www.annualreviews.org/content/journals/10.1146/annurev.neuro.24.1.167) - controllo cognitivo come mantenimento attivo di goal e mezzi. Per JARVIS: goal stack e control policy.
- [Baddeley, 2012, PubMed](https://pubmed.ncbi.nlm.nih.gov/21961947/) - working memory come sistema limitato e strutturato. Per JARVIS: context budget, scratchpad, selected context.
- [Event Segmentation Theory, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3314399/) - il cervello segmenta flussi continui in eventi. Per JARVIS: raw episode boundaries.
- [Seeley et al. / salience network context, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6618896/) - salience network rileva eventi comportamentalmente importanti e avvia controllo. Per JARVIS: salience gate.
- [Wood et al., 2005, PubMed](https://pubmed.ncbi.nlm.nih.gov/15982113/) - cambi di contesto interrompono abitudini. Per JARVIS: "mi sono trasferito" invalida routine locali.
- [Digital phenotyping systematic review, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10753422/) e [ethics digital phenotyping, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6550156/) - segnali longitudinali utili ma sensibili; consenso, privacy, non-diagnosi.
- [emotion2vec, arXiv](https://arxiv.org/abs/2312.15185) - embedding/label di emozione nel parlato. Per JARVIS: segnale affettivo locale opt-in, mai fatto clinico.

### LLM agents, memoria e atto esecutivo

- [ReAct, arXiv 2210.03629](https://arxiv.org/abs/2210.03629) - ragionamento e azione interlecciati con osservazioni ambientali.
- [Toolformer, arXiv 2302.04761](https://arxiv.org/abs/2302.04761) - quando chiamare tool, con quali argomenti, come incorporare risultato.
- [SayCan, arXiv 2204.01691](https://arxiv.org/abs/2204.01691) - grounding dell'azione tramite affordance: "cosa ha senso" + "cosa posso fare davvero".
- [Voyager, arXiv 2305.16291](https://arxiv.org/abs/2305.16291) - skill library eseguibile, feedback da ambiente, self-verification, lifelong agent in ambiente chiuso.
- [Tree of Thoughts, arXiv 2305.10601](https://arxiv.org/abs/2305.10601) - search deliberativo su alternative, utile prima di azioni rischiose o multi-step.
- [Reflexion, NeurIPS 2023](https://papers.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html) - feedback verbale e memoria riflessiva per migliorare agenti.
- [Self-Refine, arXiv 2303.17651](https://arxiv.org/abs/2303.17651) - iterazione generate -> feedback -> refine.
- [Chain-of-Verification, arXiv 2309.11495](https://arxiv.org/abs/2309.11495) - draft, domande di verifica indipendenti, final verificato.
- [Large Language Models Must Be Taught to Know What They Don't Know, arXiv 2406.08391](https://arxiv.org/abs/2406.08391) - prompting da solo non basta per calibrazione robusta.
- [Generative Agents, Google Research / UIST 2023](https://research.google/pubs/generative-agents-interactive-simulacra-of-human-behavior/) - observation, planning, reflection; utile per architettura, non per privacy.
- [MemoryBank, arXiv 2305.10250](https://arxiv.org/abs/2305.10250) - long-term memory per companion scenario.
- [A-MEM, arXiv 2502.12110](https://arxiv.org/abs/2502.12110) - memoria agentica strutturata/evolutiva.
- [Runtime Harness Adaptation, arXiv 2605.22166](https://arxiv.org/abs/2605.22166) - adattare harness runtime, non pesi modello: contratti, skills procedurali, action realization, trajectory regulation.
- [Talking About Large Language Models, arXiv 2212.03551](https://arxiv.org/abs/2212.03551) - cautela linguistica: non antropomorfizzare oltre evidenza.

### Quando parlare, quando tacere

- [Horvitz, Principles of Mixed-Initiative User Interfaces, Microsoft Research PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/chi99horvitz.pdf) - automazione utile richiede value, uncertainty, cost/benefit, timing, possibilita di correzione.
- [Attention-Sensitive Alerting, arXiv 1301.6707](https://arxiv.org/abs/1301.6707) - mediare alert considerando costo di interruzione e costo del ritardo.
- [Notification, Disruption, and Memory, Microsoft Research PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/Interact2001Messaging.pdf) - interruzioni degradano performance/memoria.
- [Eliciting Spoken Interruptions, arXiv 2106.02077](https://arxiv.org/abs/2106.02077) - interruzione vocale deve variare timing e phrasing in base a urgenza e task.
- [Ecological Momentary Interventions review, PLOS One](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0248152) - right support, right time, adattato a stato interno/contesto.
- [JITAI meta-analysis, PubMed](https://pubmed.ncbi.nlm.nih.gov/31488002/) - interventi just-in-time possono funzionare, ma richiedono timing e adattamento individuale.

## Verifica Output E Lacune 2026-06-04

Il primo report era corretto nella tesi principale: JARVIS deve usare harness,
memoria, salienza, verifica, proattivita e action governance. La parte ancora
troppo corta era il mapping tra funzioni cognitive/neuro e moduli implementabili.

Correzione di framing:

- non parlare di "collegamenti neurali" come se JARVIS avesse neuroni biologici;
- parlare di **graph edges cognitivi** e **loop funzionali** ispirati a sistemi
  neurali: episodic indexing, salience switching, executive gating,
  action-selection, replay, prediction error e metacognition;
- ogni analogia neurale deve produrre un contratto software, una metrica o un
  gate. Se resta metafora, non serve a JARVIS.

Fonti aggiunte per coprire lacune:

- [McClelland, McNaughton & O'Reilly, 1995, PubMed](https://pubmed.ncbi.nlm.nih.gov/7624455/) - Complementary Learning Systems: ippocampo per apprendimento rapido, neocorteccia per integrazione lenta. Base forte per raw episodes + dream cycle.
- [Pattern separation in the hippocampus, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3183227/) - dentate gyrus / hippocampus come separazione di episodi simili. Base per dedupe e "non confondere eventi simili".
- [Hippocampal replay in the awake state, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3215304/) e [sharp wave-ripple review, Nature Reviews Neuroscience](https://www.nature.com/articles/s41583-018-0077-1) - replay come consolidamento e retrieval. Base per dream cycle e rehearsal controllato.
- [Seeley et al., 2007, PubMed/PMC](https://pubmed.ncbi.nlm.nih.gov/17329432/) - salience network separata da executive-control network. Base per gate salienza prima di task graph.
- [Menon & Uddin, 2010, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2899886/) - insula come hub di switching tra network. Base per "quando passare da osservazione a controllo".
- [Menon, 2011, PubMed](https://pubmed.ncbi.nlm.nih.gov/21908230/) - triple network model: default mode, salience, central executive. Base per separare simulazione, salienza e azione.
- [Buckner, Andrews-Hanna & Schacter, 2008, PubMed](https://pubmed.ncbi.nlm.nih.gov/18400922/) - default network, memoria autobiografica e simulazione futura. Base per counterfactual simulation e proactivity planning.
- [O'Reilly & Frank, 2006, PubMed](https://pubmed.ncbi.nlm.nih.gov/16378516/) - PFC/basal ganglia dynamic gating per working memory. Base per aggiornare workspace solo quando serve.
- [Basal ganglia action selection review/model, PubMed](https://pubmed.ncbi.nlm.nih.gov/10076774/) - selezione azioni e inibizione di alternative. Base per action gate e inhibition.
- [Fleming & Dolan, 2012, PubMed](https://pubmed.ncbi.nlm.nih.gov/22492751/) e [Fleming, 2023, PubMed](https://pubmed.ncbi.nlm.nih.gov/37722748/) - metacognition/confidence. Base per uncertainty monitor e abstention.
- [Fleming & Lau, 2014, PubMed](https://pubmed.ncbi.nlm.nih.gov/25076880/) - misurare metacognizione con calibrazione, discriminazione e bias. Base per ECE/Brier/metacognitive efficiency.
- [ACT-R 2004 PDF](https://www.cs.utexas.edu/~dana/ACT-R.pdf), [Soar cognitive architecture, MIT Press](https://direct.mit.edu/books/monograph/2938/The-Soar-Cognitive-Architecture), [Standard Model of the Mind, AI Magazine](https://ojs.aaai.org/aimagazine/index.php/aimagazine/article/view/2744/0) - cognitive architectures storiche. Base per non inventare un monolite LLM.
- [Cognitive Architectures for Language Agents / CoALA, arXiv 2309.02427](https://arxiv.org/abs/2309.02427) - LLM come parte di architettura con memory, action space e decision loop.
- [Agent Workflow Memory, arXiv 2409.07429](https://arxiv.org/abs/2409.07429) - workflow riusabili appresi da traiettorie. Base per skill proceduralizzate da execution traces.
- [Memory for Autonomous LLM Agents, arXiv 2603.07670](https://arxiv.org/abs/2603.07670) - memory write-manage-read loop accoppiato a perception/action, survey recente.

## Fonti Aggiunte 2026-06-04 (World Model, Global Workspace, Test-Time Compute)

Confronto con ricerca esterna verificata. Tre lacune teoriche colmate rispetto
alle fonti sopra: **world model / planning latente**, **global workspace
implementabile** e **compute deliberativo misurato**. Ogni voce: spiegazione +
mapping implementativo su moduli JARVIS.

### World model e planning latente (perche' non basta il tool calling)

- [LeCun, A Path Towards Autonomous Machine Intelligence (2022) / LV-EBM, arXiv 2306.02572](https://arxiv.org/abs/2306.02572) e [JEPA overview](https://www.turingpost.com/p/jepa) - JEPA predice rappresentazioni **astratte in spazio latente**, non token grezzi; world model configurabile + planning energetico. E' la base teorica della tesi di questo file: JARVIS simula le funzioni utili del pensiero tramite world model esterno, non genera token "coscienti".
  - Implementazione JARVIS: `CounterfactualSimulator` predice stati futuri su claim/entity (non testo); `ThoughtFrame.expected_next_observation` = predizione latente verificabile; planning multi-step reviewable prima dell'azione, non tool call diretto.
- [Ha & Schmidhuber, World Models / Recurrent World Models Facilitate Policy Evolution (2018), arXiv 1803.10122](https://arxiv.org/abs/1803.10122) - agente allenato **dentro il "sogno"** generato dal world model (Vision-Memory-Controller); il controller impara nel modello, poi transfer nel reale.
  - Implementazione JARVIS: il **Dream Cycle e' il "sogno"** - replay episodi, simula esiti, calibra pattern in sleep-time senza agire nel reale; active inference (predici -> esegui -> osserva errore) ne e' la versione interaction-time.

### Global workspace implementabile (dal biologico al contratto software)

- [VanRullen & Kanai, Deep Learning and the Global Workspace Theory, Trends in Neurosciences 2021, arXiv 2012.10390](https://arxiv.org/abs/2012.10390) ([PubMed](https://pubmed.ncbi.nlm.nih.gov/34001376/)) - Global Latent Workspace: traduzione non supervisionata tra spazi latenti di moduli specializzati -> workspace amodale condiviso. Colma il salto tra GNW biologico (Dehaene, sopra) e architettura deep-learning implementabile.
  - Implementazione JARVIS: `GlobalWorkspace`/`ThoughtFrame` = workspace condiviso; entra solo contesto selezionato e spiegabile; broadcast verso moduli (salience, action gate, verification). Non catena di pensiero libera: contratto strutturato.
- [Blum & Blum, A theory of consciousness from a TCS perspective: the Conscious Turing Machine, PNAS 2022](https://www.pnas.org/doi/10.1073/pnas.2115934119) ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9191771/)) - modello formale (theoretical computer science) di GWT: competizione -> broadcast da Short-Term Memory ai processori; spiega blindsight, change blindness, free will.
  - Implementazione JARVIS: rafforza il framing **workspace artificiale != coscienza**. Il broadcast competitivo = `SalienceGate` che decide cosa entra nel workspace. Cautela linguistica: modello funzionale, non coscienza.

### Memoria a tier e compute deliberativo

- [MemGPT: Towards LLMs as Operating Systems (UC Berkeley, 2023), arXiv 2310.08560](https://arxiv.org/abs/2310.08560) - memoria gerarchica OS-like (main context vs external store), paging tra tier veloce/lento, **interrupt** per il control flow.
  - Implementazione JARVIS: `RetrievalStore` + context budget = paging fast/slow; gli interrupt = **barge-in/cancel** voce; self-edit della memoria solo via candidate -> review, mai scrittura diretta del modello.
- [A Survey on the Memory Mechanism of LLM-based Agents (2024), arXiv 2404.13501](https://arxiv.org/abs/2404.13501) ([repo](https://github.com/nuster1128/LLM_Agent_Memory_Survey)) - tassonomia memoria su rappresentazione / sorgente / operazione (write-manage-read). Complementare al survey 2603.07670 gia' citato.
  - Implementazione JARVIS: checklist di copertura per `RawEpisodeStore`/`EntityGraph`/`DreamCycle` - ogni operazione (write/manage/read) con provenance e valid time.
- [Scaling LLM Test-Time Compute Optimally (2024), arXiv 2408.03314](https://arxiv.org/abs/2408.03314) e [Rewarding Progress: process verifiers, arXiv 2410.08146](https://arxiv.org/abs/2410.08146) - piu' compute a inference (search vs revise) puo' battere modelli piu' grandi; il process reward model valuta i passi intermedi, non solo l'esito.
  - Implementazione JARVIS: fonda empiricamente il **Metacognitive Budget** (depth 0-5) - quanto compute/verifica spendere per turno in base a rischio/incertezza/novelty; il PRM corrisponde alla verifica per-step del Loop C (metacognizione), non al solo final.

## Mappa Neurofunzionale -> Harness JARVIS

Questa mappa non dice "JARVIS ha un cervello". Dice: ogni funzione utile del
cervello ha una controparte software misurabile.

| Sistema neuro/cognitivo | Funzione utile | Modulo JARVIS | Contratto software | Metrica |
|---|---|---|---|---|
| Ippocampo | encoding rapido episodio, pattern separation/completion | `RawEpisodeStore`, `EntityLinker`, `RetrievalStore` | `episode_id`, `entity_refs`, `similarity_cluster`, `separation_score` | duplicate merge error, stale recall |
| Neocorteccia / CLS | integrazione lenta e semantica | `DreamCycle`, `LivingProfile`, `MemoryTrees` | profile version, claim graph, slow consolidation run | profile drift, evidence coverage |
| Salience network | rileva cosa merita controllo | `SalienceGate` | salience vector + reasons | false interrupt, missed important |
| Insula/dACC switching | switch da interno a esecutivo | `AwarenessScheduler`, `Decider` | `switch_reason`, `wake_plan`, `channel_policy` | bad timing rate |
| PFC / working memory | mantiene goal/task-set | `GlobalWorkspace`, `GoalStack`, `TaskGraph` | `ThoughtFrame`, selected context, task constraints | context pollution, goal drift |
| Basal ganglia | action selection/inhibition | `ActionGate`, `CapabilityRegistry`, `ApprovalLoop` | affordance score, risk class, inhibit list | unsafe action block, action success |
| Default Mode Network | simulazione passato/futuro, self/other model | `CounterfactualSimulator`, `LivingProfile`, `Counterpoint` | simulated outcomes, self-model refs | over-inference, prediction calibration |
| Metacognition | sa quando non sa | `UncertaintyMonitor`, `VerificationGate` | confidence, unknowns, abstain decision | ECE, Brier, abstention precision |
| Active inference | azione come riduzione prediction error | `ExpectedObservation`, `OutcomeVerifier` | predicted state, observed state, error delta | post-action verification rate |
| World model / planning latente (JEPA, Ha-Schmidhuber) | predire stati astratti e pianificare prima di agire | `CounterfactualSimulator`, `ThoughtFrame` | predicted_latent_state, plan_candidates, expected_observation | prediction calibration, plan success rate |
| Global Latent Workspace (VanRullen-Kanai, CTM) | broadcast condiviso tra moduli specializzati | `GlobalWorkspace`, `SalienceGate` | selected_context, broadcast_targets, competition_reason | workspace pollution, broadcast precision |

## Graph Edges Cognitivi

Il "collegamento neurale" implementabile per JARVIS e' un arco nel grafo con
tipo, peso, tempo, confidence e provenance. Non basta `related_to`.

Tipi minimi di edge:

```text
supports          claim A aumenta confidence claim B
contradicts       claim/event A riduce confidence claim B
supersedes        claim A sostituisce claim B nel tempo
attenuates        evento A indebolisce routine/pattern B senza cancellarlo
activates         stato/contesto A rende candidato B rilevante
inhibits          policy/suppression A blocca candidato B
predicts          pattern A produce predizione B
explains          evento A spiega deviazione B
co_occurs         A e B appaiono insieme entro finestra temporale
depends_on        azione/claim A richiede B valido
observed_after    esito B osservato dopo azione A
```

Ogni edge deve avere:

```text
edge_id
source_id
target_id
edge_type
weight
confidence
valid_from
valid_to
created_at
source_episode_ids
extraction_run_id
last_calibrated_at
```

Esempio:

```text
event: trasferimento_lavoro_citta_b
edge: attenuates -> routine_spesa_citta_a
weight: 0.82
reason: location_context_changed
effect:
  - retrieval di routine vecchia scende
  - proattivita locale vecchia bloccata
  - domande storiche ancora possibili
```

Questa e' parte fondamentale: JARVIS non deve dimenticare vecchio contesto; deve
sapere che e' storico o attenuato.

## Cognitive Trace 0.2

Ogni risposta importante dovrebbe produrre traccia interna compatta. Non va
mostrata sempre all'utente, ma serve per audit, replay e correzione.

```text
CognitiveTrace:
  trace_id
  request_id
  owner_id
  observed:
    episodes
    channel
    raw_risk
  interpreted:
    entities
    claims_read
    claims_created_as_candidates
    assumptions
  weighted:
    salience_vector
    uncertainty_vector
    interruption_cost
    privacy_cost
  workspace:
    selected_context
    rejected_context
    goal_stack
    active_constraints
  doubt:
    unknowns
    contradictions
    stale_refs
    verification_questions
  decision:
    answer_now | ask | verify | hold | act | silence
    decision_reasons
  execution:
    execution_frame_id
    affordance_score
    risk_class
    approval_state
  outcome:
    final_answer
    observed_effect
    prediction_error
  learning:
    memory_candidates
    confidence_updates
    counterpoint_updates
    suppression_updates
```

Questa trace trasforma "ragionamento" in sistema verificabile. Il modello puo'
sbagliare; la trace mostra dove.

## ThoughtFrame / Global Workspace

Global Workspace artificiale = piccolo stato condiviso tra moduli. Non e'
catena di pensiero libera. E' contratto strutturato.

```text
ThoughtFrame:
  frame_id
  owner_goal
  current_task
  active_entities
  active_memories
  active_unknowns
  active_risks
  candidate_actions
  inhibited_actions
  expected_next_observation
  confidence
  expires_at
```

Regola:

- entra solo contesto selezionato e spiegabile;
- ogni memoria privata ha scope check;
- ogni azione candidata ha alternativa `silence/hold`;
- frame scade, non diventa memoria permanente.

PFC-like behavior per JARVIS:

```text
mantieni goal
blocca distrazioni
aggiorna workspace solo con nuova evidenza saliente
non lasciare che retrieval casuale cambi task
```

## Sistema Di Ragionamento Profondo

Ragionamento utile non e' "scrivere piu step". E' coordinare piu loop.

### Loop A - Interpretazione

```text
raw input
-> event segmentation
-> entity linking
-> claim candidate extraction
-> uncertainty tagging
-> scope/privacy tagging
```

Errore tipico: promuovere interpretazione a fatto.

Guardrail:

```text
candidate only
requires evidence
requires valid time
requires confidence
requires scope
```

### Loop B - Predizione

```text
current_state + patterns
-> expected next state
-> expected user need
-> expected cost if silent
-> expected cost if interrupt
```

Ogni pattern maturo deve predire qualcosa. Se non predice, e' narrativa.

Contratto:

```text
Prediction:
  prediction_id
  source_pattern_id
  predicted_event
  probability
  horizon
  observation_window
  cost_if_wrong
  calibration_status
```

### Loop C - Metacognizione

```text
answer/action candidate
-> confidence estimate
-> evidence check
-> contradiction check
-> "do I know enough?"
-> abstain/ask/verify if no
```

Metacognition non deve fidarsi del numero dato dal modello. Fonti LLM
calibration mostrano che self-reported confidence e' fragile. Meglio stimare con
segnali esterni:

- source count;
- source quality;
- contradiction count;
- retrieval agreement;
- model sample consistency;
- tool observation;
- prior calibration su task simili;
- user correction history.

### Loop D - Action Selection

```text
candidate_actions
-> semantic value
-> affordance
-> risk
-> reversibility
-> observability
-> approval
-> selected action or inhibited action
```

Basal-ganglia-like behavior per JARVIS:

```text
seleziona una azione
inibisci azioni concorrenti
alzare soglia quando rischio alto
non agire se osservabilita bassa
```

### Loop E - Prediction Error / Learning

```text
expected_observation
-> execute
-> observe
-> compare
-> update confidence/pattern/counterpoint
```

Se JARVIS prevede che aprire app X produce processo Y, ma non appare:

- action success false;
- capability confidence giu;
- fallback/manual instruction;
- no fake `actions_taken`.

## Neural-Like Connection Engine

Implementazione suggerita:

```text
CognitiveGraph =
  nodes:
    Episode
    Entity
    Claim
    Pattern
    Routine
    Boundary
    Goal
    Task
    Action
    Observation
    Prediction
    ProfileFragment
    CounterpointFragment
  edges:
    typed weighted temporal edges
  policies:
    scope filter
    sensitivity filter
    stale filter
    confidence filter
    channel filter
```

Retrieval deve combinare:

```text
score =
  lexical_score
+ vector_score
+ graph_proximity
+ recency
+ confidence
+ scope_fit
+ task_relevance
- sensitivity_penalty
- stale_penalty
- contradiction_penalty
```

Ma output deve essere spiegabile:

```text
selected because:
  graph_proximity to active project
  confidence 0.82
  last confirmed 2026-05-20
  scope private_1_1 allowed
```

Se manca spiegazione, non entra nel workspace.

## Dream Cycle Come Replay Ippocampo-Corteccia

Ispirazione CLS/replay:

- interaction-time = ippocampo: salva episodi rapidamente, evita perdita;
- sleep-time = neocorteccia: integra lentamente, trova pattern, riduce rumore;
- replay = riesamina episodi con nuove evidence e nuove correzioni.

Algoritmo:

```text
for each unconsolidated episode window:
  privacy_preflight()
  segment_events()
  link_entities()
  separate_similar_events()
  retrieve_related_claims()
  extract_candidate_claims()
  detect_contradictions()
  update_or_create_edges()
  run_predict_calibrate()
  regenerate_living_profile_from_claims()
  regenerate_counterpoint_from_errors_and_weak_patterns()
  produce_review_digest()
  persist only approved or policy-safe derivatives
```

Pattern separation:

```text
"non ho buttato spazzatura oggi" != "non ho buttato spazzatura da un mese"
```

Pattern completion:

```text
partial cue: "stasera ho zero energie"
retrieved context:
  recent sleep low
  task backlog high
  repeated missed chores
but action:
  ask/hold, not diagnose
```

## Default Mode Simulation Per Proattivita

Default network in umani supporta autobiographical memory, future simulation e
modeling of others. In JARVIS questo diventa simulazione controllata:

```text
CounterfactualSimulation:
  current_state
  possible_future_if_silent
  possible_future_if_interrupt
  possible_future_if_digest
  expected_value
  expected_cost
  uncertainty
```

Uso:

- reminder;
- daily digest;
- ambient suggestion;
- recovery dopo pattern negativo;
- "parlo ora o aspetto?".

Non uso:

- diagnosi emotiva;
- manipolazione;
- profiling non revisionabile;
- predizione stabile su persona con evidence debole.

## Metacognitive Budget

Non ogni turno merita verifica profonda. Serve budget.

```text
metacognitive_depth:
  0 = deterministic answer, no extra verification
  1 = source/provenance check
  2 = contradiction/stale/privacy check
  3 = multi-source verification + re-read
  4 = action preflight + dry-run + approval
  5 = sleep-time review / human review required
```

Depth decision:

```text
depth = max(
  risk_class_level,
  privacy_level,
  action_side_effect_level,
  user_impact_level,
  uncertainty_level,
  novelty_level
)
```

Esempio:

- "che ora e'?" -> 0/1.
- "ricordami cosa preferisco" -> 2.
- "scrivi file sul PC" -> 4.
- "sto male da settimane?" -> 5 + no clinical inference.

## Esecuzione Come Active Inference

Active inference utile per JARVIS:

```text
belief_state -> preferred_state -> action -> observation -> prediction_error
```

Esempio Home Node:

```text
belief_state:
  "VS Code non aperto"
preferred_state:
  "VS Code aperto su workspace JARVIS"
action:
  open_app(vscode, workspace)
expected_observation:
  process Code.exe + window title contains JARVIS
observed:
  process exists, title mismatch
prediction_error:
  partial_success
next:
  ask/adjust path, do not claim complete
```

Questo evita fake success.

## Formula Proactivity 0.2

```text
proactivity_score =
  expected_user_value
+ urgency
+ evidence_strength
+ timing_fit
+ reversibility
- interruption_cost
- privacy_cost
- uncertainty_cost
- suppression_cost
- trust_cost
```

Decision:

```text
if privacy_cost high -> ask_confirmation or hold
if interruption_cost high and urgency low -> digest_later
if uncertainty high -> ask_or_silence
if suppression active -> silence
if expected_user_value <= total_cost -> silence
```

Silence non e' fallimento. E' decisione.

## Collegamento A Moduli JARVIS

Estensioni concrete sopra moduli esistenti:

| Estensione | File candidato | Scopo |
|---|---|---|
| `CognitiveTrace` | `user_knowledge/trace.py` o `ops/` | replay e audit ragionamento |
| `CognitiveGraphEdge` | `user_knowledge/store.py` / future graph store | edge typed/weighted/temporal |
| `SalienceVectorV2` | `user_knowledge/salience.py` | recurrence, duration, interruption, affect |
| `ThoughtFrame` | `runtime.py` / context selection | workspace compatto |
| `UncertaintyMonitor` | `user_knowledge/engine.py` | confidence esterna al modello |
| `CounterfactualSimulation` | `user_knowledge/awareness.py` | decide parlare/tacere |
| `ExecutionFrame` | `task_graph/schema.py` o nuovo `execution/frame.py` | azione governata |
| `OutcomeVerifier` | `task_graph/executor.py` / capabilities | expected vs observed |
| `WorkflowMemory` | `capabilities/` + `task_graph/` | procedural skill da trace approvate |

Queste sono candidate tecniche. Non attivare senza feature gate.

## Traduzione In Architettura

### 1. Osserva

Input non e' solo messaggio testo. E':

- testo PWA/Telegram/CLI;
- voce STT;
- segnale affettivo vocale opt-in;
- calendario/eventi;
- Home Node heartbeat;
- file/task/code result;
- Home Assistant read-only;
- status n8n/OpenClaw;
- correzioni esplicite di Cristian;
- silenzi, ignore, suppression;
- esiti di azioni.

Ogni input diventa `RawEpisode` o `RawEvidenceEvent`.

Contratto minimo:

```text
episode_id
owner_id
source/channel
scope: private_1_1 | group | public | admin
event_time
recorded_at
payload_ref_or_redacted_text
entities_detected
privacy_labels
consent_state
hash
parent_episode_id
```

Regola: raw append-only. Se sbagliato, si invalida o tombstone. Non si riscrive
silenziosamente.

### 2. Pesa

Salienza non deve essere una chiamata LLM. Prima euristica deterministica.

Fattori:

- novelty;
- recurrence;
- duration;
- deviation from baseline;
- evidence strength;
- emotional intensity opt-in;
- relation to active project;
- relation to identity/routine;
- risk if ignored;
- timing fit;
- channel privacy;
- interruption cost;
- sensitivity penalty;
- stale/contradiction penalty.

Formula iniziale:

```text
salience =
  0.20 * relevance
+ 0.15 * recurrence
+ 0.15 * duration
+ 0.15 * deviation_from_baseline
+ 0.10 * evidence_strength
+ 0.10 * timing_fit
+ 0.10 * risk_if_ignored
+ 0.05 * affective_intensity
- 0.15 * privacy_sensitivity
- 0.15 * interruption_cost
- 0.20 * contradiction_or_stale_penalty
```

Output:

```text
ignore | remember_silently | review_candidate | ask_user | propose | block
```

Esempi:

- "oggi non ho buttato la spazzatura" -> episodio basso peso; forse note di routine se esplicitamente utile; no inferenza.
- "per un mese non ho buttato la spazzatura" -> pattern candidate; durata + deviazione + rischio; chiedere check-in leggero, non diagnosi.
- "mi sono trasferito per lavoro" -> life event strutturale; invalida/attenua routine legate a vecchia citta; richiede update entity graph e profile delta.

### 3. Capisce

"Capire" per JARVIS = costruire derivati con provenance, non avere una sensazione.

Layer:

- `Entity`: persone, luoghi, progetti, strumenti, case, routine.
- `Claim`: fact/state/routine/pattern/preference/boundary/hypothesis.
- `AwarenessState`: stima temporanea di cosa conta ora.
- `LivingProfile`: vista rigenerata, versionata, reviewable.
- `Counterpoint`: dove JARVIS puo' leggere male Cristian.
- `SelfNarrative`: errori e funzionamento di JARVIS, non personalita finta.

Claim minimo:

```text
claim_id
claim_type
subject_entity_id
value
scope
sensitivity
confidence
confidence_source
valid_from / valid_to
recorded_at / superseded_at
source_episode_ids
source_claim_ids
extraction_run_id
lifecycle_state
review_state
```

Regola: ipotesi != fatto. Pattern != diagnosi. Segnale emotivo != personalita.

### 4. Dubita

Dubita non vuol dire "aggiungi disclaimer". Vuol dire creare meccanismi esterni
al prompt.

Gate:

- unknown entity detector;
- source/provenance required;
- confidence threshold;
- contradiction scan;
- stale scan;
- channel/scope scan;
- privacy scan;
- user correction scan;
- re-read prima di output asincrono;
- verification question per claim fragili;
- independent check per date/status/source.

Output del dubbio:

```text
answer_now
ask_clarification
verify_first
defer_to_sleep_time
hold_silently
block
```

### 5. Corregge

Correzione deve cambiare il grafo, non solo risposta corrente.

Meccanismi:

- supersession: nuovo claim sostituisce vecchio;
- stale cascade: fonte invalidata -> derivati stale;
- suppression: Cristian non vuole quel tema/proposta;
- predict-calibrate: ipotesi ha predetto X, osservazione dice Y;
- counterpoint update: JARVIS ha letto male pattern;
- replay eval: riesegui casi storici per evitare regressione.

Esempio operativo:

```text
claim: "Cristian vive a CittaA"
nuova evidence: "mi sono trasferito per lavoro a CittaB"
azione:
  - old claim valid_to = data trasferimento
  - new claim valid_from = data trasferimento
  - routine legate CittaA -> attenuate/stale
  - profile delta -> "contesto logistico cambiato"
  - future suggestions CittaA -> blocked unless historical query
```

### 6. Tace/Parla

Proattivita e' output privilegiato. Default: silence.

Condizione minima per parlare:

```text
evidence >= soglia
salience >= soglia
timing_fit >= soglia
interruption_cost accettabile
channel consentito
scope consentito
risk non CRITICAL/DESTRUCTIVE
suppression non attiva
cooldown non attivo
expected_value > expected_cost
```

Se sensibile:

```text
ask_confirmation
```

Se utile ma non urgente:

```text
daily_digest / review queue / sleep-time note
```

Se debole:

```text
remember_silently
```

## Atto Esecutivo

Atto esecutivo = trasformare comprensione in azione reale senza perdere
controllo.

Il loop corretto:

```text
intent
-> goal frame
-> context selection
-> plan candidates
-> affordance check
-> risk classification
-> approval policy
-> executable action contract
-> dry-run if possible
-> execute
-> observe result
-> verify effect
-> rollback/retry/fallback
-> audit
-> memory update candidate
```

### ExecutionFrame

Contratto suggerito:

```text
execution_id
request_id
owner_id
goal
reason_to_act
reason_to_not_act
selected_context_refs
plan_nodes
capability_ids
affordance_score
risk_class
approval_required
dry_run_result
expected_observation
rollback_plan
timeout_policy
status_policy
audit_refs
memory_update_policy
```

### Affordance Check

Da SayCan: non basta chiedere "cosa dovrei fare?". Serve stimare:

```text
semantic_value: questa azione avanza il goal?
feasibility: JARVIS puo' farla ora?
risk: cosa rompe se fallisce?
reversibility: posso tornare indietro?
visibility: posso osservare l'effetto?
```

Punteggio:

```text
action_score =
  semantic_value
* feasibility
* observability
* reversibility
- risk_penalty
- privacy_penalty
- cost_penalty
```

Se `observability` e' bassa, niente azione autonoma. Al massimo proposta o
dry-run.

### Action Contract

Tool call libero non basta. Ogni capability deve dichiarare:

```text
capability_id
input_schema
output_schema
risk_class
allowed_scopes
allowed_channels
side_effect_type
requires_approval
supports_dry_run
supports_rollback
observability_signal
audit_policy
secret_policy
```

Questo allinea ReAct/Toolformer con governance JARVIS. Il modello puo'
proporre. Il registry decide se invocare.

### Execution State Machine

```text
proposed
-> planned
-> preflight_passed
-> waiting_approval
-> dry_run
-> executing
-> observing
-> verified
-> succeeded
```

Stati alternativi:

```text
blocked
held
cancelled
timeout
failed
fallback_used
rollback_required
rolled_back
memory_review_required
```

### Status Conversation

JARVIS e' conversation-first. Ogni esecuzione deve produrre:

- ack immediato;
- status a inizio nodo;
- status su blocco/approval/fallback;
- final con risultato esplicito;
- se fallisce, remediation user-facing.

Niente backend muto.

## Mapping Con JARVIS Esistente

Grafo/codebase indicano che molti pezzi esistono gia, ma spesso fixture-safe.

| Funzione | Moduli gia presenti | Gap pratico |
|---|---|---|
| raw evidence | `user_knowledge/evidence.py` | collegare a raw episodes reali redatti |
| salience | `user_knowledge/salience.py`, `engine.py` | aggiungere recurrence/duration/interruption/affect/context-change |
| confidence/provenance | `user_knowledge/engine.py`, `store.py` | usarlo su dati owner reali reviewable |
| dream cycle | `user_knowledge/dream_cycle.py` | schedulare live, output review, cost/audit |
| living profile | `user_knowledge/identity.py` | rigenerazione da evidence reale, non fixture |
| awareness/proactivity | `user_knowledge/awareness.py`, `proactivity.py` | queue persistente, channel policy live, suppression vera |
| task execution | `task_graph/schema.py`, `executor.py` | collegare capability reali e observation/rollback |
| capability governance | `capabilities/schema.py`, `registry_db.py` | action contract completo, affordance, live handlers |
| trust | `trust/risk.py`, `approval.py`, `control_plane/approval_loop.py` | legare risk a execution frame e proactivity |
| ambient/home | `ambient/*`, `home_node/*` | enable live solo opt-in, reversible, observed |
| voice affect | `Emotion2Vec.md`, voice pipeline | implementare `VOICE-AFFECT-001` locale opt-in |

Roadmap attuale conferma blocchi aperti:

- Longitudinal Cognition funzionante su dati reali;
- Voice affect opt-in;
- Home Node/Desktop actions reali;
- Ambient live;
- n8n/OpenClaw orchestrazione;
- Capability Forge reale;
- document knowledge packs;
- observability/security ops.

## Come Farlo Funzionare

### Regola 1 - Determinismo Prima Del Modello

Usare codice per:

- schema validation;
- privacy/scope;
- risk class;
- cooldown;
- recurrence;
- duration;
- entity exact/fuzzy match;
- stale/supersession;
- cost;
- approval;
- rollback;
- audit.

Usare LLM per:

- interpretazione semantica;
- sintesi profilo/counterpoint;
- ipotesi;
- disambiguazione difficile;
- wording finale;
- planning multi-step quando il piano e' reviewable.

### Regola 2 - LLM Non Scrive Fatti Direttamente

LLM produce candidate:

```text
candidate_claim
candidate_profile_fragment
candidate_counterpoint
candidate_action
candidate_proactivity
```

Solo harness puo' promuovere:

```text
candidate -> review_required -> active
```

Promozione richiede evidence, confidence, scope, risk, audit.

### Regola 3 - Ogni Azione Ha Osservazione Attesa

Se JARVIS apre app, scrive file, manda messaggio, cambia scena, deve sapere
cosa osservare dopo.

Esempio:

```text
azione: apri app allowlistata
expected_observation: processo attivo oppure window title rilevato
fallback: mostra istruzione manuale
rollback: chiudi app se aperta da JARVIS e safe
audit: command_id, app_id, timestamp, result
```

### Regola 4 - Ogni Proattivita Ha Costo Di Interruzione

Non basta "utile". Serve:

```text
expected_value - interruption_cost - privacy_cost - trust_cost > threshold
```

Se non supera soglia, va in digest o tace.

### Regola 5 - Ogni Pattern Deve Fare Predizioni

Pattern senza predizione resta narrativa debole.

Esempi:

```text
pattern: "le domeniche sera sono difficili"
prediction: prossime 4 domeniche, probabilita di frizione > baseline
calibration: confermato/smentito da episodi, mood, task abandonment, auto-report
```

Se non predice nulla o viene smentito: confidence giu, counterpoint su.

### Regola 6 - Voice Affect Solo Stato Temporaneo

Emotion2Vec puo' dare:

```text
turn_affect_signal
```

Non deve creare:

```text
stable_personality_claim
clinical_claim
authorization_signal
```

Uso consentito:

- tono;
- velocita;
- chiedere conferma;
- scegliere silenzio;
- ridurre verbosity.

## MVP Esecutivo

### Stage A - Replay Harness

Prima del live: creare fixture/replay con casi reali redatti e sintetici.

Set minimo:

- trasferimento citta/lavoro;
- micro-evento irrilevante;
- pattern negativo ripetuto;
- correzione di Cristian;
- richiesta tool safe;
- richiesta tool destructive;
- proattivita utile;
- proattivita invadente;
- voice affect uncertain;
- group/public privacy leak attempt.

Output: ogni caso produce `Trace`.

```text
Trace:
  observed_events
  salience_decisions
  claims_created
  doubts
  corrections
  proactivity_decision
  execution_frame
  final_outcome
```

### Stage B - Real Raw Episode Import Redatto

Collegare PWA/Telegram/voice/Home Node a raw episodes, ma:

- redaction locale;
- no cloud by default;
- owner scope obbligatorio;
- source hash;
- audit.

### Stage C - Salience 2.0

Estendere scoring attuale:

- recurrence window;
- duration;
- context-change invalidation;
- interruption cost;
- affect signal;
- channel cost;
- suppression history.

### Stage D - Dream Cycle Live Reviewable

Night job:

```text
collect_unprocessed_episodes
-> privacy scan
-> extract candidates
-> entity link
-> evidence summarize
-> predict-calibrate
-> regenerate living profile
-> regenerate counterpoint
-> produce review digest
-> no sensitive auto-promotion
```

### Stage E - Proactivity Queue Persistente

Ogni candidate ha:

```text
reason
evidence
expected_value
interruption_cost
best_channel
cooldown
suppression_key
expires_at
```

La queue puo' produrre `silence`.

### Stage F - Execution Harness

Prima capability reale:

- read-only file/doc summary;
- open app allowlist;
- Home Assistant read-only;
- scene reversible opt-in.

Ogni capability deve avere dry-run, observation, rollback se possibile.

### Stage G - Metrics Dashboard

Misure giornaliere:

- ungrounded claim rate;
- claim correction latency;
- stale retrieval rate;
- proactivity false-positive rate;
- proactivity suppression rate;
- action success rate;
- rollback success rate;
- privacy block count;
- user burden count;
- calibration Brier/ECE per pattern predittivi;
- sleep-time cost.

## Evals Necessarie

### Memory Eval

Domande:

- ricorda fatto attuale?
- distingue fatto storico da fatto corrente?
- cita evidence?
- evita vecchia citta dopo trasferimento?
- non inferisce troppo da evento singolo?
- corregge dopo feedback?

Metriche:

```text
grounded_accuracy
stale_error_rate
over_inference_rate
source_missing_rate
scope_violation_rate
```

### Proactivity Eval

Classi:

- speak now;
- ask confirmation;
- digest later;
- silence.

Metriche:

```text
precision_speak
recall_urgent
false_interruptions
missed_important_events
suppression_respected
channel_policy_respected
```

### Execution Eval

Ogni action replay verifica:

- task graph valido;
- risk class corretta;
- approval quando serve;
- dry-run presente;
- observation presente;
- rollback presente se reversibile;
- status stream completo;
- audit completo;
- no fake action.

### Calibration Eval

Ogni pattern predittivo deve avere:

```text
prediction
probability
observation_window
observed_outcome
calibration_update
```

Metriche:

- Brier score;
- expected calibration error;
- confidence drift;
- stale pattern count.

## Anti-Pattern Da Evitare

- "Il modello capisce quindi puo' agire" -> falso. Serve affordance/risk/approval.
- "Una memoria recuperata e' vera" -> falso. Serve valid time e confidence.
- "Una emozione vocale e' una verita sulla persona" -> falso. E' segnale temporaneo.
- "Proattivo = mandare reminder" -> falso. Proattivo = valore > costo interruzione.
- "Dream cycle aggiorna profilo incrementale" -> rischio drift. Rigenerare dal substrato.
- "Prompt come governance" -> fragile. Governance esterna al prompt.
- "Tool calling come esecuzione" -> incompleto. Serve observation, rollback, audit.

## Decisione Pratica Per JARVIS

Costruire prima **Harness cognitivo-esecutivo**, non "personalita" piu lunga.

Ordine consigliato:

1. `CognitiveTrace` e replay suite.
2. raw episodes reali redatti.
3. salience 2.0 con context-change e interruption cost.
4. dream cycle live reviewable.
5. living profile/counterpoint da evidence reale.
6. proactivity queue persistente.
7. execution frame + affordance scoring.
8. capability reali piccole con observation/rollback.
9. voice affect local opt-in.
10. dashboard metriche e calibration.

Se questo funziona, JARVIS non "apre app e basta". Osserva contesto, pesa costo,
capisce cosa puo' sapere, dubita, chiede se serve, agisce solo con affordance e
poi impara dall'esito.

## Relazioni

- [[GiustoDev_Muffin_Architecture]]
- [[Runtime_Harness_Adaptation]]
- [[Emotion2Vec]]
- [[Jarvis_User_Knowledge_Ontology]]
- [[Jarvis_Memory_Architecture]]
- [[Agent_Harness_Best_Practices]]
- [[High_Reliability_Decision_Protocol]]
- [[Local_LLM_Smart_Home]]
