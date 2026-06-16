# Graph Report - seed-knowledge-graph  (2026-06-12)

## Corpus Check
- 73 files · ~85,118 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1562 nodes · 2981 edges · 110 communities (101 shown, 9 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 487 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f078dddd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Mutation Validation|Mutation Validation]]
- [[_COMMUNITY_Evaluation Reporting|Evaluation Reporting]]
- [[_COMMUNITY_Lineage Tracking|Lineage Tracking]]
- [[_COMMUNITY_Evolution Engine|Evolution Engine]]
- [[_COMMUNITY_Descendant Building|Descendant Building]]
- [[_COMMUNITY_Memory Management|Memory Management]]
- [[_COMMUNITY_Promotion Authority|Promotion Authority]]
- [[_COMMUNITY_Onboarding Logic|Onboarding Logic]]
- [[_COMMUNITY_Personality Runtime|Personality Runtime]]
- [[_COMMUNITY_Telemetry and Testing|Telemetry and Testing]]
- [[_COMMUNITY_File System Security|File System Security]]
- [[_COMMUNITY_Capability Registry|Capability Registry]]
- [[_COMMUNITY_Command Routing|Command Routing]]
- [[_COMMUNITY_Configuration Management|Configuration Management]]
- [[_COMMUNITY_Activity Watching|Activity Watching]]
- [[_COMMUNITY_LLM and Voice Interface|LLM and Voice Interface]]
- [[_COMMUNITY_Privacy Redaction|Privacy Redaction]]
- [[_COMMUNITY_Core Orchestration|Core Orchestration]]
- [[_COMMUNITY_App Entry Point|App Entry Point]]
- [[_COMMUNITY_Onboarding State Validation|Onboarding State Validation]]
- [[_COMMUNITY_Onboarding Tests|Onboarding Tests]]
- [[_COMMUNITY_Background Job Scheduling|Background Job Scheduling]]
- [[_COMMUNITY_Permission Brokering|Permission Brokering]]
- [[_COMMUNITY_Audit Reporting|Audit Reporting]]
- [[_COMMUNITY_System Architecture|System Architecture]]
- [[_COMMUNITY_Design Principles|Design Principles]]
- [[_COMMUNITY_System Components|System Components]]
- [[_COMMUNITY_Runtime Adaptation|Runtime Adaptation]]
- [[_COMMUNITY_Experiment Protocol|Experiment Protocol]]
- [[_COMMUNITY_Product Vision|Product Vision]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `Memory` - 91 edges
2. `LineageStore` - 84 edges
3. `MutationCandidate` - 78 edges
4. `DescendantBuilder` - 66 edges
5. `SeedApp` - 60 edges
6. `EvaluatorHarness` - 58 edges
7. `PromotionAuthority` - 56 edges
8. `LineageError` - 48 edges
9. `DescendantIntegrityError` - 43 edges
10. `EvolutionEngine` - 34 edges

## Surprising Connections (you probably didn't know these)
- `test_seed_prompt_uses_relevant_memory_without_dumping_unrelated()` --calls--> `SeedApp`  [INFERRED]
  corpus/seed/tests/test_salience.py → corpus/seed/core/app.py
- `test_knowledge_recall_excludes_sensitive()` --calls--> `SeedApp`  [INFERRED]
  corpus/seed/tests/test_user_knowledge.py → corpus/seed/core/app.py
- `test_knowledge_recall_intent_is_explicit_command()` --calls--> `SeedApp`  [INFERRED]
  corpus/seed/tests/test_user_knowledge.py → corpus/seed/core/app.py
- `test_live_capture_records_user_episode_provenance()` --calls--> `SeedApp`  [INFERRED]
  corpus/seed/tests/test_user_knowledge.py → corpus/seed/core/app.py
- `test_salience_telemetry_is_aggregate_only()` --calls--> `Telemetry`  [INFERRED]
  corpus/seed/tests/test_salience.py → corpus/seed/core/telemetry.py

## Import Cycles
- None detected.

## Communities (110 total, 9 thin omitted)

### Community 0 - "Mutation Validation"
Cohesion: 0.07
Nodes (76): AcceptanceCheck, _build_layout(), _candidate(), _CheckRecorder, _components(), _contains_private_pattern(), CoreAcceptanceError, _create_parent() (+68 more)

### Community 1 - "Evaluation Reporting"
Cohesion: 0.11
Nodes (46): _aggregate_outcome(), _atomic_create_json(), _canonical_json(), _changed_files(), _contains(), _contains_obvious_private_data(), _evaluate_assertion(), EvaluationCheck (+38 more)

### Community 2 - "Lineage Tracking"
Cohesion: 0.18
Nodes (19): Memory, PersonalityRuntime, MockLLM, Tests for S8 compatible personality runtime., _runtime(), test_counterpoint_is_required_for_opinion_not_for_plain_fact_request(), test_explainability_uses_audit_without_raw_turn_text(), test_free_form_preference_is_structured_and_identity_conflicts_are_excluded() (+11 more)

### Community 3 - "Evolution Engine"
Cohesion: 0.22
Nodes (5): EvolutionEngine, Collect -> redact -> propose -> select -> lineage -> validation-only.          S, parse_json_object(), Parse a JSON object, tolerating provider-added Markdown fences/prose., Any

### Community 4 - "Descendant Building"
Cohesion: 0.26
Nodes (11): _clamp(), _connected_to_seed(), _item_ref(), K3: gate di salienza deterministico e spiegabile per il contesto.  Non parla aut, Filtra l'output M3. Senza segnale spiegabile non entra nulla., Counterpoint approvato entra solo se topic/reason ha match spiegabile., Score iniziale K3. Rilevanza spiegabile obbligatoria per entrare., SalienceDecision (+3 more)

### Community 6 - "Promotion Authority"
Cohesion: 0.04
Nodes (46): 10. Conclusione, 1. Principio Base, 2.1 Runtime Core, 2.2 Capability Forge Harness, 2.3 Servizi di Supporto, 2. Ruoli Canonici dei Componenti, 3. Chi parla con l'utente e chi no, 4.1 Sezione A - Runtime Pubblico (+38 more)

### Community 7 - "Onboarding Logic"
Cohesion: 0.06
Nodes (43): config_path(), EvolutionConfig, _from_dict(), LLMConfig, load(), PrivacyConfig, Caricamento e validazione config. Le API key NON vengono mai loggate.  Ordine di, Versione loggabile: key sostituite da presenza/assenza. (+35 more)

### Community 8 - "Personality Runtime"
Cohesion: 0.16
Nodes (6): PersonalityDecision, PersonalityRuntime, Compatible personality runtime: distinct identity, contextual modes and audit., Builds an explainable prompt without turning the user into a persona., normalize(), lowercase, niente accenti, niente punteggiatura, spazi collassati.

### Community 9 - "Telemetry and Testing"
Cohesion: 0.12
Nodes (10): Telemetria locale e report d'esperimento.  Tutto resta sul PC. Il report finale, Aggregati S9: mai query, mai key, mai testo dei risultati., Aggregati S10: separazione ruoli, fallback e costo (token).         Mai prompt,, Aggregati M2: tipi e stati dei claim. Mai i valori (sarebbe testo         person, Aggregate-only lineage audit. Never exports proposals or evidence., Micro-survey serale: 2 domande, 10 secondi., Bottone 'Esporta report' nella UI: scrive nel workspace e ritorna il path., Aggregati per la tesi. Leggibile di proposito: l'utente lo apre         e lo leg (+2 more)

### Community 10 - "File System Security"
Cohesion: 0.18
Nodes (21): check(), core_config_dir(), _expand_user_root(), is_execute_denied(), _is_other_user_profile(), is_read_denied(), _is_under(), is_write_denied() (+13 more)

### Community 11 - "Capability Registry"
Cohesion: 0.06
Nodes (33): 1.1 UX conversation-first, 1.2 Gateway cloud unico, 1.3 Search layer esterno, 1.4 Lanes canoniche, 1.5 Capability evolution live, 1.6 Task Graph interno, 1.7 User Knowledge Ontology, 1.8 Proattivita e ambient intelligence (+25 more)

### Community 12 - "Command Routing"
Cohesion: 0.16
Nodes (8): CommandRouter, _humanize(), Command router deterministico: puro Python prima, LLM solo come normalizzatore., Usato dal forge: una capability generata puo' dichiarare seed pattern., Persist only clearly explicit, already-redacted preference statements., Esegue la route. Locale = zero costi; capability = sandbox gated., Risposta testuale senza LLM per gli esiti delle capability., Route

### Community 13 - "Configuration Management"
Cohesion: 0.08
Nodes (25): 1. Obiettivo del Workflow, 2. Ciclo di Vita Canonico di una Richiesta, 3.1 Richiesta di Ricerca, 3.2 Richiesta di Coding, 3.3 Richiesta di Documento o Preventivo, 3.4 Evento Ambientale o Routine, 3. Pattern Operativi Canonici, 4. Esperienza Conversazionale Attesa (+17 more)

### Community 14 - "Activity Watching"
Cohesion: 0.16
Nodes (6): ActivityWatcher, _foreground_window(), _is_idle(), Activity watcher: processi + finestra attiva + media. Niente screenshot, niente, Blocco interno: nessuna osservazione prima della fine onboarding., (exe_name, window_title) della finestra in foreground. Windows only.

### Community 15 - "LLM and Voice Interface"
Cohesion: 0.17
Nodes (12): Evidenza K3 pronta per review (2026-06-12), Feature Context Pack - K2 Living Profile + Counterpoint, Feature Context Pack - K3 Salience / Awareness, Fix gate K3 post test owner - trasparenza senza disclosure operativa, Fonti e decisioni estratte, Fonti e decisioni estratte, Implicazioni implementative K2, Implicazioni implementative K3 (+4 more)

### Community 16 - "Privacy Redaction"
Cohesion: 0.15
Nodes (3): Test M1 selezione per rilevanza (recall.py): deterministica, solo pertinenti, ma, M1: una nuova istanza SEED ricarica la conversazione precedente., test_history_persists_across_sessions()

### Community 17 - "Core Orchestration"
Cohesion: 0.33
Nodes (4): PermissionBroker, PermissionRequest, Permission broker: nessuna azione rischiosa senza autorizzazione.  Classi di ris, ask_callback(request) -> {"decision": "allow"|"deny", "remember": bool}

### Community 18 - "App Entry Point"
Cohesion: 0.11
Nodes (11): normalize_repl_command(), K1: recall esplicito del modello utente. Raggruppa per tipo, esclude i         c, M2: estrazione candidate-only dalla conversazione recente (sleep-time)., M2+K2 sleep-time: estrae claim, poi rigenera i derivati reviewable., Esporta uno snapshot coerente, mai a meta' reflection., Entry point della chat (UI o REPL).          Prima il ROUTER DETERMINISTICO (pur, SeedApp, LLMClient (+3 more)

### Community 19 - "Onboarding State Validation"
Cohesion: 0.10
Nodes (20): 14 - Memory Consolidation Plan, Acceptance per fase, CoALA (4 tipi di memoria) come framing M2, Cosa NON prendere da Mem0, Cosa prendere da agentmemory (segmento local-first, vicino a SEED), Fasi, Fonti canoniche (LLM Wiki JARVIS), Graphify (tool nostro) per M3 (+12 more)

### Community 20 - "Onboarding Tests"
Cohesion: 0.10
Nodes (19): 08 — Piano test Windows (per Cristian, 2026-06-11), A. Privacy Filter reale - necessario prima del pilot, B. Conversazione e reflection con provider reale - necessario, C. Giudizio umano breve - necessario, Cosa deve testare Cristian adesso, Cosa ho verificato stanotte (e cosa no), Esito test manuale reale 2026-06-11, Evidenza build 2026-06-11 (+11 more)

### Community 21 - "Background Job Scheduling"
Cohesion: 0.19
Nodes (4): Job in background: watcher, reflection notturno su idle, promemoria survey.  Il, Per il debug di Cristian e per il pilot: bottone nascosto in UI., Barrier per export/report: ritorna solo a reflection conclusa., Scheduler

### Community 22 - "Permission Brokering"
Cohesion: 0.10
Nodes (19): 13 - Model Roles, Design Governor e Voice Plan, Configurazione proposta, Configurazione target, Contratto output reviewer, Conversation: `gemma4:31b`, Corpus minimo, Design Directive Pack, Design reviewer: `gpt-oss:120b` (+11 more)

### Community 23 - "Audit Reporting"
Cohesion: 0.10
Nodes (19): 10. Conclusione Operativa, 1.1 Control Plane, 1.2 Execution Plane Locale, 1.3 User Knowledge e Ambient Layer, 1. Stack Locale e Infrastrutturale, 2. Gateway Cloud Canonico, 3.1 Modelli da non usare come default globale, 3. Lanes Modello Raccomandate (+11 more)

### Community 24 - "System Architecture"
Cohesion: 0.18
Nodes (10): JARVIS Agent Ecosystem, M3 Memory, JARVIS Operational Workflow, SEED Evolutionary Architecture, SEED Stable Boot Supervisor, 1. Core Value / Funzione Principale, 2. Specifiche Tecniche, 3. Integrazione con JARVIS (+2 more)

### Community 25 - "Design Principles"
Cohesion: 0.50
Nodes (4): JARVIS Design Principles, SEED Mutation Contract, SEED Evolution Engine, SEED Isolation & Security

### Community 26 - "System Components"
Cohesion: 0.50
Nodes (4): JARVIS User Knowledge Ontology, SEED Activity Watcher, SEED Compatible Personality, SEED Privacy Gate

### Community 27 - "Runtime Adaptation"
Cohesion: 0.10
Nodes (19): Arco Storico Proposto, Direzione Chiara, Domande Da Portare Al Relatore, Il Rischio Del Linguaggio, Informazione-numeri-interrogazioni, Perimetro Consigliato, Personal OS Thesis Direction, Principi Del Personal OS Accessibile (+11 more)

### Community 30 - "Community 30"
Cohesion: 0.11
Nodes (18): Anti-Pattern Da Evitare, Cognitive Trace 0.2, Collegamento A Moduli JARVIS, Decisione Pratica Per JARVIS, Default Mode Simulation Per Proattivita, Dream Cycle Come Replay Ippocampo-Corteccia, Esecuzione Come Active Inference, Formula Proactivity 0.2 (+10 more)

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (15): 10. Internal Cognition, Optional Observability, 11. Ambient Intelligence With Boundaries, 12. Distinctive Voice, 1. Personal Operating Ecosystem, 2. Conversation First, Not Conversation Only, 3. Knowledge Before Action, 4. User Knowledge Is an Open Ontology, 5. Hypotheses Are Not Facts (+7 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (14): 01 - Architettura evolutiva, 1. Interaction Surface, 2. Active Runtime, 3. Evidence & Personal State, 4. Evolution Lab, 5. Lineage Archive, 6. Stable Boot Supervisor, Flusso di una mutazione (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.13
Nodes (14): 06 - Protocollo dell'esperimento, Criteri di interpretazione, Disegno, Domande di ricerca, Evoluzione e lineage, Fasi dei 14 giorni, Fiducia, controllo e privacy, Giorno 0 - Risveglio e onboarding (+6 more)

### Community 34 - "Community 34"
Cohesion: 0.13
Nodes (14): 15 - Cognitive User Knowledge Plan, Acceptance per fase, Contratti minimi, Fasi, Fonti canoniche (LLM Wiki JARVIS, subordinate ai doc SEED), K1 - User Knowledge Ontology, K2 - Living Profile + Counterpoint, K3 - Salience / Awareness (+6 more)

### Community 35 - "Community 35"
Cohesion: 0.14
Nodes (13): 09 - Personalita compatibile, non speculare, 1. Identita stabile, 2. Modello dell'utente, 3. Storia della relazione, 4. Modalita contestuale, 5. Self-narrative e counterpoint, Definizione operativa, Gerarchia dell'evidenza personale (+5 more)

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (13): 09 - Personalita compatibile, non speculare, 1. Identita stabile, 2. Modello dell'utente, 3. Storia della relazione, 4. Modalita contestuale, 5. Self-narrative e counterpoint, Definizione operativa, Gerarchia dell'evidenza personale (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.14
Nodes (13): 02 - Evolution Engine, Command router deterministico, Cosa non puo fare un candidate direttamente, Evaluator, Loop evolutivo, Obiettivo, Origine delle mutazioni, Predizioni falsificabili (+5 more)

### Community 38 - "Community 38"
Cohesion: 0.14
Nodes (13): 10. Documenti Canonici Correlati, 1. Sintesi, 2. Principi Fondamentali, 3. Planes e Trust Zones, 4. Runtime Lanes Canoniche, 5. Search Policy Canonica, 6. Memoria e Retrieval, 7. Ecosistema Agenti e Harness (+5 more)

### Community 39 - "Community 39"
Cohesion: 0.25
Nodes (7): 12 - Piano implementativo SEED, Feature attiva - S9 Online Research Lane, Feature future - S10/S11 Model Roles e Voice, Ordine successivo, Posizione corrente, Riepilogo finale S9 (2026-06-12), Stato implementazione S9 (2026-06-12)

### Community 40 - "Community 40"
Cohesion: 0.15
Nodes (13): Evidenza manuale Ollama Cloud e fix richiesti, Evidenza post-fix Ollama Cloud, Feature Context Pack - S5.5 Core Practical Acceptance, Rischi residui post-fix, Contesto subordinato, Decisioni, Evidenza implementativa corrente, Fonti SEED (+5 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (13): Evidenza manuale Ollama Cloud e fix richiesti, Evidenza post-fix Ollama Cloud, Feature Context Pack - S5.5 Core Practical Acceptance, Rischi residui post-fix, Contesto subordinato, Decisioni, Evidenza implementativa corrente, Fonti SEED (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (12): 11 - Contratto normativo di mutazione, valutazione e promozione, Anti-gaming, Audit minimo, Ciclo obbligatorio, Classificazione per impatto, Concetti, Promozione, Rollback e recovery (+4 more)

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (6): CounterpointFragment, LivingProfile, LivingProfileBuilder, K2: viste rigenerabili e reviewable del modello utente.  Il source of truth rest, Rigenera K2 in modo deterministico, senza patch incrementali., Solo il privato 1:1 puo' leggere derivati approvati.

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (11): Contesto subordinato, Feature Context Pack - S7 Her-like Onboarding, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati (+3 more)

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (11): Decisioni, Evidenza implementativa corrente, Feature Context Pack - S8 Compatible Personality Runtime, Fonti ufficiali e contesto subordinato, Non-goals, Rischi, Rischi residui osservati, Scope (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (11): Contesto subordinato, Feature Context Pack - S7 Her-like Onboarding, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.18
Nodes (11): Decisioni, Evidenza implementativa corrente, Feature Context Pack - S8 Compatible Personality Runtime, Fonti SEED, Fonti ufficiali e contesto subordinato, Non-goals, Rischi, Rischi residui osservati (+3 more)

### Community 48 - "Community 48"
Cohesion: 0.18
Nodes (11): Evidenza Fix recall (2026-06-12), Evidenza K1 (2026-06-12), Evidenza K2 pronta per review (2026-06-12), Evidenza M1 (2026-06-12), Evidenza M2 (2026-06-12), Evidenza M3 (2026-06-12), Fasi, Feature Context Pack - Memory Consolidation (M1-M4) (+3 more)

### Community 49 - "Community 49"
Cohesion: 0.18
Nodes (10): 1. Essere Presente, 2. Conoscere l'Utente, 3. Automatizzare con Giudizio, 4. Proteggere l'Utente, 5. Evolvere, Collegamenti, Cosa Deve Fare, Cosa Non Deve Essere (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.18
Nodes (10): 1. [[Obsidian]], 2. [[ChromaDB]], 3. [[MemPalace]], 🔄 Data Flow, Jarvis Memory Architecture, 📚 Key Components, 🏗️ Memory Layers, Related Components (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.20
Nodes (10): Feature Context Pack - S1 Lineage Foundation, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati, Scope (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.20
Nodes (10): Feature Context Pack - S4 Replay And Evaluator Harness, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati, Scope (+2 more)

### Community 53 - "Community 53"
Cohesion: 0.20
Nodes (10): Feature Context Pack - S5 Shadow, Canary And Promotion, Wiki collegata, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati (+2 more)

### Community 54 - "Community 54"
Cohesion: 0.20
Nodes (10): Feature Context Pack - S6 Stable Boot Supervisor, Contesto subordinato, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati (+2 more)

### Community 55 - "Community 55"
Cohesion: 0.20
Nodes (10): Fonti SEED, Decisione di sequencing, Evidenza implementativa S10.1 (2026-06-12), Evidenza implementativa S10.2 (2026-06-12), Evidenza implementativa S10.3 (2026-06-12), Evidenza implementativa S10.4 (2026-06-12), Feature Context Pack - S10 Model Role Separation And Design Governor, Non ancora fatto (S10.5, dopo smoke owner) (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.20
Nodes (10): Feature Context Pack - S1 Lineage Foundation, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati, Scope (+2 more)

### Community 57 - "Community 57"
Cohesion: 0.20
Nodes (10): Feature Context Pack - S4 Replay And Evaluator Harness, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati, Scope (+2 more)

### Community 58 - "Community 58"
Cohesion: 0.20
Nodes (10): Feature Context Pack - S5 Shadow, Canary And Promotion, Wiki collegata, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati (+2 more)

### Community 59 - "Community 59"
Cohesion: 0.20
Nodes (10): Feature Context Pack - S6 Stable Boot Supervisor, Contesto subordinato, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.20
Nodes (9): 03 - Privacy Gate, Cosa puo uscire, Dati evolutivi, Export sperimentale, Mutazioni del privacy gate, Obiettivo, Personalita e privacy, Pipeline corrente (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.20
Nodes (9): 04 - Isolamento, sicurezza e recovery, Anti-gaming, Controlli su codice e artefatti, Livelli di isolamento, Modello di minaccia, Path e credenziali, Permission broker, Registro rischi (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.10
Nodes (29): capture_explicit(), K1 semantica della conoscenza dell'utente sopra il substrato M2.  M2 da' lo stor, Estrae claim espliciti chiari (gia' redatti). Deterministico, zero token.     Lo, Ripara solo claim attivi che contengono due dichiarazioni esplicite     riconosc, repair_compound_claims(), _sensitivity(), K2 living profile + counterpoint: derivati rigenerabili e reviewable., _runtime() (+21 more)

### Community 63 - "Community 63"
Cohesion: 0.22
Nodes (9): Feature Context Pack - S2 Legacy Reflection Migration, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati, Scope (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.22
Nodes (9): Feature Context Pack - S3 Descendant Builder, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati, Scope (+1 more)

### Community 65 - "Community 65"
Cohesion: 0.22
Nodes (9): Feature Context Pack - S2 Legacy Reflection Migration, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati, Scope (+1 more)

### Community 66 - "Community 66"
Cohesion: 0.22
Nodes (9): Feature Context Pack - S3 Descendant Builder, Decisioni, Evidenza implementativa corrente, Fonti SEED, Non-goals, Rischi, Rischi residui osservati, Scope (+1 more)

### Community 67 - "Community 67"
Cohesion: 0.22
Nodes (8): 00 - Visione prodotto e autorita documentale, Criterio di successo, Esperienza iniziale, Gerarchia delle fonti, Principi non negoziabili, Runtime attuale e architettura obiettivo, Superficie primaria e superfici secondarie, Tesi del prodotto

### Community 68 - "Community 68"
Cohesion: 0.22
Nodes (8): 07 - Struttura del repository: corrente e target, Moduli target, Regole di migrazione, Repository documentale, Runtime v0.2 corrente, Struttura runtime target, Test correnti, Verifiche target minime

### Community 69 - "Community 69"
Cohesion: 0.22
Nodes (8): Collegamenti, Conoscere l'utente, Direzione, J.A.R.V.I.S. v6.3 - Vision, Personal Operating Ecosystem, Proattivita' Pensata, Tono, Visione

### Community 70 - "Community 70"
Cohesion: 0.12
Nodes (12): Orchestratore: collega tutti i moduli core e gestisce il loop di chat.  Flusso d, Client LLM OpenAI-compatible: un solo client per OpenRouter / Vercel AI Gateway, GateResult, PrivacyGate, Privacy gate: nulla lascia il PC senza passare di qui.  Doppio layer in serie:, Da chiamare PRIMA di qualunque uscita verso l'API o i log., Ripristina i valori reali nei testi mostrati all'utente. MAI nei log., Invoca OPF.redact e converte RedactionResult.detected_spans         nel formato (+4 more)

### Community 71 - "Community 71"
Cohesion: 0.25
Nodes (7): 1. Principio Decisionale, 2. Matrice Sintetica, 3. Raccomandazione Per JARVIS, 4. Decisioni Provvisorie, 5. Open Questions, Agentic Runtime Options 2026-05, Relazioni

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (8): MVP Esecutivo, Stage A - Replay Harness, Stage B - Real Raw Episode Import Redatto, Stage C - Salience 2.0, Stage D - Dream Cycle Live Reviewable, Stage E - Proactivity Queue Persistente, Stage F - Execution Harness, Stage G - Metrics Dashboard

### Community 73 - "Community 73"
Cohesion: 0.25
Nodes (7): 1. Core Value / Funzione Principale, 2. Pattern Tecnici Da Estrarre, 3. Integrazione con JARVIS, 4. Candidate Backlog, 5. Rischi, OpenHarness, Relazioni

### Community 74 - "Community 74"
Cohesion: 0.29
Nodes (6): 1. Valore Principale, 2. Uso Possibile In JARVIS, 3. Rischi, 4. Raccomandazione, AgentMemory, Relazioni

### Community 75 - "Community 75"
Cohesion: 0.29
Nodes (7): 1. Osserva, 2. Pesa, 3. Capisce, 4. Dubita, 5. Corregge, 6. Tace/Parla, Traduzione In Architettura

### Community 76 - "Community 76"
Cohesion: 0.29
Nodes (7): Come Farlo Funzionare, Regola 1 - Determinismo Prima Del Modello, Regola 2 - LLM Non Scrive Fatti Direttamente, Regola 3 - Ogni Azione Ha Osservazione Attesa, Regola 4 - Ogni Proattivita Ha Costo Di Interruzione, Regola 5 - Ogni Pattern Deve Fare Predizioni, Regola 6 - Voice Affect Solo Stato Temporaneo

### Community 77 - "Community 77"
Cohesion: 0.29
Nodes (6): 1. Principio, 2. Domini aperti, 3. Tipi di conoscenza, 4. Regola di sicurezza cognitiva, 5. Relazioni, Jarvis User Knowledge Ontology

### Community 78 - "Community 78"
Cohesion: 0.15
Nodes (10): _atomic_create_json(), _candidate_contract(), _event_hash(), LineageError, _nonempty_string(), Typed mutation contract and append-only lineage store.  This module is the first, Base error for mutation contract and lineage failures., _utc_now() (+2 more)

### Community 79 - "Community 79"
Cohesion: 0.33
Nodes (5): Authority, Explicit Bridges, Graph Scope, Purpose, SEED Specific Knowledge Graph - Corpus Bridges

### Community 80 - "Community 80"
Cohesion: 0.33
Nodes (5): 12 - Piano implementativo SEED, Feature attiva - S9 Online Research Lane, Feature future - S10/S11 Model Roles e Voice, Ordine successivo, Posizione corrente

### Community 81 - "Community 81"
Cohesion: 0.33
Nodes (6): Action Contract, Affordance Check, Atto Esecutivo, Execution State Machine, ExecutionFrame, Status Conversation

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (6): Loop A - Interpretazione, Loop B - Predizione, Loop C - Metacognizione, Loop D - Action Selection, Loop E - Prediction Error / Learning, Sistema Di Ragionamento Profondo

### Community 83 - "Community 83"
Cohesion: 0.33
Nodes (5): 1. Core Value / Funzione Principale, 2. Specifiche Tecniche, 3. Integrazione con JARVIS, Relazioni, Runtime Harness Adaptation

### Community 84 - "Community 84"
Cohesion: 0.40
Nodes (5): Calibration Eval, Evals Necessarie, Execution Eval, Memory Eval, Proactivity Eval

### Community 85 - "Community 85"
Cohesion: 0.40
Nodes (5): Fonti Principali, LLM agents, memoria e atto esecutivo, Muffin e JARVIS Plus, Neuroscienze e cognizione, Quando parlare, quando tacere

### Community 86 - "Community 86"
Cohesion: 0.40
Nodes (4): 🛠️ Key Features, M3 Memory: Hybrid Retrieval Layer, Related Components, 🏗️ Role in JARVIS

### Community 88 - "Community 88"
Cohesion: 0.50
Nodes (4): Fonti Aggiunte 2026-06-04 (World Model, Global Workspace, Test-Time Compute), Global workspace implementabile (dal biologico al contratto software), Memoria a tier e compute deliberativo, World model e planning latente (perche' non basta il tool calling)

### Community 93 - "Community 93"
Cohesion: 0.16
Nodes (13): Capability registry: action contract, validazione manifest, esposizione al model, validate_manifest(), DescendantBuildError, Isolated, deterministic descendant materialization.  S3 builds candidate artifac, Raised when a descendant cannot be materialized safely., _safe_component(), _apply_trait_diff(), _DEFAULT_UI_MANIFEST() (+5 more)

### Community 100 - "Community 100"
Cohesion: 0.26
Nodes (4): Capability, CapabilityRegistry, Gate completo: registrata -> permesso -> sandbox -> stats., Path

### Community 101 - "Community 101"
Cohesion: 0.15
Nodes (4): Test K1 semantica user-knowledge: cattura esplicita deterministica, sensibilita', test_knowledge_recall_excludes_sensitive(), test_knowledge_recall_intent_is_explicit_command(), test_live_capture_records_user_episode_provenance()

### Community 103 - "Community 103"
Cohesion: 0.33
Nodes (9): _apply_nested_value(), _content_hash(), DescendantManifest, _file_hashes(), _load_json(), _write_json(), Any, MutationCandidate (+1 more)

### Community 104 - "Community 104"
Cohesion: 0.23
Nodes (13): AuditResult, dry_run(), _minimal_env(), _python_cmd(), Sandbox executor + audit statico AST per il codice delle capability.  Contratto, Env senza key, senza variabili utente: solo il minimo per Python., In dev: interprete corrente. Frozen (PyInstaller): l'exe in modalita' --run-tool, Esegue il tool con input sintetici prima della registrazione. (+5 more)

### Community 105 - "Community 105"
Cohesion: 0.23
Nodes (6): _Evolution, Scheduler compatibility tests for proposal-only reflection., test_report_barrier_waits_for_running_reflection(), test_scheduler_blocks_automatic_and_forced_reflection_during_onboarding(), test_scheduler_notifies_proposal_only_digest(), _Watcher

### Community 106 - "Community 106"
Cohesion: 0.22
Nodes (4): STT/TTS via ElevenLabs — FACOLTATIVI. Key vuota = modulo spento, SEED testuale., STT (ElevenLabs Scribe). Ritorna il testo grezzo: il chiamante DEVE         pass, TTS: il testo in ingresso e' quello GIA' re-idratato mostrato all'utente, VoiceEngine

### Community 107 - "Community 107"
Cohesion: 0.22
Nodes (8): 05 - Activity Watcher, Controlli utente, Evoluzione del watcher, Limiti inferenziali, Pipeline, Scope corrente, Uso nell'evoluzione, Direzione media locale

### Community 108 - "Community 108"
Cohesion: 0.25
Nodes (7): 05 - Activity Watcher, Controlli utente, Evoluzione del watcher, Limiti inferenziali, Pipeline, Scope corrente, Uso nell'evoluzione

### Community 109 - "Community 109"
Cohesion: 0.33
Nodes (4): Convert a selected legacy proposal into a governed lineage record., Validation-only compatibility gate. Never mutates active state., Versione senza codice per digest/selettore (il codice resta nel forge)., _strip_code()

## Knowledge Gaps
- **659 isolated node(s):** `LLMConfig`, `VoiceConfig`, `PrivacyConfig`, `WatcherConfig`, `EvolutionConfig` (+654 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EvolutionEngine` connect `Evolution Engine` to `Mutation Validation`, `Evaluation Reporting`, `Community 70`, `Community 109`, `Community 78`, `App Entry Point`, `Community 93`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `SeedApp` connect `App Entry Point` to `Lineage Tracking`, `Evolution Engine`, `Community 100`, `Memory Management`, `Community 70`, `Onboarding Logic`, `Personality Runtime`, `Telemetry and Testing`, `Community 106`, `Community 43`, `Command Routing`, `Community 101`, `Activity Watching`, `Privacy Redaction`, `Core Orchestration`, `Background Job Scheduling`, `Community 62`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `Memory` connect `Memory Management` to `Mutation Validation`, `Community 96`, `Community 97`, `Community 98`, `Lineage Tracking`, `Community 70`, `Community 102`, `Onboarding Logic`, `File System Security`, `App Entry Point`, `Community 87`, `Community 89`, `Community 90`, `Community 91`, `Community 92`, `Community 94`, `Community 95`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Memory` (e.g. with `AcceptanceCheck` and `_CheckRecorder`) actually correct?**
  _`Memory` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 51 inferred relationships involving `LineageStore` (e.g. with `AcceptanceCheck` and `_CheckRecorder`) actually correct?**
  _`LineageStore` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Are the 58 inferred relationships involving `MutationCandidate` (e.g. with `AcceptanceCheck` and `_CheckRecorder`) actually correct?**
  _`MutationCandidate` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Are the 52 inferred relationships involving `DescendantBuilder` (e.g. with `AcceptanceCheck` and `_CheckRecorder`) actually correct?**
  _`DescendantBuilder` has 52 INFERRED edges - model-reasoned connections that need verification._