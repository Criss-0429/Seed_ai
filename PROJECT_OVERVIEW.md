# FrameworkUtenti - SEED

> Framework desktop personale auto-evolutivo per l'esperimento di tesi.
> Ultimo aggiornamento: 2026-06-15.

## Knowledge graph specifico

Il grafo SEED specifico, collegato ai documenti ufficiali JARVIS e alla LLM
Wiki pertinente, vive in
[`seed-knowledge-graph/`](seed-knowledge-graph/README.md).

- report navigabile: [`GRAPH_REPORT.md`](seed-knowledge-graph/graphify-out/GRAPH_REPORT.md)
- grafo interattivo: `seed-knowledge-graph/graphify-out/graph.html`
- grafo SEED + JARVIS merged:
  `seed-knowledge-graph/graphify-out/jarvis-seed-merged.json`

## Cos'e

SEED e un'applicazione Windows locale che parte da una base comune e costruisce,
in relazione con ogni utente, un sistema progressivamente diverso. Il modello
puo proporre mutazioni a qualunque parte del software: interfaccia, personalita,
policy, workflow, capability, memoria, routing, architettura e core.

La divergenza non consiste nello sbloccare gradualmente lo stesso catalogo.
SEED decide quali capacita conviene imparare, mantenere o non concepire per lo
specifico utente. Tool, integrazioni e superfici emergono da salienza ed
evidenza; `non imparare` e un risultato valido quanto costruire una capability.

Lo spazio candidato e aperto, ma una mutazione non sostituisce direttamente la
versione attiva. Ogni cambiamento viene materializzato come descendant isolato,
valutato rispetto al parent, registrato nel lineage e promosso solo quando
esistono evidenza, controllo dei rischi e rollback.

SEED non e JARVIS. Distilla pattern generalizzabili studiati in JARVIS e nella
LLM Wiki, ma ha una propria autorita documentale, un proprio runtime e un proprio
esperimento.

## Esperienza obiettivo

Il primo avvio presenta una superficie minimale e calda ispirata alla qualita
relazionale di *Her*: una presenza centrale si risveglia, spiega il patto con
l'utente e avvia una conversazione naturale. Chiede alla persona di parlare di
se, propone confronti concreti tra possibili modalita di collaborazione e
restituisce cio che pensa di aver compreso.

Questo processo non costruisce una copia dell'utente. Costruisce una personalita
compatibile composta da identita SEED, modello dell'utente, storia della
relazione, modalita contestuale e self-narrative/counterpoint.

## Decisioni non negoziabili

1. **Locale per default:** memoria, profilo, telemetria, lineage e varianti sul PC.
2. **Privacy prima dell'uscita:** qualunque contenuto remoto passa dal privacy gate.
3. **Spazio candidato aperto:** nessuna categoria software e esclusa a priori.
4. **Attivazione governata:** chi genera una mutazione non puo auto-promuoverla.
5. **Versioni recuperabili:** nessun overwrite in-place dell'unico runtime funzionante.
6. **Permessi per effetti:** ogni variazione di autorita e dichiarata e
   approvata; entro autorita gia concessa, una authority indipendente puo
   attivare capability verificate senza auto-espandere i permessi.
7. **Compatibilita senza imitazione:** adattamento espressivo e funzionale, con dissenso.
8. **Ipotesi diverse dai fatti:** provenance, confidenza, controevidenza e correzione.
9. **Fitness multi-obiettivo:** utilita, fiducia, continuita, costo, privacy e sicurezza.
10. **Controllo dell'utente:** spiegazione, ispezione, revoca, export e rollback.

## Stato corrente e target

Il codice v0.2 e una base sperimentale con command router deterministico,
privacy gate, permission broker, sandbox capability, watcher, memoria M1-M4,
Cognitive User Knowledge K1-K4, reflection, rollback, model-role separation,
ricerca online governata e backend voce/emotion opt-in. Il runtime corrente
limita ancora le mutazioni candidate alle categorie legacy. Il reflection
non applica piu direttamente: registra candidate proposal-only nel lineage e
costruisce descendant isolati non eseguibili. Un evaluator indipendente esegue
replay deterministici state-based, verifica invarianti e registra report hashati;
non esegue codice candidato. Il promotion core separato apre shadow senza
effetti, governa canary contestuali e puo promuovere solo mutazioni state-based
supportate dopo evidence gate, stale-parent check e rollback disponibile.

La S9 Online Research Lane (2026-06-12) da' al runtime ricerca online
governata: provider Exa/Tavily, privacy gate sulla query, citazioni
verificate, budget giornaliero e ampiezza legata alla preferenza dell'utente
con floor di 3 fonti.

La feature attiva e `D0 - Runtime Option Benchmark`: confronto locale e
deterministico di pattern OpenClaw, Hermes e OpenHarness su fixture sintetiche.
Non integra ancora worker o daemon reali. La UI Her-like e S11.3 restano nella
fase UI successiva.

## Indice documentazione

| File | Autorita e contenuto |
|---|---|
| `docs/00_Visione_Prodotto.md` | Intento, principi, UX iniziale, gerarchia documentale |
| `docs/01_Architettura.md` | Architettura obiettivo: runtime attivo, evolution lab, supervisor |
| `docs/02_EvolutionEngine.md` | Generazione, valutazione e selezione evolutiva |
| `docs/03_PrivacyGate.md` | Trust zone, redazione, dati personali e mutazioni |
| `docs/04_Sandbox_Sicurezza.md` | Isolamento, permessi, descendant e recovery |
| `docs/05_ActivityWatcher.md` | Osservazione consensuale e limiti inferenziali |
| `docs/06_Esperimento.md` | Protocollo di 14 giorni e metriche |
| `docs/07_Struttura_Repo.md` | Stato del codice v0.2 e struttura target |
| `docs/08_TestWindows_Domani.md` | Smoke test del runtime corrente |
| `docs/09_Personalita_Compatibile.md` | Personalita compatibile ma non speculare |
| `docs/10_Fonti_Ricerca.md` | Paper, preprint, repo e collegamenti alla wiki |
| `docs/11_Contratto_Mutazione.md` | Requisiti normativi di mutazione e promozione |
| `docs/12_ImplementationPlan.md` | Feature attiva, scope, test plan e ordine di sviluppo |
| `docs/13_ModelRoles_Voice_Plan.md` | S10 model role separation/design governor e S11 voice |
| `docs/14_Memory_Consolidation_Plan.md` | Substrato memoria M1-M4 (persistenza, ontologia, edge semantici, dream cycle) |
| `docs/15_Cognitive_User_Knowledge_Plan.md` | Modello cognitivo dell'utente K1-K4 (living profile, salienza, counterpoint) |
| `docs/16_Agentic_Daemon_Plan.md` | Daemon agentico background (Hermes+OpenClaw pattern), read-only observation, sandbox sicuro — priorita' #1 forecast |
| `docs/17_UI_Implementation_Plan.md` | Implementazione UI da SEED_UI (Guidelines P0-P5, Brand, 4 wireframe, Prototype); regole UI/UX nel design reviewer |
| `docs/18_Adaptive_Web_Rendering_Plan.md` | Capability futura emergente per ripresentare contenuti web in modo isolato e reversibile |
| `docs/19_Selective_Capability_Forge_Plan.md` | Programma futuro per generare, verificare e attivare capability specifiche dell'utente senza auto-espandere autorita |

## Fonti

La tracciabilita completa e in `docs/10_Fonti_Ricerca.md`. I riferimenti
principali includono Darwin Godel Machine, AlphaEvolve, ADAS, AFlow, Voyager,
Reflexion, Agent Workflow Memory, Generative Agents, MemGPT/Letta, studi sulla
personalizzazione e sul conversational style matching, principi mixed-initiative
e i design reference OpenHarness e Muffin.

La LLM Wiki e usata come contesto tecnico subordinato. I collegamenti principali
sono `Runtime_Harness_Adaptation.md`,
`Jarvis_Cognitive_User_Model_Execution_Harness.md`,
`Jarvis_User_Knowledge_Ontology.md`, `Jarvis_Memory_Architecture.md`,
`Agent_Harness_Best_Practices.md` e `Personal_OS_Thesis_Direction.md`.

## Stato operativo

- [ ] Runtime v0.2: suite automatica verde, 329 test al 2026-06-13
- [ ] Smoke test su Windows reale e build PyInstaller - owner gate Cristian
- [ ] Migrazione dalla mutazione periferica al lineage di descendant
- [ ] Implementazione onboarding conversazionale e personalita compatibile
- [ ] Pilot interno
- [ ] Esperimento con 6-8 partecipanti per 14 giorni
