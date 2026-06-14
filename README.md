# SEED v0.2 - runtime corrente

Questa cartella contiene la base eseguibile attuale di SEED. Implementa un
harness locale con command router deterministico, privacy gate, permessi,
sandbox capability, memoria, watcher, reflection e rollback.

P0 distribuzione aggiunge il Provider Hub BYOK: nelle installazioni tester
(`provider_hub.required=true`) onboarding personale e chat restano bloccati
finche almeno un profilo Ollama Cloud, OpenRouter o Vercel AI Gateway non viene
validato realmente. Le key sono cifrate con DPAPI; il fallback automatico
cross-provider puo andare solo verso Ollama Cloud, mai verso provider PAYG.
La superficie **Provider e modelli** permette configurazione, test, revoca,
preset e mapping per ruolo. P1 installer e bundle ML offline restano separati.

La visione e l'architettura obiettivo sono in `../docs/`. In particolare:

- `00_Visione_Prodotto.md` definisce l'esperienza iniziale e i principi;
- `02_EvolutionEngine.md` descrive il modello evolutivo target;
- `09_Personalita_Compatibile.md` sostituisce l'idea di persona costruita per
  semplice imitazione dell'utente;
- `11_Contratto_Mutazione.md` definisce quando una mutazione puo essere promossa.

Il codice v0.2 non implementa ancora integralmente queste decisioni. Mantiene un
core compilato non mutabile, mutazioni periferiche e un cap fisso di selezione.
La prima fondazione target e presente in `seed/core/lineage.py`: candidate typed,
transizioni, record evaluator, promotion blockers e lineage append-only.
Il reflection pass e ora proposal-only: registra candidate e validazione legacy
nel lineage, ma non applica cambiamenti al runtime attivo. Le candidate valide
vengono materializzate come descendant isolati e non eseguibili sotto
`%LOCALAPPDATA%\SEED\lab\descendants\`.
Il replay/evaluator S4 verifica integrita, scope, permission contract, pattern
di segreti e assertion state-based. I report canonici vivono sotto
`%LOCALAPPDATA%\SEED\lab\evaluator_runs\`. Nessun descendant o codice capability
generato viene eseguito; candidate runtime-only restano `inconclusive`.
Il promotion core S5 separa autorita e candidate: reflection puo aprire solo
shadow senza effetti; canary usa lease per context id; promotion state-based
richiede prove shadow/canary, parent non stale e rollback. UI/personality,
capability generate e descendant completi non sono promossi in questa fase.
S6 aggiunge `SEEDSupervisor.exe`, un processo esterno al core attivo che valida
pointer, snapshot e lineage, avvia il runtime, attende un health signal
tokenizzato e mantiene una known-good legata all'hash completo della versione.
Su boot unhealthy ripristina la known-good e ritenta una sola volta.
S7 aggiunge un onboarding conversazionale persistente core-only: consenso prima
di qualsiasi raccolta, racconto redatto, preferenze esplicite, ipotesi
correggibili a bassa confidenza, sintesi, pausa, revoca e reset. Durante
onboarding watcher e reflection sono bloccati; gli episodi onboarding non
alimentano mutazioni. S8 aggiunge una identita conversazionale stabile e
distinta dall'utente, modalita temporanee, counterpoint, correzioni stilistiche
esplicite, explainability e telemetria aggregata. Le ipotesi onboarding non
diventano istruzioni di personalita e `persona_change` resta proposal-only.
La UI Her-like resta una fase separata.
S9 (completa, 2026-06-12) aggiunge la Online Research Lane: ricerca online
provider-neutral (Exa/Tavily) con query redatta dal privacy gate, key solo in
core_config, cap giornaliero di chiamate, fallback esplicito tra provider,
risultati con provenance, risposta con citazioni verificate e distinzione
fonte/inferenza. Le pagine analizzate scalano con la profondita (quick 3,
basic 5, deep 10) e con la preferenza esplicita dell'utente: floor fisso a 3
fonti per evitare fiducia cieca, nessun massimo sul deep. La builtin
`web_search` e' dormant: la lane e' l'unico percorso web governato.

D0 (pronta per review, 2026-06-13) aggiunge un benchmark architetturale locale
e deterministico per OpenClaw, Hermes e OpenHarness. Usa solo fixture sintetiche
privacy-safe, non installa o avvia runtime esterni e non concede accesso reale.
La decisione proposta mantiene SEED Core governatore: OpenHarness come backend
isolamento/esecuzione, Hermes come pattern registry/skills/delega, OpenClaw come
pattern daemon/sessione. Il comando `:runtimebench` esporta evidenza hashata
sotto `%LOCALAPPDATA%\SEED\lab\runtime_bench\`. Il gate D0 e' stato approvato
manualmente dall'owner il 2026-06-13 (documentato in `../docs/12_ImplementationPlan.md`).

D1 (pronta per review, 2026-06-13) aggiunge un daemon di background SOLO
in-process: vive dentro il processo SEED supervisionato, parte con SEED e muore
alla chiusura. Nessun servizio OS, nessun auto-start, nessun always-on. Emette un
heartbeat reviewable e mantiene una coda di proattivita' locale e persistente con
cooldown, suppression e silenzio di default (parla solo se il valore atteso supera
il costo di interruzione + privacy + trust). Il daemon NON esegue azioni
agentiche di scrittura, non ha accesso a shell/file reali/worker esterni e non
riceve registry/broker: per costruzione produce solo decisioni rivedibili. La coda
e l'audit non contengono dati personali, segreti o testo grezzo (solo categoria,
riferimento opaco e conteggi aggregati). Comando locale `:daemon` per lo snapshot
review; telemetria nella sezione `daemon` del report.

D2 (pronta per review, 2026-06-13) aggiunge il worker adapter READ-only: la prima
capability worker `worker.runtime_status` dietro permission broker + audit
aggregato. Ogni azione worker ha un `ActionContract` tipizzato (input/output
schema, risk_class, side_effect_type, requires_approval, supports_dry_run,
supports_rollback, observability_signal); in D2 sono ammesse SOLO azioni
READ-only (`side_effect_type == "read"`, risk class `safe`/`read_safe`), e il
registry rifiuta in registrazione qualunque azione non-read. Il worker riceve solo
un provider di stato aggregato (mai config/key/memoria grezza), supporta dry-run
e dichiara l'observation attesa. Nessuna scrittura, shell, file reale o worker
esterno (l'isolamento container/ristretto e' D3, la capability WRITE_SAFE e' D4).
Allowlist azioni in config. Comando locale `:worker`; telemetria sezione `worker`.

D-OBS / D3 / D4 / D5 + UI U0-U7 (pronti per review, 2026-06-13) — tutti
**default OFF / gated**, nulla attivato:

- **D-OBS** observation lane READ-only (`observation.py`): consenso per-classe
  (default OFF), sensibile escluso, salienza deterministica, candidate-ipotesi a
  bassa confidenza (mai fatti), revoca = purge. `:observation`.
- **D3** sandbox hardening (`worker_sandbox.py`): tier isolamento, trust gate
  (`destructive` vietata, write -> approval owner, observability gate), dry-run,
  rollback. `:sandbox`.
- **D4** WRITE_SAFE (`write_safe.py`): write reversibili allowlistate solo nel
  workspace, approval owner + dry-run + rollback + auto-rollback su observation
  fallita. Default OFF. `:writesafe`.
- **D5** skills + delega (`skills.py`): registry review-gated (no self-install),
  task graph IR aciclico, delega a sub-agenti isolati gated. Default OFF.
  `:skills`.
- **D6 ritirata dall'owner**: nessun gateway esterno; tutto resta in `SEED.exe`.
- **UI U0-U7** (`ui/surface/index.html`, `ui_governance.py`): riproduzione fedele
  del design `SEED_UI/SEED Prototype.dc.html` (palette oklch, DM Sans/DM Mono, orb
  seme+anelli, conversazione, superfici Modello Utente/Permessi via Ctrl+., voice
  overlay = S11.3, toast), **reimplementata in JS vanilla** (niente React/CDN) per
  restare app Python/pywebview offline con build EXE; chat via `JsApi`. Governance
  P0-P5 (`ui_directives` nel DesignDirectivePack).

Attivazione delle lane, smoke reali e apertura dei gate restano owner.

Comandi ricerca: `cerca online <tema>`, `cerca <tema> sul web`,
`approfondisci <tema>`. Ampiezza: `analizza piu fonti`, `analizza meno fonti`,
`fonti standard`. Telemetria aggregata nella sezione `research` del report.

## Compatible Personality Runtime S8

Il runtime di personalita:

- adatta forma e modalita, ma non copia opinioni o identita dell'utente;
- usa modalita informative, creative, supportive, critiche e operative;
- permette override per turno, per esempio `modalità critica: valuta...`;
- tratta correzioni esplicite supportate come preferenze persistenti;
- attiva counterpoint per richieste di opinione, critica o rischio senza
  inventare disaccordo sulle richieste fattuali;
- registra decisioni e report solo in forma aggregata, senza testo del turno;
- tenta al massimo un repair privacy-gated su risposte evidentemente servili o
  compiacenti.

Controlli locali disponibili:

- `Quali principi segui?`
- `Perché hai risposto così?`

## Stable Boot Supervisor S6

Prima del primo boot supervisionato, registrare esplicitamente lo stato attivo:

```powershell
dist\SEEDSupervisor.exe --register-current baseline-v1
```

Avvio supervisionato:

```powershell
dist\SEEDSupervisor.exe --boot --runtime dist\SEED.exe
```

Recovery manuale esplicito:

```powershell
dist\SEEDSupervisor.exe --recover baseline-v1 --reason "owner recovery"
```

Il supervisor:

- fallisce chiuso su pointer, versione, lineage o known-good invalidi;
- considera healthy il runtime solo dopo inizializzazione e token health valido;
- marca known-good solo dopo health riuscito;
- rileva modifiche successive allo snapshot known-good tramite SHA-256;
- registra tentativi, fallback e recovery in log append-only;
- usa `SEED_DATA_ROOT` per garantire che child e supervisor condividano la
  stessa root anche nei test isolati.

S6 protegge snapshot state-based e l'avvio iniziale. Non prova stabilita
continua dopo il health signal, non sceglie binari diversi per versione e non
sostituisce un filesystem transazionale o firme contro un attaccante con pieno
accesso disco.

## Acceptance pratica isolata S1-S5

Il runner seguente crea dati sintetici sotto una root temporanea e attraversa
memoria, lineage, descendant, evaluator, shadow, canary, promotion, riapertura,
rollback e tamper detection:

```powershell
cd C:\Users\Cristian\Documents\Progetti\JARVIS
.\.venv\Scripts\python.exe FrameworkUtenti\seed\scripts\core_acceptance.py
```

Output atteso:

```json
{"status":"passed","checks":12,"report":"...core_acceptance_report.json"}
```

Il runner non usa `%LOCALAPPDATA%\SEED`, rete, provider, OPF, UI o dati reali.
Le observation shadow/canary sono sintetiche e verificano i gate, non la
qualita dell'adattamento reale.

Il follow-up pratico con Ollama Cloud ha inoltre verificato:

- OpenAI Privacy Filter reale;
- persistenza e recall locale di preferenze dichiarate esplicitamente;
- parsing di JSON strutturato anche quando il provider aggiunge fence Markdown;
- reflection reale con candidate valida in shadow e candidate invalida
  bloccata dal builder;
- nessuna promotion automatica.

## Setup dev

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install git+https://github.com/openai/privacy-filter
copy config\config.example.json config\config.json
python run_dev.py
python run_dev.py --repl
```

## Build exe

```powershell
pyinstaller build/seed.spec
# dist/SEED.exe
pyinstaller build/supervisor.spec
# dist/SEEDSupervisor.exe
```

## Dati del runtime corrente

```text
%LOCALAPPDATA%\SEED\
  core_config\config.json
  data\seed.db
  data\traces\*.jsonl
  state\
  capabilities\
  versions\YYYY-MM-DD\
  lineage\events\
  active\current_version.json
  lab\descendants\
  lab\replay_fixtures\
  lab\evaluator_runs\
  lab\canary_leases\
  recovery\known_good.json
  recovery\health\
  recovery\supervisor_logs\
  workspace\
  logs\seed.log
```

Il target aggiunge ancora descendant completi, evaluator comportamentali e
canary con effetti controllati. La struttura prevista e documentata in
`../docs/07_Struttura_Repo.md`.

## Primo avvio target

Il primo avvio non sara una chat vuota e non sara un questionario di
personalita. Mostrera una presenza minimale che:

1. completa avvio e download necessari con stato leggibile;
2. presenta consenso, privacy, mutabilita e rollback;
3. chiede all'utente di parlare di se;
4. raccoglie preferenze tramite conversazione e confronti concreti;
5. mostra cio che pensa di aver compreso per consentire correzioni;
6. entra nel periodo sperimentale di 14 giorni.

## Promemoria distribuzione

1. una API key per utente con hard cap di spesa;
2. nessun upload automatico di memoria, trace o lineage;
3. consenso informato prima di watcher, voce o integrazioni;
4. avviso chiaro sul download iniziale del privacy filter;
5. accesso sempre visibile a pausa, permessi, spiegazioni e rollback;
6. l'esperimento dura 14 giorni, con onboarding al giorno 0 e debrief al giorno 15.

## Runtime Completion locale

Il runtime desktop include ora:

- isolamento reale con container Docker fail-closed oppure processo ristretto
  con ambiente senza segreti e filesystem limitato al workspace;
- observation collector locale consent-first per foreground app e categorie di
  processo, senza titoli, URL, screenshot o contenuti;
- sub-agent locale che esegue task graph di sole capability allowlistate, un
  nodo isolato alla volta;
- tool builder governato: stage, audit AST, test isolato, reviewer e owner gate
  prima dell'installazione;
- lifecycle automatico per evidenze shadow/canary e proposta di promozione;
  la promotion finale non e' automatica;
- brand evolutivo deterministico da eventi locali reali;
- backup/restore, update staging, migrazioni versionate, crash recovery e
  uninstall plan confermato.

Nessun gateway Telegram/mobile/device viene avviato o collegato. Tutto resta
nell'app `SEED.exe`. Comandi locali utili: `:backup`, `:brand`, `:lifecycle`,
`:sandbox`.
