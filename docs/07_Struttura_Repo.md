# 07 - Struttura del repository: corrente e target

> **Stato verificato della base corrente:** v0.2 + S1 lineage + S2 reflection
> proposal-only + S3 descendant builder + S4 replay/evaluator + S5 promotion
> core + S5.5 acceptance pratica + S6 stable boot supervisor, 134 test passati
> e zero skip al 2026-06-12.
> Questo file non dichiara implementata l'architettura obiettivo.

## Repository autocontenuto

```text
seed/
|-- AGENTS.md
|-- README.md
|-- PROJECT_OVERVIEW.md
|-- ProductionPlan.md
|-- TESI_SEED_Scaletta.md
|-- docs/
|-- SEED_UI/
|-- seed-knowledge-graph/
|-- packaging/
|   `-- pyinstaller/
|       |-- seed.spec
|       `-- supervisor.spec
|-- scripts/
|-- tests/
`-- seed/
    `-- runtime corrente
```

Questa cartella Git e' la singola fonte di verita'. Documentazione, fasi,
design, knowledge graph, codice, test e ricette di build restano insieme e
possono essere recuperati dalla cronologia Git.

`build/`, `dist/` e `release/` sono output locali rigenerabili e ignorati da
Git. Installer e pacchetti update destinati ai tester vanno pubblicati come
asset di GitHub Release.

## Runtime v0.2 corrente

La base esistente contiene:

```text
seed/
|-- run_dev.py
|-- requirements.txt
|-- config/
|-- packaging/
|   `-- pyinstaller/
|       |-- seed.spec
|       `-- supervisor.spec
|-- scripts/
|   |-- core_acceptance.py
|   `-- supervisor_probe.py
|-- supervisor_entry.py
|-- tests/
`-- seed/
    |-- __main__.py
    |-- supervisor.py
    |-- supervisor_cli.py
    |-- core/
    |   |-- app.py
    |   |-- config.py
    |   |-- llm.py
    |   |-- router.py
    |   |-- privacy.py
    |   |-- forbidden.py
    |   |-- permissions.py
    |   |-- sandbox.py
    |   |-- capabilities.py
    |   |-- watcher.py
    |   |-- memory.py
    |   |-- evolution.py
    |   |-- descendant.py
    |   |-- evaluator.py
    |   |-- promotion.py
    |   |-- acceptance.py
    |   |-- lineage.py
    |   |-- telemetry.py
    |   |-- voice.py
    |   `-- scheduler.py
    |-- ui/
    `-- capabilities_builtin/
```

Decisioni implementate utili alla migrazione:

- router deterministico con alias appresi;
- privacy gate locale e pseudonimizzazione;
- permission broker e path protection;
- sandbox capability e audit statico;
- watcher consensuale;
- memoria locale, trace, reflection, snapshot e rollback;
- UI webview e capability builtin.

Fondazione target gia introdotta:

- `lineage.py`: mutation candidate typed, transizioni, evaluator record,
  promotion blockers e hash chain append-only;
- `tests/test_lineage.py`: 10 test di contratto, integrita e tampering.
- `evolution.py`: reflection proposal-only, snapshot parent univoci, validation
  non-promozionale e pruning senza modifica diretta.
- `descendant.py`: materializzazione isolata, manifest/hash riproducibili,
  static audit senza esecuzione e tamper detection.
- `evaluator.py`: replay state-based, fixture redatte tipizzate, invarianti
  indipendenti e report hashati riproducibili, senza esecuzione candidate.
- `promotion.py`: authority separata, shadow senza effetti, lease canary
  contestuali, evidence gate, activation state-based e rollback transazionale.
- `acceptance.py`: percorso pratico isolato S1-S5 con dati sintetici, riapertura,
  promotion, rollback, tamper detection e report privacy-safe.
- `supervisor.py`: boot esterno, health tokenizzato, known-good hashata,
  fallback singolo, restore transazionale e audit append-only.
- `supervisor_cli.py` / `supervisor_entry.py`: confine CLI e artefatto
  `SEEDSupervisor.exe` separato dal runtime.

Differenze note rispetto al target:

- il core e compilato e trattato come immutabile;
- il selettore legacy usa ancora categorie e cap fisso, ma il reflection non
  applica piu direttamente le proposte;
- esistono descendant isolati, replay state-based, shadow e canary contestuali;
  manca ancora build/runtime completo;
- promotion state-based supportata; evaluator comportamentali, canary con effetti
  reali e descendant completi restano non implementati;
- supervisor indipendente implementato per versioni state-based; non seleziona
  ancora binari/versioni runtime completi diversi;
- onboarding e modello di personalita compatibile non sono implementati;
- la UI corrente non rappresenta l'esperienza di risveglio obiettivo.

## Test correnti

La documentazione precedente separava 31 test core e 13 test router:

| Suite | Numero documentato | Ambito |
|---|---:|---|
| `tests/test_core.py` | 36 | forbidden, privacy, audit, memory, manifest, evolution, sandbox |
| `tests/test_router.py` | 16 | normalizzazione, pattern, alias, fuzzy, fallback |
| `tests/test_lineage.py` | 11 | mutation contract, transizioni, promotion gate e integrita |
| `tests/test_packaging.py` | 5 | entrypoint package-aware SEED/supervisor e comandi REPL |
| `tests/test_scheduler.py` | 1 | notifica digest proposal-only |
| `tests/test_descendant.py` | 11 | isolamento, proposal legacy, hash e tampering |
| `tests/test_evaluator.py` | 10 | replay, privacy fixture, report hash e tampering |
| `tests/test_promotion.py` | 13 | authority, shadow, canary, promotion e rollback |
| `tests/test_acceptance.py` | 2 | acceptance pratica isolata e protezione root non vuota |
| `tests/test_supervisor.py` | 21 | boot, health, fallback, recovery, tampering e subprocess reale |
| **Totale core verificato** | **126** | base runtime + S1-S6 + packaging |

In aggiunta, gli `8` test OPF reali sono stati eseguiti: totale locale
`134 passed`, zero skip.

Gli integration test OPF sono descritti in `08_TestWindows_Domani.md` e non
vanno confusi con la copertura dell'architettura evolutiva target.

## Struttura runtime target

I nomi finali possono cambiare, ma le responsabilita devono restare separate:

```text
%LOCALAPPDATA%\SEED\
|-- active/
|   `-- current_version.json
|-- versions/
|   `-- <version-id>/              # build/artefatto recuperabile
|-- lineage/
|   |-- mutations/
|   |-- evaluations/
|   |-- promotions/
|   `-- rollbacks/
|-- lab/
|   |-- candidates/
|   |-- descendants/
|   |-- fixtures_redacted/
|   `-- evaluator_runs/
|-- personal/
|   |-- memory/
|   |-- user_model/
|   |-- relationship/
|   `-- self_narrative/
|-- permissions/
|-- traces/
|-- workspace/
|-- exports/
`-- recovery/
    |-- known_good.json
    `-- supervisor_logs/
```

## Moduli target

| Area | Responsabilita |
|---|---|
| `supervisor` | boot, health check, fallback e recovery indipendente |
| `runtime` | versione attiva e orchestrazione |
| `interaction` | presenza, conversazione, stato e superfici di controllo |
| `personal_state` | fatti, preferenze, ipotesi, relazione e self-narrative |
| `mutation_generator` | formulazione problema e generazione candidate |
| `descendant_builder` | build isolata e riproducibile |
| `evaluators` | replay, invarianti, rischio, personalita e costi |
| `promotion` | shadow, canary, consenso, decisione e rollback |
| `lineage` | archivio append-only e ricostruzione |
| `privacy_permissions` | trust zone e variazioni di autorita |
| `need_fitness` | WorkflowEvidence, NeedHypothesis, alternative e decisione multi-obiettivo |
| `connectors` | discovery, vetting, pinning, drift e connector host isolato |
| `connections` | Connection Broker, credential vault e authority envelope |
| `capability_activation` | subset check, awaiting_connection e attivazione indipendente |

Il target non richiede che ogni area sia un processo o package separato. Richiede
che le autorita non vengano collassate: il generatore non puo essere anche
l'unico evaluator e il promotore della propria mutazione.

## Regole di migrazione

1. preservare il runtime v0.2 come versione nota funzionante;
2. introdurre lineage e schema mutation prima delle mutazioni al core;
3. costruire evaluator e replay prima di ampliare l'autorita del generator;
4. introdurre supervisor e recovery prima dell'attivazione di descendant completi;
5. migrare onboarding e personalita senza promuovere inferenze storiche a fatti;
6. mantenere compatibilita con privacy, permessi e trace esistenti;
7. documentare ogni deviazione dal contratto in `11_Contratto_Mutazione.md`.
8. introdurre i contratti P7 e la migrazione conservativa V1 prima di consentire
   attivazione automatica authority-contained.

## Verifiche target minime

- test schema e lineage;
- build riproducibile del descendant;
- health check e fallback;
- replay personalizzato redatto;
- invarianti privacy e permission delta;
- authority envelope subset check fail-closed;
- connector provenance, digest, schema drift e quarantena;
- secret discard e assenza di credenziali nei tool generati;
- evaluator anti-mirroring e anti-sycophancy;
- shadow e canary;
- rollback manuale e automatico;
- ricostruzione completa di una decisione di promozione.
