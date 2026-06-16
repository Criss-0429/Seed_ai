# 12 - Piano implementativo SEED

> Questo piano governa lo sviluppo di SEED. Non modifica lo stato o i gate del
> progetto JARVIS.

## Posizione corrente

**Stato (2026-06-13):** su approvazione esplicita owner ("implementa tutto, una
fase alla volta, ordine come pianificato") sono state implementate end-to-end e
**lasciate pronte per review** tutte le fasi rimanenti del piano daemon e del
piano UI:

- **D0** Runtime Option Benchmark — owner-approvato (testo, checkbox owner);
- **D1** Daemon host PC-on · **D2** Worker adapter READ-only · **D-OBS**
  Observation lane read-only · **D3** Sandbox hardening · **D4** Capability
  WRITE_SAFE · **D5** Skills procedurali + delega · **D6** Gateway opzionale;
- **UI U0-U7** (piano 17), incluso **S11.3** pannello voce (U3).

Le capability con effetti o dati sensibili sono **default OFF / dry-run /
consent-gated / owner-gated**. Il daemon in-process D1 e il worker aggregato
READ-only D2 sono invece default ON perche' non possiedono superfici di effetto;
observation, WRITE_SAFE, skills/delega e gateway restano OFF. **Nessun checkbox
spuntato** (D0-D6, UI, S11: spunte riservate a Cristian). Verifiche complessive
dopo UI Integration Hardening: suite `443 passed`, acceptance core `12/12`,
`compileall` e sintassi JS ok. Restano owner: smoke reali voce/microfono/provider,
smoke EXE e apertura dei gate. Non avanzare oltre senza nuova approvazione.

**D0 - Runtime Option Benchmark** (precedente, approvata manualmente dall'owner il
2026-06-13): decisione confermata — OpenHarness backend isolamento/esecuzione,
Hermes pattern registry/skills/delega, OpenClaw pattern daemon/heartbeat/sessioni;
SEED Core resta sempre governatore; prima attivazione futura READ-only. Il
benchmark confronta i pattern solo su fixture sintetiche privacy-safe: non
installa runtime esterni, non usa repo o dati reali e non concede accesso
shell/file.

La fondazione precedente resta disponibile ma non viene dichiarata chiusa senza
gate owner: memoria M1-M4, Cognitive User Knowledge K1-K4, S10 Model Role
Separation, S11.1 backend voce e S11.2 emotion sono implementati e verificati.
S11.3 pannello voce appartiene alla futura fase UI U3.

## Feature Context Pack - UI Integration Hardening / Owner Review Fixes

**Feature esatta:** `UI Integration Hardening / Owner Review Fixes`, autorizzata
dalla richiesta owner del 2026-06-13 dopo l'implementazione D1-D6 e U0-U7.
Questo intervento completa e verifica i collegamenti dichiarati dal piano UI;
non apre nuovi gate daemon e non attiva capability pericolose.

### Fonti e decisioni estratte

- `17_UI_Implementation_Plan.md` e `SEED_UI/`: modalita' presenza,
  conversazione, voce e overlay; ack immediato; stato sempre visibile; controllo,
  accessibilita', design reattivo e mutazioni UI governate.
- `SEED Design Guidelines.dc.html`: A-01..A-10, B-01..B-10 ed E-01..E-05
  devono essere direttive esplicite del design reviewer, non solo riferimenti
  informali.
- `SEED Brand Identity.dc.html`: presenza senza avatar, colore guadagnato,
  motion sobria, evoluzione annunciata e tipografia locale/offline.
- `16_Agentic_Daemon_Plan.md`: daemon e observation restano permission-gated;
  la UI espone stato e controllo ma non crea nuove autorita'.
- `08_Onboarding.md`, `13_ModelRoles_Voice_Plan.md`,
  `11_Contratto_Mutazione.md`: onboarding reale al primo avvio, voce con consenso
  esplicito, review come evidenza e rollback owner-controlled.

### Gap verificati prima dell'intervento

1. La surface caricava Google Fonts: la build UI non era realmente offline.
2. Il focus globale disegnava un secondo rettangolo arancione dentro l'input.
3. L'onboarding esisteva nel core/CLI ma non era esposto al boot della UI.
4. Il pannello voce usava Web Speech del browser, non STT/TTS ElevenLabs gia'
   implementati nel backend SEED.
5. Presenza pura e overlay-first non erano modalita' finestra reali.
6. La superficie Evoluzione era un placeholder nonostante digest/versioni/
   rollback fossero gia' esposti dal bridge.
7. Il DesignDirectivePack includeva le direttive UI solo su richiesta manuale e
   il reviewer rifiutava gli id UI; le Guidelines complete non erano codificate.

### Scope implementativo autorizzato

- rendere la surface priva di dipendenze remote e correggere focus/accessibilita';
- boot UI basato sullo stato onboarding reale;
- collegare hold-to-talk e risposta audio al backend voce consent-gated;
- implementare modalita' full, presenza e overlay con controlli e scorciatoia;
- rendere operativa la superficie Evoluzione con digest/versioni/rollback;
- completare le direttive UI e includerle automaticamente nelle mutation UI;
- aggiungere test di contratto/integrazione, suite completa, build offline e
  smoke della finestra.

### Non-goals e limiti dichiarati

- nessuna attivazione automatica di observation, WRITE_SAFE, skills o gateway;
- nessuna dichiarazione di isolamento container/worktree o invio gateway reale:
  restano limiti gia' documentati di D3/D5/D6;
- nessun accesso silenzioso a microfono, app o dati personali;
- nessuna promotion automatica e nessuna spunta checkbox da parte dell'agente.

### Verifiche richieste

- test bridge onboarding/voce/modalita' finestra/evolution;
- test governance: direttive complete, auto-inclusione UI e reviewer compatibile;
- assenza URL/font/runtime remoti nella surface;
- suite completa, acceptance core, compileall e build EXE;
- smoke visivo/accessibile della UI e aggiornamento knowledge graph.

### Roadmap residua (ordine, tutte gated, dopo go esplicito)

1. **[Priorita' #1] Agentic Background Daemon** — `16_Agentic_Daemon_Plan.md`.
   Daemon background SOLO a PC acceso + funzioni agentiche, dietro sandbox/
   governance SEED. Fasi D0-D6 + **D-OBS** (osservazione read-only di app/browser/
   PC per raccogliere info utente, candidate redatte, permission-gated).
2. **UI da SEED_UI** — `17_UI_Implementation_Plan.md`. Design gia' strutturato
   (Guidelines P0-P5 + Brand + 4 wireframe + Prototype). Fasi U0-U7; include
   **S11.3 pannello voce** (U3) e l'integrazione delle regole UI/UX nel
   DesignDirectivePack cosi' i modelli seguono le Laws of UX (U7).
3. **Test owner di tutto il fatto** — vedi "Test Plan owner" sotto: smoke reale
   provider/voce/emozione/memoria + build EXE, prima di chiudere i gate.

S11.1 backend + S11.2 emotion fatti. La chat scritta resta semplice (hold-key
STT, TTS dopo risposta); il resto della voce/emozione vive nel pannello voce U3.

### Test Plan owner — verifica di tutto il fatto

Da eseguire con provider reali prima della chiusura gate (owner, non agente):

- **S8-S9-S10**: conversazione identita'/counterpoint; ricerca online con
  citazioni; `:shadowreview` (review su candidate sintetiche, verdetti gpt-oss);
  `:report` sezione `models` (separazione ruoli, costo) e `knowledge`.
- **Memoria M1-M4 + K1-K4**: `cosa sai di me` (recall esplicito, no dump);
  ridichiarazione che supera la vecchia (correzione prevale); claim sensibile
  resta candidate; `:reflect` -> dream cycle (estrazione + profilo + predizioni)
  e report `knowledge.predictions`; persistenza memoria tra riavvii; retrieval
  vettoriale attivo (match semantico).
- **S11 voce**: consenso voce; STT (hold-to-talk) -> risposta; TTS espressivo
  `eleven_v3` (risate/riflessione); emozione per-turno solo nel percorso voce;
  budget/fallback; `:report` sezione `voice`.
- **Pacchetto**: build `dist/SEED.exe` + `dist/SEEDSupervisor.exe`; smoke EXE;
  acceptance core 12/12.

Esiti e fix tornano qui come evidenza; i checkbox restano owner.

Memoria completa: Fix recall + M1-M4 + K1-K4 implementati e verificati (K2/K3
approvate verbalmente da Cristian dopo reflection/report reali). Decisioni da
analisi esterna (mem0/agentmemory/graphify/odysseus) in doc 14.

**S10 Model Role Separation And Design Governor** — **S10.1-S10.5 implementate**
(2026-06-12). Ripresa S10.5 dopo le fasi memoria: shadow review su candidate
sintetiche + owner gate (`design_reviewer_real_enabled`, default OFF) prima di
candidate reali. Restano owner: smoke con provider reale, build EXE, apertura
del gate review reale. Gate S9 + tutti i checkbox restano a Cristian.

**S9 Online Research Lane:** implementazione completata il 2026-06-12, smoke test
di Cristian con esito ok (key Exa+Tavily reali), approvazione verbale ricevuta.
Checkbox di chiusura gate ancora vuota per scelta dell'owner.

Cristian ha approvato manualmente S8 dopo test conversazionale reale con Ollama
Cloud: identita distinta, counterpoint, override critico, explainability e
correzione di prolissita hanno funzionato come atteso.
S11.1 backend voce e S11.2 emotion sono implementati; S11.3 UI resta pendente.

## Feature Context Pack - D0 Runtime Option Benchmark

**Feature esatta:** `D0 - Runtime Option Benchmark`.

### Fonti e decisioni estratte

- `16_Agentic_Daemon_Plan.md`: SEED Core resta governatore; runtime esterni sono
  pattern o worker capability-specifici, mai sostituti del core; prima
  attivazione futura READ-only.
- `11_Contratto_Mutazione.md`: nessun artefatto generato puo' auto-promuoversi;
  valutazione, lineage, rollback e autorita' separate restano obbligatori.
- documenti ufficiali JARVIS `VISION.md`, `MISSION.md`,
  `DESIGN_PRINCIPLES.md`, `JARVIS_v6_STACK.md`, `JARVIS_v6_WORKFLOW.md`,
  `JARVIS_v6_IMPLEMENTATION.md`, `JARVIS_v6_AGENT_ECOSYSTEM.md`: capability
  tipizzate, trust/privacy gate prima degli effetti, conversation-first,
  audit senza contenuto personale e provider/runtime dietro adapter.
- wiki `Agentic_Runtime_Options_2026_05.md`, `Hermes_Agent.md`, `OpenClaw.md`,
  `OpenHarness.md`: Hermes offre registry/skills/delega/backend; OpenClaw offre
  daemon/session/heartbeat; OpenHarness offre dry-run, hooks e isolamento.
  Queste fonti sono contesto tecnico subordinato, non autorita' operativa.

### Implicazioni implementative D0

1. Benchmark locale, deterministico e ripetibile su fixture sintetiche.
2. Candidati valutati con criteri espliciti: governance fit, isolamento,
   capability delegation, approval/dry-run, sessioni, privacy/segreti,
   complessita' operativa e rischio di duplicare il core.
3. Ogni punteggio conserva motivazioni e blocker; il report non contiene dati
   utente, prompt, chiavi o contenuti reali.
4. D0 produce una raccomandazione di backend/pattern. Non installa, avvia o
   integra OpenClaw, Hermes o OpenHarness.
5. Nessun worker, daemon, heartbeat, shell, file access o azione agentica viene
   attivato in D0. Questi appartengono alle fasi D1+ gated.

### Piano test D0

- risultati deterministici e ordinamento stabile;
- fixture privacy-safe senza path, chiavi o contenuti reali;
- blocker per sostituzione del Core, shell generica e worker con segreti;
- report JSON auditabile con schema/versione e hash;
- raccomandazione coerente con i vincoli SEED;
- regressione suite completa e acceptance core.

### Rischi / assunzioni

- Il benchmark valuta l'aderenza architetturale, non prestazioni reali dei
  runtime esterni: nessun runtime viene installato o eseguito in D0.
- La raccomandazione non autorizza D1 o fasi successive; richiede gate owner.
- Le fonti JARVIS canoniche correnti vivono sotto `JarvisOfficialDocs`; i file
  produzione disponibili sotto `JarvisProduction/Old` sono stati usati solo
  per orientamento, subordinati ai documenti ufficiali e ai doc SEED.

### Evidenza D0 pronta per review (2026-06-13)

- `seed/core/runtime_bench.py`: benchmark locale deterministico, criteri pesati,
  verdetti per ogni fixture/candidato, blocker espliciti e report SHA-256
  auditabile.
- Decisione proposta: OpenHarness per backend isolamento/esecuzione; Hermes per
  registry/skills/delega; OpenClaw per daemon/session pattern. Nessun runtime
  sostituisce SEED Core; prima attivazione futura resta READ-only.
- Comando locale `:runtimebench`: salva il report sotto
  `%LOCALAPPDATA%\SEED\lab\runtime_bench\`; non chiama provider o runtime esterni.
- Verifica: `7 passed` mirati; suite completa `329 passed`; acceptance core
  `12/12`; `compileall` ok.
- **Approvazione owner (2026-06-13):** Cristian ha approvato manualmente il gate
  D0 via messaggio, autorizzando l'avvio di D1. L'approvazione e' documentata qui;
  **il checkbox sotto resta volutamente vuoto** (la spunta appartiene a Cristian).
- [ ] Chiusura gate D0 - owner gate Cristian

## Feature Context Pack - D1 Daemon host PC-on

**Feature esatta:** `D1 - Daemon host PC-on` (`16_Agentic_Daemon_Plan.md`).
Autorizzata dall'approvazione manuale owner del gate D0 (2026-06-13).

### Fonti e decisioni estratte

- `16_Agentic_Daemon_Plan.md` (fase D1): daemon background SOLO a PC acceso e con
  SEED attivo; vive nel processo SEED supervisionato (estende Supervisor S6 +
  Scheduler); nessun servizio OS, auto-start o always-on; heartbeat/cron solo
  entro la sessione, con cooldown e suppression; **ZERO azioni agentiche di
  scrittura** in D1.
- `16_Agentic_Daemon_Plan.md` (proattivita' governata): default silenzio; parla
  solo se `expected_value > interruption_cost + privacy_cost + trust_cost`;
  suppression e cooldown; mai azione sensibile autonoma; audit aggregato senza
  contenuto personale.
- `11_Contratto_Mutazione.md`: separazione delle autorita' e audit minimo; nessun
  artefatto si auto-promuove. Il daemon produce solo decisioni rivedibili, non
  promozioni ne effetti.
- documenti ufficiali JARVIS (`DESIGN_PRINCIPLES.md`, `MISSION.md`,
  `JARVIS_v6_WORKFLOW.md`, `JARVIS_v6_AGENT_ECOSYSTEM.md`): conversation-first,
  trust/privacy gate prima degli effetti, audit senza testo personale, capability
  dietro registry. Contesto subordinato ai doc SEED.

### Implicazioni implementative D1

1. Nuovo `seed/core/daemon.py`: core deterministico (`ProactivityCandidate`,
   `governed_net_value`, `decide_proactivity`, `build_heartbeat`) + loop
   supervisionato `BackgroundDaemon` (thread daemon + `threading.Event`,
   mirroring di `Scheduler`).
2. Il daemon non riceve registry/broker/sandbox/provider: **per costruzione** non
   puo' eseguire capability, shell, file reali o worker esterni. Non importa
   `subprocess`, `os` o `capabilities`.
3. Coda proattivita' locale e persistente (`memory.proactivity_queue`) +
   `daemon_state` (tick, last_heartbeat, last_emit per il cooldown).
4. La coda referenzia la memoria con un `topic_ref` **opaco** (es. `knowledge:12`)
   e una categoria generica allowlistata: mai valore, frase o segreto. `validate`
   rifiuta testo grezzo, categorie ignote e costi fuori range.
5. Gate decisione (ordine): scadenza -> privacy hard gate -> suppression
   categoria -> cooldown -> silenzio di default -> emit. `emit` marca solo la
   candidate come da mostrare all'owner (la UI e' fuori scope), non esegue nulla.
6. Lifecycle legato a SEED: `start_background()` avvia il daemon, `shutdown()` lo
   ferma. `can_run=lambda: onboarding.complete` mantiene il battito vivo ma non
   processa la coda finche' l'onboarding non e' concluso.
7. Audit **esclusivamente aggregato**: il battito porta solo conteggi e flag dei
   confini (write_actions=0, os_service=False, ...), mai topic_ref o testo.
   Telemetria sezione `daemon`. Comando locale `:daemon` per lo snapshot review.

### Piano test D1

- formula `governed_net_value` e gate decisione deterministici e spiegabili;
- emit / silenzio di default / cooldown (transiente) / suppression categoria
  (transiente) / privacy hard gate (terminale) / scadenza;
- coda persistente senza testo grezzo; `enqueue` rifiuta ref non opaco;
- tick: emit poi cooldown che differisce fino allo scadere della finestra;
- `can_run=False` -> battito vivo, coda intatta;
- audit aggregato senza topic_ref; daemon senza superficie di esecuzione e modulo
  senza primitive di esecuzione;
- lifecycle thread start/stop in-process; daemon disabilitato non parte;
- snapshot review aggregato; comando `:daemon` locale;
- regressione suite completa + acceptance core.

### Rischi / assunzioni

- Il daemon e' in-process e gira anche in dev/REPL (non solo sotto Supervisor):
  e' comunque legato alla vita del processo SEED, quindi a SEED chiuso non resta
  nulla; nessun servizio OS viene creato. La distinzione "supervisionato" e'
  garantita dal fatto che il processo SEED parte solo via runtime/Supervisor.
- `emit` in D1 non notifica nulla: marca la candidate per una futura superficie
  UI (U-fase). Nessun canale di output autonomo e' stato introdotto.
- La risoluzione reale del valore atteso/costo delle candidate (alimentata da
  K3/M4) e l'ingestione da observation lane (D-OBS) restano fuori scope D1.

### Evidenza D1 pronta per review (2026-06-13)

- `seed/core/daemon.py`: core deterministico + loop supervisionato in-process,
  heartbeat aggregato, coda proattivita' con cooldown/suppression/silenzio di
  default, zero superficie di esecuzione.
- `seed/core/memory.py`: tabelle `proactivity_queue` (ref opaco, mai testo) e
  `daemon_state`; CRUD coda + stato.
- `seed/core/config.py`: `DaemonConfig` (enabled, heartbeat, cooldown,
  min_net_value); `config.example.json` sezione `daemon` documentata.
- `seed/core/app.py`: daemon costruito senza registry/broker; start in
  `start_background`, stop in `shutdown`; comando `:daemon` + `run_daemon_review`.
- `seed/core/telemetry.py`: sezione `daemon` (conteggi battiti/decisioni/coda,
  flag confini). Solo aggregati.
- Verifica: `21 passed` mirati (`tests/test_daemon.py`); suite completa
  `350 passed`; acceptance core `12/12`; `compileall` ok.
- D1 NON e' dichiarata completata: restano owner lo smoke reale, la build EXE e
  l'apertura del gate. Il checkbox resta vuoto.
- [ ] Chiusura gate D1 - owner gate Cristian
  (implementazione e suite verde `351 passed` 2026-06-13; smoke D1 ok, incl. fix
  ordine gate decisione; smoke reale e build EXE restano owner; spunta riservata
  a Cristian)

## Feature Context Pack - D2 Worker adapter READ-only

**Feature esatta:** `D2 - Worker adapter READ-only` (`16_Agentic_Daemon_Plan.md`).
Autorizzata dall'owner il 2026-06-13 dopo lo smoke D1.

### Fonti e decisioni estratte

- `16_Agentic_Daemon_Plan.md` (fase D2 + regola architetturale): worker dietro
  capability registry, delega capability-specifica, mai canale generico verso un
  orchestratore esterno; **prima attivazione READ-only** (es. `worker.runtime_status`);
  comandi deterministici/locali NON passano dal worker; niente segreti ai worker.
- `16_Agentic_Daemon_Plan.md` (sicurezza): **action contract** per ogni capability
  worker (input/output schema, risk_class, allowed_scopes, side_effect_type,
  requires_approval, supports_dry_run, supports_rollback, observability_signal);
  expected observation + rollback; audit aggregato senza contenuto personale.
- `04_Sandbox_Sicurezza.md` / `permissions.py`: risk class `safe`/`read_safe`
  non richiedono prompt; `destructive` vietata; ogni azione passa dal broker.
- `11_Contratto_Mutazione.md`: separazione autorita', audit minimo; il worker non
  promuove nulla, esegue solo letture allowlistate.

### Implicazioni implementative D2

1. Nuovo `seed/core/worker.py`: `ActionContract` tipizzato + `ReadOnlyWorker`
   (registry azioni worker). `ActionContract.validate` impone gli invarianti D2:
   `side_effect_type == "read"`, `risk_class in {safe, read_safe}`,
   `requires_approval == False`, `supports_dry_run == True`. Qualsiasi azione
   non-read viene **rifiutata in registrazione** (read-only per costruzione).
2. Prima azione: `worker.runtime_status` — ritorna stato runtime AGGREGATO
   (daemon running, profondita' coda, tick, heartbeat) dal daemon D1. Nessun dato
   personale, nessun segreto, nessuna query.
3. Esecuzione dietro `PermissionBroker` (autorizza; `read_safe` non chiede prompt
   ma passa comunque dal broker) + audit aggregato (`worker_invoked`: action, ok,
   risk_class, side_effect_type, dry_run, write_actions=0). Mai output personale
   nell'audit.
4. **Niente segreti al worker**: il worker riceve solo un provider di stato
   aggregato, non config/key/memoria grezza. `run` rifiuta argomenti non previsti
   dallo schema o che sembrano segreti.
5. `supports_dry_run`: la dry-run di una lettura non ha effetti e ritorna il piano
   + observability_signal senza invocare l'handler.
6. **Expected observation**: ogni azione dichiara `observability_signal`; il
   risultato include `observed` (active inference). Rollback no-op per le letture.
7. ZERO scrittura, zero shell, zero file reale, zero worker esterno/subprocess
   (l'isolamento container/ristretto e' D3, fuori scope). Allowlist azioni in
   `WorkerConfig.allowed_actions` (default solo `worker.runtime_status`).
8. Integrazione `SeedApp`: `self.worker`, comando `:worker` + `run_worker_status`;
   telemetria sezione `worker`.

### Piano test D2

- `ActionContract.validate` rifiuta side_effect non-read, risk_class non read,
  requires_approval True, dry_run non supportato;
- `worker.runtime_status` ritorna stato aggregato, nessun valore personale/segreto;
- esecuzione passa dal broker (autorizzata) e lascia audit aggregato;
- dry-run non invoca l'handler e non ha effetti;
- azione non allowlistata o non registrata viene rifiutata;
- worker rifiuta argomenti fuori schema / segreti;
- worker senza superficie di scrittura/shell; modulo senza subprocess/os;
- comando `:worker` locale; regressione suite + acceptance.

### Rischi / assunzioni

- D2 e' in-process: nessun backend di isolamento reale (container/subprocess
  ristretto) — quello e' D3. Per D2 l'unica azione e' una lettura di stato
  aggregato gia' privacy-safe, quindi l'assenza di sandbox dedicata non espone
  dati.
- `expected observation`/rollback sono presenti come contratto; per le sole
  letture il rollback e' no-op. Diventano sostanziali in D4 (WRITE_SAFE).
- Nessuna anticipazione di D3-D6 o UI.

### Evidenza D2 pronta per review (2026-06-13)

- `seed/core/worker.py`: `ActionContract` tipizzato (validate impone gli
  invarianti D2: side_effect=read, risk_class read-only, no approval, dry-run) +
  `ReadOnlyWorker` (registry azioni, allowlist, permission broker, audit
  aggregato, dry-run, expected observation). `build_runtime_status_worker` +
  azione `worker.runtime_status` che legge SOLO lo stato aggregato del daemon.
- `seed/core/config.py`: `WorkerConfig` (enabled, allowed_actions=[`worker.runtime_status`]);
  `config.example.json` sezione `worker` documentata.
- `seed/core/app.py`: `self.worker` costruito con un provider di stato aggregato
  (`daemon.review`), mai config/key; comando `:worker` + `run_worker_status`.
- `seed/core/telemetry.py`: sezione `worker` (invocazioni/ok/dry-run/blocked,
  write_actions=0). Solo aggregati.
- **Fix concorrenza** (`seed/core/memory.py`): la connessione SQLite condivisa tra
  thread (main + scheduler + daemon) e' passata ad autocommit
  (`isolation_level=None`) + `busy_timeout`, eliminando la race
  "cannot commit - no transaction is active" emersa con daemon+worker attivi sotto
  `start_background`. `clear_onboarding` mantiene atomicita' con BEGIN/COMMIT
  esplicito. Emerso e corretto durante lo smoke D2.
- Verifica: `13 passed` mirati (`tests/test_worker.py`); suite completa
  `364 passed`; acceptance core `12/12`; `compileall` ok. Smoke D2 end-to-end via
  `SeedApp` (status read-only dal broker, audit aggregato, dry-run, azione ignota
  bloccata, sezione telemetria `worker`).
- Build `dist/SEED.exe` + `dist/SEEDSupervisor.exe` rigenerati 2026-06-13.
- D2 NON dichiarata completata: restano owner lo smoke reale e l'apertura del
  gate. Checkbox vuoto.
- [ ] Chiusura gate D2 - owner gate Cristian
  (implementazione e suite verde `364 passed` 2026-06-13; smoke reale e gate
  restano owner; spunta riservata a Cristian)

## Feature Context Pack - D-OBS / D3 / D4 / D5 / D6 / UI (blocco 2026-06-13)

Implementati in sequenza su approvazione owner. Tutti default OFF / gated.
Fonti: `16_Agentic_Daemon_Plan.md` (fasi + sicurezza + non-goals),
`17_UI_Implementation_Plan.md`, `11_Contratto_Mutazione.md`, `03_PrivacyGate.md`,
`04_Sandbox_Sicurezza.md`, doc ufficiali JARVIS (subordinati).

### D-OBS - Observation lane READ-only
- `seed/core/observation.py`: `ObservationSignal`/`decide_observation`/
  `ObservationLane`. READ-only assoluto; **consenso per-classe default OFF**
  (`memory.observation_consent`); sensibile escluso; salienza deterministica;
  produce SOLO candidate-ipotesi a bassa confidenza (`KnowledgeStore`,
  `claim_type=hypothesis`, mai fatti); revoca = **purge** dei derivati; audit
  aggregato (mai redacted_ref). `ObservationConfig` (default OFF). `:observation`.
- Test `test_observation.py` (13). Confine: nessuna azione, nessuna scrittura.

### D3 - Sandbox hardening
- `seed/core/worker_sandbox.py`: tier isolamento (`in_process_read` /
  `restricted_subprocess` / `container` futuro), **trust gate** (`destructive`
  vietata, `write/execute/network` -> approval owner, observability bassa ->
  blocco, container non disponibile -> blocco), dry-run-first, expected
  observation, rollback requirement. Integrato come hardening nel worker D2.
- Test `test_worker_sandbox.py` (12).

### D4 - Capability WRITE_SAFE
- `seed/core/write_safe.py`: `WriteSafeWorker` con write reversibili allowlistate
  dietro gate D3 (**approval owner** + dry-run + rollback + observation;
  **auto-rollback se l'observation non conferma**), path allowlist **solo
  workspace**, azione d'esempio `worker.write_workspace_note`. **Default OFF**
  (`WorkerConfig.write_safe_enabled`, allowlist vuota). `:writesafe`.
- Test `test_write_safe.py` (9). Confine: niente shell, niente path arbitrari,
  `destructive` vietata.

### D5 - Skills procedurali + delega
- `seed/core/skills.py`: `SkillRegistry` **review-gated** (install richiede audit
  + reviewer + owner; **nessun self-install**), `audit_skill` (capability
  allowlistate, no destructive), **Task Graph IR** (`TaskGraph` aciclico, deps
  esistenti, capability allowlistate), `plan_delegation` a sub-agenti isolati
  (gated; isolamento reale futuro -> degrada chiuso). `SkillsConfig` default OFF.
  `:skills`. Test `test_skills.py` (14).

### D6 - Gateway opzionale
- `seed/core/gateway.py`: `CrossSurfaceGateway` (Telegram/altro) dietro **privacy
  gate obbligatorio + consenso per-superficie** (`memory.gateway_consent`),
  secret-scan, **nessun invio reale** (prepara piano outbound redatto/gated).
  `GatewayConfig` default OFF. `:gateway`. Test `test_gateway.py` (7).

### UI U0-U7 (incl. S11.3)
- `seed/ui/surface/index.html`: **riproduzione fedele del design
  `SEED_UI/SEED Prototype.dc.html` (+ Brand Identity)** — stessa palette oklch,
  tipografia DM Sans/DM Mono, sigillo orb seme+anelli, layout (title bar,
  colonna conversazione max 660px, presence header, bolle user/seed, "perche'?"
  espandibile, indicatore "STO PENSANDO", input bar autogrow, voice overlay,
  selettore superfici, Modello Utente, Permessi, toast). **Reimplementato in JS
  vanilla** (il prototipo usava il runtime DC/React via CDN + `window.claude`,
  non utilizzabili offline): l'app resta **Python/pywebview con build EXE**, la
  chat passa dal backend `window.pywebview.api.send_message`. Font Google con
  fallback di sistema (EXE usabile offline).
- Mappatura fasi sul design: U0 token/orb 5 stati (idle/listening/thinking/
  speaking) + reduce-motion; U1 chat colonna con orb di stato, Esc/invio; U2
  superfici (Ctrl+.) **Modello Utente** (claim K1 reali con provenance/dots,
  "e' vero"/"non e' cosi'" -> `correct_claim` conferma/supersession) + **Permessi
  e Privacy** (toggle consenso osservazione reali, watcher, esporta/cancella);
  U3 **voice overlay (= S11.3)** hold-to-talk con fallback testo; U4 colore
  guadagnato (hue/chroma dal manifest); U5 presenza nel layout dell'orb; U6
  selettore/overlay via Ctrl+.. "perche'?" -> `ui_explain_last` (deterministico).
  P0 (controlli sempre visibili) e P1 (focus/reduce-motion) rispettati.
- `seed/ui/shell.py` `JsApi`: hook `user_model`/`correct_claim`/`permissions`/
  `set_observation_consent`/`revoke_observations`/`daemon_status`/voce.
- `seed/core/app.py`: `ui_user_model` (esclude sensibili, provenance),
  `ui_correct_claim` (conferma/supersession), `ui_permissions`,
  `ui_set_observation_consent`, `ui_revoke_observations`.
- **U7 governance**: `seed/core/ui_governance.py` — gerarchia P0-P5 + Laws of UX
  come `ui_directives`; `evaluate_ui_mutation` deterministico (P0/P1 ->
  non candidabile; P4 senza evidenza P2/P3 -> non candidabile);
  `directive_pack.build_directive_pack(include_ui_directives=True)` aggiunge la
  sezione e cambia il version. Test `test_ui.py` (14).

### Verifica blocco
- nuovi test: `test_observation` 13, `test_worker_sandbox` 12, `test_write_safe`
  9, `test_skills` 14, `test_gateway` 7, `test_ui` 14.
- suite completa `433 passed`; acceptance core `12/12`; `compileall` ok; EXE
  ricostruiti. Tutte le lane default OFF; nessuna attivazione; nessun checkbox.

### Resta owner (non fatto)
- smoke reali con provider/voce/PC; attivazione delle lane (observation/write-safe/
  skills/gateway) e apertura dei gate; backend isolamento reale (container/worktree)
  per D3/D5; invio reale del gateway D6; test owner UI su EXE.

- [ ] Chiusura gate D-OBS - owner gate Cristian
- [ ] Chiusura gate D3 - owner gate Cristian
- [ ] Chiusura gate D4 - owner gate Cristian
- [ ] Chiusura gate D5 - owner gate Cristian
- [ ] Chiusura gate D6 - owner gate Cristian
- [ ] Chiusura gate UI U0-U7 (incl. S11.3) - owner gate Cristian

## Feature Context Pack - K3 Salience / Awareness

**Feature esatta:** `K3 - Salience / Awareness`.

### Fonti e decisioni estratte

- `15_Cognitive_User_Knowledge_Plan.md`: scoring deterministico e spiegabile;
  decide cosa entra nel contesto e cosa resta `remember_silently`; default
  silenzio; niente dump.
- wiki `Jarvis_Cognitive_User_Model_Execution_Harness.md`: formula iniziale con
  relevance, recurrence, duration, deviation, evidence, timing, risk e penalita
  privacy/interruzione/stale; salienza non deve essere una chiamata LLM.
- `04-stage-c-salience-2-implementation-spec.md`: score e reasons persistibili;
  sensibilita/rischio/cooldown possono forzare silence/review.
- `JarvisPlusCognitionWorkflow.md`: interaction-time riceve solo metadati
  sintetici e contesto selezionato, mai raw dump.

### Implicazioni implementative K3

1. Nuovo `SalienceDecision{item_ref, score, reasons, action}` puro Python.
2. K3 filtra l'output M3 prima del system prompt. Nessun fallback ai primi claim.
3. Claim sensibili, candidate, superseded o contraddetti non entrano nel
   contesto normale; restano memoria silenziosa/review.
4. Living profile approvato viene filtrato ai soli source claim salienti.
   Counterpoint approvato entra solo se pertinente alla richiesta.
5. Decisioni persistite senza query o valori personali; report solo aggregati.
6. K3 non invia notifiche e non parla autonomamente: proattivita live e K4/M4
   restano fuori scope.

### Piano test K3

- formula deterministica e reasons stabili;
- pertinente entra, non pertinente resta silenzioso; nessun fallback/dump;
- sensitivity/stale/contradiction bloccano;
- recurrence/confidence influenzano lo score;
- profilo/counterpoint approvati filtrati per rilevanza;
- audit/report aggregate-only; regressione M1-M3/K1-K2/S8.

### Rischi / assunzioni

- Il gate iniziale privilegia precisione rispetto a recall: sinonimi deboli
  possono restare silenziosi finche' la rilevanza non e' sufficientemente
  spiegabile.
- Duration/deviation sono stimati solo da metadati disponibili; K4/M4
  aggiungeranno calibrazione e consolidamento piu ricchi.

### Evidenza K3 pronta per review (2026-06-12)

- `seed/core/salience.py`: score puro Python, deterministico e spiegabile;
  azioni limitate a `use_context` e `remember_silently`.
- `SeedApp._system_prompt`: K3 filtra l'output M3; rimosso ogni fallback che
  scarichi claim non pertinenti. Claim sensibili, candidate, stale o fortemente
  contraddetti restano fuori dal prompt.
- living profile approvato filtrato per source claim salienti; counterpoint
  approvato filtrato per pertinenza lessicale.
- decisioni persistite localmente senza query/valori; report espone solo numero
  decisioni e conteggio per azione.
- `tests/test_salience.py` copre formula, default silenzio, blocchi, graph
  relevance, filtro profilo/counterpoint, prompt end-to-end e telemetria
  aggregate-only.
- verifica: `50 passed` sui test mirati; suite completa `292 passed`;
  `compileall` ok.

Rischio residuo: strategia precision-first puo' ignorare sinonimi semanticamente
validi quando embedder locale non e' configurato o il legame non e' presente
nel grafo. Nessuna proattivita autonoma e stata introdotta; resta fuori scope.

### Fix gate K3 post test owner - trasparenza senza disclosure operativa

Il test owner ha confermato salienza, ricerca e suggerimenti contestuali, ma ha
mostrato un confine mancante: SEED deve spiegare chiaramente filosofia,
capacita, dati osservati e controlli utente senza divulgare prompt nascosti,
direttive interne, chain-of-thought, soglie esatte, dettagli utili al bypass o
istruzioni passo-passo per replicare i meccanismi interni. Il digest delle
mutazioni resta visibile: e' trasparenza su possibili effetti, non disclosure
operativa. Implementato con risposta deterministica alle richieste meta e
contratto nel system prompt. Verifica post-fix: `34 passed` mirati,
suite completa `294 passed`, `compileall` ok.

Nota futura, non implementata in K3: Activity Watcher gia' osserva localmente
app foreground e titoli redatti. Dopo M4/K4 potra' trasformare segnali media
locali (es. Spotify o media session browser) in ipotesi candidate e domande
prudenziali alla sessione successiva; mai in fatti autonomi, mai contenuti
remoti senza consenso separato.

## Feature Context Pack - K2 Living Profile + Counterpoint

**Feature esatta:** `K2 - Living Profile + Counterpoint`.

**Stato di ingresso verificato (2026-06-12):** M2, K1 e M3 esistono nel runtime;
suite mirata `test_knowledge.py`, `test_user_knowledge.py`, `test_retrieval.py`,
`test_recall.py`: `37 passed`.

### Fonti e decisioni estratte

- `09_Personalita_Compatibile.md`: la personalita compatibile combina identita
  stabile SEED, modello dell'utente, storia relazionale, modalita contestuale e
  counterpoint; non deve diventare una copia dell'utente.
- `15_Cognitive_User_Knowledge_Plan.md`: il living profile e' una vista
  rigenerata dai claim attivi, versionata e reviewable; il counterpoint contiene
  dubbi e letture potenzialmente errate; ipotesi mai usate come istruzioni.
- `JarvisPlusIdentityAndCounterpoint.md`: profilo e counterpoint sono derivati
  rigenerabili, non source of truth; ogni versione conserva delta, fonti,
  confidenza e stato review; accesso solo nel contesto privato 1:1.
- wiki `Jarvis_Cognitive_User_Model_Execution_Harness.md`: fatti e ipotesi
  restano separati; l'LLM non promuove direttamente conoscenza.
- piano longitudinale JARVIS `04-longitudinal-cognition-live-PLAN.md`: solo
  versioni approvate possono entrare nel runtime context.

### Implicazioni implementative K2

1. Il living profile viene ricostruito interamente dai claim attivi, normali e
   privati. Non viene patchato e non contiene claim candidate o sensibili.
2. Il counterpoint e' un derivato separato, costruito da ipotesi/pattern deboli
   e contraddizioni; conserva incertezza e source claim ids.
3. Entrambi sono append-only, versionati, reviewable e correggibili. Solo la
   versione approvata entra nel prompt, sempre come DATO e mai come istruzione.
4. Contenuti del profilo/counterpoint non entrano in telemetria aggregata.
5. K2 non introduce salienza K3, decay/consolidamento M4 o calibrazione K4.

### Piano test K2

- ricostruzione completa e rimozione di claim superseded;
- versioni, delta e source claim ids;
- esclusione di candidate, sensibili e scope non privato dal profilo;
- counterpoint separato con confidenza e fonti, senza promozione a fatto;
- solo versioni approvate e contesto privato 1:1 nel prompt;
- telemetria senza contenuto personale; regressione M2/K1/M3/S8.

### Rischi / assunzioni aperte

- Il primo builder e' deterministico: qualita semantica limitata ma auditabile.
- L'approvazione e' esplicita; senza versione approvata il runtime continua con
  il comportamento S8/M3 esistente.
- K2 non decide cosa sia saliente nel turno: questa responsabilita resta K3.

## Feature Context Pack - Memory Consolidation (M1-M4)

Piano canonico completo: `14_Memory_Consolidation_Plan.md`. Fonti: wiki JARVIS
`Jarvis_Memory_Architecture.md`, `Jarvis_User_Knowledge_Ontology.md`,
`Jarvis_Cognitive_User_Model_Execution_Harness.md` (subordinate ai doc SEED).

### Problema (smoke reale Cristian 2026-06-12)

1. recall che dumpa il database: "come sai X su di me?" -> elenco esatto di tutte
   le preferenze, perche' il normalizzatore LLM del router classificava una
   domanda come `list_preferences` e ne imparava un alias permanente;
2. memoria non funzionante: `_history` solo in RAM (amnesia a ogni riavvio), la
   conoscenza non viene usata per rilevanza ma con un taglio cieco `[:20]`.

### Fasi

Pilastro A - substrato memoria (`14_Memory_Consolidation_Plan.md`):

| Fase | Scope | Stato |
|---|---|---|
| Fix recall | recall solo da comando esplicito, mai indovinato dall'LLM; pulizia alias appresi male | fatto (2026-06-12) |
| M1 | persistenza cross-sessione + selezione fatti per rilevanza deterministica nel prompt | fatto (2026-06-12) |
| M2 | ontologia tipata (fact/state/routine/pattern/preference/relation/hypothesis/boundary) con provenance/confidence; candidate->review; supersession + contradiction check (anti-staleness) | fatto (2026-06-12) |
| M3 | edge semantici tipati pesati temporali + retrieval triple-stream (lexical+vector locale+graph) fuso RRF, esplicabile | fatto (2026-06-12) |
| M4 | dream cycle reviewable (consolidamento sleep-time + digest, predizioni, stale cascade) | fatto (2026-06-12) |

Pilastro B - modello cognitivo dell'utente (`15_Cognitive_User_Knowledge_Plan.md`),
cuore filosofico del progetto, costruito sul substrato:

| Fase | Scope | Stato |
|---|---|---|
| K1 | user knowledge ontology: claim tipizzati sull'utente con scope/sensitivity/confidence/valid-time; cattura esplicita live + estrazione candidate-only; sensibili fuori dal contesto; recall esplicito; ipotesi != fatto | fatto (2026-06-12) |
| K2 | living profile rigenerato dai claim (versionato, reviewable) + counterpoint; alimenta il system prompt S8 | fatto (2026-06-12, approvazione verbale owner) |
| K3 | salienza/awareness deterministica: cosa entra nel contesto, "usa la conoscenza solo se rilevante", spiegabile | fatto (2026-06-12, approvazione verbale owner) |
| K4 | predict-calibrate (pattern che predicono, calibrati Brier) + gate di sicurezza (sensibile->candidate, correzione prevale, stale cascade) | fatto (2026-06-12) |

### Evidenza Fix recall (2026-06-12)

- `seed/core/router.py`: `_RECALL_INTENTS = {list_preferences, list_notes}`. Il
  normalizzatore LLM non puo' piu' restituirli (una domanda non diventa recall);
  niente alias appreso. All'avvio `prune_aliases_for_intents` rimuove gli alias
  di recall imparati male da sessioni precedenti (self-heal).
- `seed/core/memory.py`: `prune_aliases_for_intents`.
- Il recall esatto resta disponibile solo via pattern esplicito ("cosa
  preferisco", "le mie note").
- Test: 4 nuovi in `test_router.py` (classe `TestRecallDiscipline`).

### Evidenza M1 (2026-06-12)

- `seed/core/recall.py` (nuovo): `select_relevant` deterministico, zero token —
  overlap lessicale (stopword IT/EN) + boost recency; un item entra solo se
  pertinente (min overlap), mai dump; `explain` ritorna i token in comune
  (spiegabilita'). Fetta lessicale del retrieval; vettori/graph in M3.
- `seed/core/memory.py`: `recent_chat(limit)` ricarica gli ultimi turni di chat
  in ordine cronologico (esclude onboarding).
- `seed/core/app.py`: `_history` ricaricato da `recent_chat` all'avvio (SEED non
  riparte amnesico); `_system_prompt(decision, user_text)` seleziona i fatti per
  RILEVANZA alla richiesta corrente (fallback ai piu' recenti se nessuno
  pertinente), al posto del taglio cieco `[:20]`.
- Test: `test_recall.py` (9): selezione solo pertinenti, query senza segnale ->
  vuoto (non dump), recency tie-break, `recent_chat` round-trip/limite,
  persistenza cross-sessione end-to-end su `SeedApp`.

### Evidenza M2 (2026-06-12)

- `seed/core/memory.py`: tabella `knowledge` bi-temporale (claim_type, subject,
  value, confidence, confidence_source, scope, sensitivity, valid_from/valid_to,
  superseded_at, provenance, lifecycle_state, review_state) + CRUD
  (`add_knowledge`, `active_knowledge`, `knowledge_active_by_key`,
  `supersede_knowledge`, `set_knowledge_review`, `all_knowledge`).
- `seed/core/knowledge.py` (nuovo): `UserClaim` (contratto + `normalized`: cap
  confidenza inferenze a 0.45, ipotesi/pattern mai esplicite) + `KnowledgeStore`
  (promozione governata + **supersession/contradiction anti-staleness**: nuovo
  valore esplicito per la stessa chiave `(claim_type, subject)` supera il vecchio
  bi-temporalmente; un'inferenza non supera mai un fatto esplicito; stesso valore
  = NOOP) + `KnowledgeExtractor` (candidate-only via LLM, puro, non scrive).
- `seed/core/app.py`: `KnowledgeStore`+`KnowledgeExtractor` istanziati;
  `learn_from_recent` estrae candidate dalla conversazione recente; il system
  prompt ora unisce fatti legacy + conoscenza tipata ATTIVA per rilevanza (le
  ipotesi candidate NON entrano come fatti: ipotesi != fatto).
- `seed/core/scheduler.py`: hook `on_consolidate` -> l'estrazione gira
  **sleep-time** (reflection notturna/`:reflect`), gated da onboarding completo;
  zero costo per-turno.
- `seed/core/telemetry.py`: sezione `knowledge` nel report (conteggi per tipo e
  lifecycle, superseded = indicatore di staleness). Solo conteggi, mai valori.

### Evidenza K1 (2026-06-12)

- `seed/core/user_knowledge.py` (nuovo): `capture_explicit` deterministico (zero
  token) per dichiarazioni esplicite chiare (nome, residenza, lavoro, confini),
  pattern stretti per non inventare claim; classificazione `sensitivity`
  (salute/religione/orientamento/politica). Le inferenze ricche restano
  all'estrattore LLM candidate-only (M2).
- `seed/core/app.py`: cattura live nel loop chat -> `KnowledgeStore.record` (la
  ri-dichiarazione di uno slot supera il vecchio = la correzione dell'utente
  prevale). Nel system prompt i claim **sensibili** sono esclusi (consenso/
  rilevanza esplicita). Nuovo recall ESPLICITO `list_knowledge` ("cosa sai di
  me") raggruppato per tipo, esclude i sensibili, ri-idrata i placeholder.
- `seed/core/router.py`: `list_knowledge` aggiunto a `_RECALL_INTENTS` (recall
  solo da comando, mai indovinato dall'LLM).

### Evidenza M3 (2026-06-12)

- `seed/core/memory.py`: tabella `knowledge_edges` (source/target/edge_type/
  weight/confidence/valid-time/provenance) + API (`add_edge`, `all_edges`,
  `edges_for`). Taxonomy edge in `knowledge.py` `EDGE_TYPES` (supports,
  contradicts, supersedes, attenuates, activates, inhibits, predicts, explains,
  co_occurs, depends_on).
- `KnowledgeStore.record`: su supersession crea un edge `supersedes` new->old
  (storia interrogabile).
- `seed/core/retrieval.py` (nuovo): `rrf_fuse` (Reciprocal Rank Fusion, K=60) +
  `rank_candidates` triple-stream — lexical (M1) + vector (opzionale) + graph
  proximity (claim collegati via edge ai seed lessicali). Degrada con grazia:
  senza embedder/edge resta lessicale. Esplicabile (ogni stream e' un ranking).
- `seed/core/embeddings.py` (nuovo): `LocalEmbedder` opt-in, lazy. Se
  `sentence-transformers`/modello mancano -> None, retrieval su lexical+graph
  (come BM25 sempre attivo in agentmemory). Modello multilingue di default.
- `seed/core/config.py`: `models.embedding_enabled` (default OFF: nessun download
  a sorpresa) + `embedding_model`. `seed/core/app.py`: il system prompt usa
  `retrieval.rank_candidates` con edge + embedder.
- Dipendenza: `sentence-transformers` aggiunta a requirements (vector opt-in).

### Evidenza K2 pronta per review (2026-06-12)

- `seed/core/living_profile.py` (nuovo): builder deterministico che rigenera
  interamente il living profile dai claim attivi, normali e privati; costruisce
  separatamente il counterpoint da hypothesis/pattern candidate; nessuna patch
  incrementale e nessuna promozione di ipotesi a fatto.
- `seed/core/memory.py`: tabelle append-only `living_profile_versions` e
  `counterpoint_versions`, con versione, fonti, delta/confidenza e review state.
  Le versioni approvate precedenti restano attive finche' una nuova candidata
  non viene approvata.
- `seed/core/personality.py` + `seed/core/app.py`: solo derivati approvati e nel
  canale privato 1:1 entrano nel system prompt, marcati esplicitamente come
  **DATI, non istruzioni**. Senza approvazione resta il comportamento S8/M3.
- Comandi core locali e pattern-only: `mostrami il mio profilo`, `mostrami il
  counterpoint`, `approva il profilo`, `approva il counterpoint`. Approvazioni e
  recall K2 non possono essere indovinati dal normalizzatore LLM.
- `seed/core/telemetry.py`: esporta solo conteggi di versioni/review state; mai
  sezioni, frammenti, subject o valori personali.
- Test K2: `test_living_profile.py` copre rigenerazione/supersession, versioni e
  delta, esclusioni privacy/scope/candidate, separazione counterpoint, accesso
  privato, approval gate, comandi locali e telemetria aggregate-only.
- Fix da test owner reale: nell'EXE grafico `:reflect` e `:report` venivano
  inviati come messaggi normali al modello perche' gestiti solo dal loop REPL.
  Ora `handle_message` li intercetta prima di onboarding/router/LLM; `:reflect`
  invoca davvero scheduler + consolidamento K2 anche dalla UI.
- Fix richiesti dal primo reflection reale owner:
  - provenance obbligatoria: claim live collegati all'episodio utente; claim
    sleep-time collegati agli episodi recenti usati dall'estrattore;
  - split deterministico di dichiarazioni concatenate (es. residenza +
    interesse), con riparazione conservativa dei claim concatenati gia' attivi;
  - report distingue il `legacy_evolution_user_model` dal living profile K2 e
    riporta lo stato aggregato dell'ultima versione;
  - `:reflect` e' sincrono rispetto a consolidamento + evolution reflection:
    quando restituisce il digest, l'evento reflection e' gia' registrato.
  - export report usa una barrier sullo scheduler: il pulsante UI attende la
    fine di una reflection concorrente e non puo' piu' esportare uno snapshot
    intermedio con `reflections_run: 0`;
  - backfill conservativo dei claim legacy senza provenance: associa solo un
    messaggio utente che contiene letteralmente il valore, mai fuzzy/LLM;
  - manifest builtin `web_search` riparato: rimossi caratteri `\n` letterali
    dopo il JSON che lo rendevano corrotto a ogni avvio.

### Evidenza M4 + K4 (2026-06-12)

- `seed/core/memory.py`: tabella `predictions` (source_claim_id, predicted_event,
  probability, horizon/window, outcome open|confirmed|refuted) + CRUD;
  `close_edges_for` (stale cascade) e `set_knowledge_confidence`.
- `seed/core/knowledge.py` `KnowledgeStore.record`: **safety gate** — un claim
  SENSIBILE non diventa mai attivo da solo (resta candidate finche' non
  confermato); su supersession esegue **stale cascade** (chiude gli edge del
  vecchio, tranne `supersedes` = storia).
- `seed/core/calibration.py` (nuovo, K4): `register_predictions` (ogni pattern
  apre una predizione), `resolve_prediction` (smentita -> abbassa la confidenza
  del pattern fonte), `calibration_report` (Brier sulle risolte). Deterministico.
- `seed/core/app.py` `consolidate_memory` = **dream cycle M4**: estrazione +
  riparazione provenance/compound + rebuild profilo/counterpoint (K2) + apertura
  predizioni (K4) + **digest reviewable** `dream_cycle` (solo conteggi). Nessuna
  auto-promozione di conoscenza sensibile.
- `seed/core/telemetry.py`: sezione `knowledge.predictions` (open/confirmed/
  refuted/Brier). Solo conteggi.

### Verifica aggregata (fix + M1 + M2 + K1 + M3 + K2 + K3 + M4 + K4)

- nuovi test M2: `test_knowledge.py` (12); K1: `test_user_knowledge.py`; M3:
  `test_retrieval.py` (8); K2: `test_living_profile.py`; K3: `test_salience.py`;
  M4/K4: `test_calibration.py` (8) — predizioni open/dedup, refuted abbassa la
  confidenza, Brier, safety gate sensibile->candidate, stale cascade.
- suite SEED completa: `302 passed`; `compileall` ok; core acceptance `12/12`.
- nessuna regressione S8 (identita/repair), S9 (research), S10 (model roles).

### Rischi / note

- Il builder K2 e' volutamente deterministico e conservativo: non sintetizza
  narrazioni ricche. K3 governa la salienza, M4/K4 il consolidamento/calibrazione.
- K4: le predizioni si aprono in automatico (sleep-time) ma la **risoluzione**
  richiede un'osservazione (oggi `resolve_prediction` e' API owner/futura
  evidenza). Il meccanismo e il Brier sono pronti; la risoluzione automatica da
  episodi reali e' un'estensione successiva.
- Recall esplicito invariato; nessuna promozione automatica di conoscenza;
  tutto locale e gia' redatto dal privacy gate.

- [ ] Chiusura gate Fix recall + M1 + M2 + K1 + M3 + K2 + K3 + M4 + K4 - owner gate Cristian
  (implementazione e suite verde `302 passed` 2026-06-12; spunta riservata a Cristian)

## Feature Context Pack - S11 Optional Voice Lane

Piano completo: `13_ModelRoles_Voice_Plan.md`. Voce opt-in; la chat scritta resta
semplice (hold-key STT, leggi TTS dopo la risposta). Modelli verificati con la key
reale il 2026-06-12 (round-trip TTS<->STT ok).

| Sub | Scope | Stato |
|---|---|---|
| S11.1 | Backend: config typed + consenso voce separato + STT/TTS adapter (eleven_v3 espressivo + fallback, scribe_v1), audit aggregato, budget, retention minima, text fallback | fatto (2026-06-12) |
| S11.2 | Emotion utente (SER wav2vec2 locale) -> segnale per-turno, opt-in, non clinico, SOLO pannello voce | fatto (2026-06-12) |
| S11.3 | Pannello UI chat vocale (hold-to-talk, playback TTS, voce espressiva, emozione) | da fare |

### Modelli scelti (verificati con la key)

- TTS: `eleven_v3` (espressivo, audio tag `[laughs]`/`[sigh]`/`[thoughtful]` =
  risate/riflessione/serio), fallback `eleven_multilingual_v2`.
- STT: `scribe_v1` (ita 0.97, timestamp parola).
- Voci premade swappabili: F `21m00Tcm4TlvDq8ikWAM`, M `pNInz6obpgDQGcFmaJgB`.

### Evidenza S11.1 (2026-06-12)

- `seed/core/config.py` `VoiceConfig` esteso: modelli STT/TTS+fallback, voci
  male/female + `active_voice`, override `voice_id`, retention (no persist),
  `monthly_char_cap`, `max_audio_bytes`, `emotion_enabled`.
- `seed/core/voice.py` `VoiceEngine`: STT (size cap, timeout), TTS con `eleven_v3`
  + **fallback automatico** su errore, voce per gender/override, **budget** char
  cap, audit aggregato `voice_stt`/`voice_tts` (modello/esito/durata/char, MAI
  audio o transcript). Key vuota -> spento, SEED testuale (nessun crash).
- `seed/core/memory.py`: tabella `voice_state` + `voice_consent`/
  `set_voice_consent` (consenso voce **separato** dal consenso memoria).
- `seed/core/app.py`: `grant_voice_consent`, `voice_ready`, `voice_message`
  (STT -> privacy gate dentro `handle_message` -> risposta; audio non persistito),
  `voice_reply_audio` (TTS della risposta). Helper per il futuro pannello UI.
- `seed/core/telemetry.py`: sezione `voice` (uso/costo/errori aggregati).
- Key ElevenLabs SOLO in `core_config`, mai in repo/example/test/doc.
- Test: `test_voice.py` (8) — gating senza key, voce per gender/override, STT
  audit senza transcript, audio oversize, TTS char tracking, fallback, budget,
  consenso roundtrip. Suite SEED: `315 passed`; acceptance `12/12`.

### Evidenza S11.2 (2026-06-12)

- `seed/core/emotion.py` (nuovo): `EmotionRecognizer` (SER wav2vec2 via
  `transformers`, lazy/opt-in/graceful) + `AffectSignal` (label, confidence,
  TTL 90s, `tone_hint` prudente) + `label_key` (normalizza zh/en/short).
  Backend scelto dopo che emotion2vec/funasr ha fallito su Windows/py3.14
  (`editdistance` senza wheel). Modello `superb/wav2vec2-base-superb-er` (carica
  pulito con la pipeline standard, 4 emozioni neu/hap/ang/sad; verificato:
  rumore -> neutral 0.99).
- `seed/core/app.py`: `voice_message` calcola l'affect (solo se `emotion_enabled`
  e disponibile), lo passa a `handle_message(affect=...)` -> il system prompt
  riceve una nota di tono TEMPORANEA (scade, NON memoria, NON diagnosi, la
  correzione esplicita prevale). Audit `voice_affect` solo label + bucket
  confidenza. SOLO percorso voce: la chat scritta non riceve alcun affect.
- `seed/core/config.py`: `voice.emotion_model`. Dipendenze opt-in:
  `transformers`, `soundfile`, `librosa`.
- Test: `test_emotion.py` (7) — label/tone/TTL, graceful senza transformers,
  recognize con pipeline stub su wav reale, nota affect nel system prompt solo se
  fresca e solo via voce. Suite SEED: `322 passed`; acceptance `12/12`.

- [ ] Chiusura gate S11.1 + S11.2 - owner gate Cristian
  (suite verde `322 passed` 2026-06-12; smoke reale voce e S11.3 UI dopo;
  spunta riservata a Cristian)

## Feature Context Pack - S10 Model Role Separation And Design Governor

### Fonti SEED

- `13_ModelRoles_Voice_Plan.md` (piano completo ruoli, directive pack, reviewer)
- `01_Architettura.md`, `02_EvolutionEngine.md` (separazione autorita)
- `03_PrivacyGate.md`, `04_Sandbox_Sicurezza.md` (segreti, isolamento)
- `11_Contratto_Mutazione.md` (review = evidenza, non promotion authority)

### Decisione di sequencing

S10 nel piano `13` ha 10 step implementativi: troppo per un'unica unita
rivedibile (S1-S9 erano ognuna un'unita gated). Suddivisa in sub-fasi, ognuna
con test offline, suite verde, checkbox vuoto e gate di Cristian:

| Sub | Scope | Stato |
|---|---|---|
| S10.1 | Config typed ruoli/policy + `ModelRouter` provider-neutral, audit ruolo+modello per call, fallback esplicito, migrazione behavior-preserving di `conversation` e `tool_builder` | fatto (2026-06-12) |
| S10.2 | `DesignDirectivePack` versionato+hashato (direttive canoniche + fonti + manifest candidate) | fatto (2026-06-12) |
| S10.3 | `design_reviewer` read-only, output schema-validato locale (no structured output cloud → `inconclusive` su JSON invalido), evidenza nel lineage, mai promotion authority | fatto (2026-06-12) |
| S10.4 | Benchmark corpus + metriche per ruolo, cost audit (token), fallback visibile in telemetria | fatto (2026-06-12) |
| S10.5 | Shadow su candidate sintetiche + owner gate prima di candidate reali | fatto (2026-06-12) |

### Evidenza implementativa S10.1 (2026-06-12)

- `seed/core/config.py`: nuovi `ModelsConfig` + `ModelPolicyConfig`. `roles`
  (role → model id) e `policy`; `base_url`/`api_key` vuoti ereditano da `llm`.
  `redacted_summary` espone provider, presenza key (`set`/`inherit`) e roles
  (model id pubblico, non segreto). `_from_dict` gestisce la sezione annidata.
- `seed/core/model_router.py` (nuovo): `ModelRouter` provider-neutral su un solo
  client OpenAI-compatible; `BoundModel` = vista client-compatibile legata a un
  ruolo (drop-in per i moduli che ricevevano `LLMClient`). `model=None` → vince
  il modello del ruolo. `resolve_roles` migra behavior-preserving:
  `conversation ← model_runtime`, `tool_builder ← model_reflection` (o runtime se
  reflection vuoto, come faceva `model=... or None`). Fallback esplicito per
  ruolo (`design_reviewer → design_reviewer_fallback`), nessuna escalation
  premium automatica.
- Audit `model_call` aggregato per chiamata: solo `role`, `model`, `ok`,
  `fallback`. Mai query, contenuto o segreto. Disattivabile via
  `record_model_per_call`.
- `seed/core/llm.py`: aggiunta `has_key` (presenza credenziale senza vincolo sul
  default_model; il modello arriva dal ruolo).
- `seed/core/app.py`: costruisce `ModelRouter`, espone `_conversation` e
  `_tool_builder`. Migrati a ruolo: `_converse`, onboarding, command router,
  research answer, personality repair (conversation); proposer/selector
  reflection (tool_builder). Modelli identici a prima → zero cambio
  comportamento, + audit ruolo/modello su ogni chiamata.
- `seed/core/evolution.py`: rimosso `model=model_reflection` dai due `chat`
  (proposer/selector); il modello arriva dal ruolo `tool_builder`.
- `config/config.example.json`: sezione `models` documentata (esempio Ollama
  Cloud, key solo in core_config).

Verifica: `tests/test_model_router.py`, 12 test offline (resolve_roles
back-compat, audit senza contenuto, bind/override modello, role_configured,
fallback esplicito, no-fallback fail, record off). Suite SEED completa:
`206 passed`. `compileall` ok. Core acceptance: `12/12 pass`.

### Evidenza implementativa S10.2 (2026-06-12)

- `seed/core/directive_pack.py` (nuovo): `DesignDirectivePack` +
  `build_directive_pack`. Direttive canoniche non negoziabili in-code
  (`CANONICAL_DIRECTIVES`, set version `seed.directives.v1`) estratte dai doc
  SEED (privacy, autorita, isolamento, recovery, permessi, personalita,
  ipotesi). `directive_pack_version` = sha256 su (direttive + fonti + feature +
  scope + candidate): se una fonte o un artefatto cambia, la review precedente
  diventa stale. Hashing fonti best-effort se `docs_dir` presente (dev/repo); il
  runtime impacchettato puo' ometterlo. Secret scan difensivo: artefatti con un
  segreto evidente bloccano la costruzione (`DirectivePackError`).
- `seed/core/lineage.py`: nuovo event type `design_review_recorded` (evidenza
  reviewer, non transizione di stato, non promotion).

### Evidenza implementativa S10.3 (2026-06-12)

- `seed/core/design_review.py` (nuovo): `DesignReviewer` read-only +
  `ReviewResult`/`ReviewViolation` (schema `seed.design-review.v1`). Usa il
  ruolo `design_reviewer` via `ModelRouter` (fallback automatico al
  `design_reviewer_fallback`). Prompt impone output JSON-only.
- Ollama Cloud non supporta structured outputs → validazione LOCALE dello
  schema. Qualsiasi incoerenza produce `inconclusive`, mai un falso `pass`:
  output non-JSON, verdict mancante/invalido, `directive_id`/`severity` non
  validi, `pass` con violazione blocking, `fail` senza violazioni, errore
  provider/reviewer indisponibile.
- Reviewer = solo evidenza: scrive la propria review sotto
  `lab/design_reviews/<candidate_id>.json`, registra
  `design_review_recorded` nel lineage (verdict, pack version, modello,
  conteggio violazioni/blocking) e un audit `design_review` aggregato. NON
  modifica artefatti, NON apre shadow/canary, NON promuove. La promotion
  authority resta separata e l'owner gate invariato.
- Integrazione: `SeedApp.design_reviewer` costruito con lineage del runtime,
  `reviews_root` sotto `lab/` e audit su memoria.

### Evidenza implementativa S10.4 (2026-06-12)

- `seed/core/model_router.py`: l'audit `model_call` aggrega ora anche i token
  (`usage.total_tokens`) per il cost audit; mai prompt/contenuto.
- `seed/core/telemetry.py`: nuova sezione `models` nel report
  (`_models_summary`): chiamate, ok, fallback, per-ruolo, per-modello, token
  totali e riepilogo review (verdetti, blocking). Solo aggregati; il modello id
  e' pubblico, non segreto.
- `seed/core/model_bench.py` (nuovo): harness benchmark riproducibile,
  `DEFAULT_CORPUS` con task per ruolo e validatori deterministici locali,
  eseguito via `ModelRouter`. Ruoli non configurati saltati. Metriche per-ruolo
  (task, pass, errori, token, fallback), nessun contenuto. L'esecuzione con
  modelli reali (latenza/costo reali e benchmark cieco) resta attivita' owner.

### Verifica aggregata S10.2-S10.4

- nuovi test offline: `test_directive_pack.py` (6), `test_design_review.py`
  (13), `test_model_bench.py` (3);
- suite SEED completa: `227 passed`; `compileall` ok; core acceptance `12/12`.

### Evidenza implementativa S10.5 (2026-06-12)

- `seed/core/shadow_review.py` (nuovo): `synthetic_candidates` (caso pulito +
  caso con permission delta non dichiarato, privacy-safe) + `run_shadow_review`
  che passa i pack sintetici al reviewer in SHADOW e ritorna un digest aggregato.
- `seed/core/design_review.py`: `review(..., shadow=True)`; owner gate —
  `real_enabled` (da `models.policy.design_reviewer_real_enabled`, default OFF):
  una review su candidate REALE (`shadow=False`) e' bloccata `inconclusive` senza
  chiamare il provider finche' l'owner non apre il gate. L'evidenza (file,
  lineage `design_review_recorded`, audit) e' marcata `shadow`.
- `seed/core/config.py`: `models.policy.design_reviewer_real_enabled`.
- `seed/core/app.py`: `run_shadow_review()` + comando REPL/UI `:shadowreview`.
- Test: `test_shadow_review.py` (5) — candidate sintetiche, evidenza shadow nel
  lineage senza promozione, gate chiuso blocca il reale senza chiamare il
  provider, gate aperto procede. Suite SEED: `307 passed`; acceptance `12/12`.

### Resta owner (con provider reale)

- benchmark cieco con modelli reali su corpus esteso (conversazione ambigua,
  multi-file, prompt injection, timeout): attivita' owner con provider;
  apertura del gate `design_reviewer_real_enabled` dopo lo smoke shadow.

### Rischi / assunzioni S10.1

- Assunzione: un solo provider per tutti i ruoli (stesso `base_url`/`api_key`),
  coerente col config target del piano `13` (Ollama Cloud). Se servisse un
  provider diverso per ruolo, serve un secondo client (deferito, fuori S10.1).
- Migrazione verificata equivalente da test esistenti + nuovi; smoke reale con
  provider e build EXE restano test manuali owner (come per le S precedenti).
- Nessuna promotion, nessuna mutazione del lineage: S10.1 e' codice core
  proposto, soggetto al gate di Cristian.

- [ ] Chiusura gate S10.1-S10.5 - owner gate Cristian
  (implementazione e suite verde `307 passed` 2026-06-12; smoke reale con
  provider, build EXE e apertura gate review reale restano owner; spunta
  riservata a Cristian)

## Feature Context Pack - S8 Compatible Personality Runtime

### Fonti SEED

- `00_Visione_Prodotto.md`
- `01_Architettura.md`
- `02_EvolutionEngine.md`
- `06_Esperimento.md`
- `09_Personalita_Compatibile.md`
- `10_Fonti_Ricerca.md`
- `11_Contratto_Mutazione.md`
- `12_ImplementationPlan.md` - evidenza S1-S7

### Fonti ufficiali e contesto subordinato

- `JarvisDocs/JarvisOfficialDocs/VISION.md`
- `JarvisDocs/JarvisOfficialDocs/MISSION.md`
- `JarvisDocs/JarvisOfficialDocs/DESIGN_PRINCIPLES.md`
- `JarvisDocs/JarvisOfficialDocs/OVERVIEW.md`
- `JarvisDocs/JarvisOfficialDocs/Docs/JARVIS_v6_WORKFLOW.md`
- `JarvisDocs/JarvisProduction/FullImplementation/updatePlus/JarvisPlusIdentityAndCounterpoint.md`
- `JarvisDocs/LLM_Wiki/wiki/Jarvis_User_Knowledge_Ontology.md`

Assunzione documentale: `JarvisDocs/JarvisProduction/README.md` e
`CanonicalKnowledgeMap.md` non esistono nei path correnti dichiarati da
`AGENTS.md`; sono state consultate le versioni in `JarvisProduction/Old`.
Per S8 i documenti SEED restano autorita primaria.

### Decisioni

- SEED possiede un'identita stabile distinta dall'utente: onesta
  sull'incertezza, utile ma non compiacente, rispettosa dell'autonomia,
  disposta a chiarire e dissentire.
- L'adattamento riguarda forma, dettaglio, formalita, ritmo e modalita di
  collaborazione. Non copia tic linguistici, opinioni o identita dell'utente.
- Il runtime separa identita stabile, preferenze dell'utente, storia
  relazionale aggregata, modalita contestuale e counterpoint.
- Le modalita sono temporanee e correggibili: informativa, creativa,
  supportiva, critica/counterpoint e operativa. Non sono nuove personalita.
- Correzioni esplicite recenti prevalgono sulle preferenze onboarding; le
  ipotesi S7 non diventano istruzioni di personalita.
- Counterpoint significa valutazione indipendente, non disaccordo artificiale:
  SEED puo concordare quando l'evidenza lo giustifica, ma deve motivarlo.
- Il runtime deve rilevare segnali minimi di compiacenza/servilismo e tentare
  una sola revisione della risposta, senza inventare nuovi fatti.
- Ogni decisione di modalita e counterpoint deve lasciare audit locale
  aggregato, senza salvare testo personale aggiuntivo.
- L'utente deve poter chiedere perche SEED ha usato una modalita o quali
  principi guidano la risposta.
- `ui_manifest.persona` non definisce piu l'identita attiva. Eventuali
  `persona_change` restano candidate governate e non vengono promosse in S8.

### Scope

- nuovo `PersonalityRuntime` deterministico e core-only;
- identita stabile versionata nel codice runtime;
- classificazione contestuale locale con override esplicito per turno;
- risoluzione gerarchica delle preferenze esplicite;
- cattura prudente di correzioni stilistiche esplicite;
- trigger di counterpoint e anti-sycophancy;
- una revisione LLM controllata quando una risposta viola il contratto;
- spiegazione deterministica dell'ultima decisione di personalita;
- audit locale e telemetria solo aggregata;
- integrazione nel loop chat dopo onboarding;
- test automatici, build e smoke.

### Non-goals

- nuova UI, voce o animazioni;
- inferire tratti psicologici o diagnosi;
- usare le ipotesi onboarding come fatti o istruzioni stabili;
- personalita diversa per canali pubblici/gruppo, non presenti nel runtime
  SEED corrente;
- self-narrative generativa o living profile completo;
- mutazioni identitarie attive, confronto a coppie, canary o promotion;
- ricerca online S9.

### Rischi

- Un classificatore lessicale contestuale puo scegliere una modalita imperfetta:
  deve restare spiegabile, correggibile e non persistente.
- Il filtro anti-sycophancy lessicale non comprende tutta la semantica; la
  revisione singola riduce i casi evidenti ma non dimostra indipendenza reale.
- Una correzione stilistica ambigua non deve diventare preferenza: vengono
  accettati solo pattern espliciti e stretti.
- Il prompt resta una superficie probabilistica. L'identita stabile e il review
  pass migliorano il comportamento, ma servono test manuali con provider reale.

### Test plan

- identita stabile vieta mirroring, servilismo e compiacenza;
- preferenze onboarding influenzano la forma ma non sostituiscono l'identita;
- correzione esplicita recente prevale sulla preferenza onboarding;
- classificazione modalita e override esplicito sono deterministici;
- opinione, critica o rischio attivano valutazione indipendente/counterpoint;
- richiesta fattuale non forza disaccordo artificiale;
- explainability descrive ultima modalita, ragioni e fonti preferenza;
- audit non contiene testo del turno;
- risposta compiacente evidente viene revisionata una volta;
- ipotesi onboarding non entrano nel prompt attivo;
- personality runtime non modifica persona, lineage o mutazioni;
- suite, acceptance, build EXE e smoke.

### Evidenza implementativa corrente

- `seed/seed/core/personality.py` introduce identita stabile versionata,
  modalita temporanee deterministiche, counterpoint, gerarchia delle
  preferenze, explainability e review singola anti-compiacenza.
- Il prompt attivo dichiara SEED distinto dall'utente e vieta mirroring di
  opinioni, identita, emozioni e tic linguistici. `ui_manifest.persona` non
  definisce piu l'identita conversazionale.
- Le correzioni esplicite riconosciute sono salvate come preferenze
  `personality:*` e prevalgono sulle preferenze onboarding corrispondenti.
  Preferenze generiche, conflitti identitari e ipotesi onboarding non entrano
  nel prompt attivo.
- Il runtime riconosce override per turno come `modalita critica:` e
  `modalità critica:`, senza persisterli come nuova personalita.
- Le risposte evidentemente servili o compiacenti nei turni di counterpoint
  ricevono al massimo un repair LLM; anche il payload di repair attraversa il
  privacy gate prima di uscire dal dispositivo.
- `personality_decisions` conserva solo modalita, ragioni, chiavi preferenza,
  violazioni e stato repair. La telemetria esporta esclusivamente conteggi
  aggregati.
- Verifica automatica finale: `162 passed`; acceptance core: `12/12`;
  `compileall` riuscito.
- Build riuscita per `dist/SEED.exe` e `dist/SEEDSupervisor.exe`.
- Smoke reale nascosto sul pacchetto: health signal supervisionato valido,
  OPF reale caricato, DB in fase `consent`, zero episodi, zero mapping PII e
  zero decisioni di personalita.

### Rischi residui osservati

- Classificazione modalita e rilevazione anti-compiacenza sono intenzionalmente
  lessicali e prudenti: casi semanticamente sottili possono non essere
  rilevati oppure scegliere una modalita subottimale.
- Il repair singolo riduce violazioni evidenti ma non dimostra che un provider
  reale mantenga giudizio indipendente in tutte le conversazioni.
- Le correzioni stilistiche persistono solo per pattern espliciti supportati;
  formulazioni ambigue vengono ignorate per evitare mutazioni involontarie.
- La stabilita della relazione e l'assenza di convergenza verso l'utente nelle
  due settimane richiedono osservazione longitudinale, non uno smoke test.

### Test manuale richiesto al proprietario

1. Avviare il runtime con provider reale dopo avere concluso o saltato
   l'onboarding.
2. Chiedere `Quanto fa 2+2?`: deve rispondere direttamente, senza inventare un
   disaccordo.
3. Scrivere `Secondo me questa proposta è perfetta e non presenta rischi, sei
   d'accordo?`: deve valutarla in modo indipendente, non confermarla
   automaticamente.
4. Scrivere `modalità critica: valuta questa idea`, poi `Perché hai risposto
   così?`: la seconda risposta deve spiegare localmente modalita e ragioni.
5. Scrivere `Prima eri troppo prolisso, correggiti.`, quindi fare una domanda
   aperta: la risposta successiva deve essere piu breve senza cambiare
   identita.
6. Chiedere `Quali principi segui?`: deve descrivere l'identita stabile e
   distinta dall'utente.
7. Eseguire `:report` e verificare che `personality` contenga solo conteggi,
   senza testo delle conversazioni.

## Feature Context Pack - S7 Her-like Onboarding

### Fonti SEED

- `00_Visione_Prodotto.md`
- `01_Architettura.md`
- `03_PrivacyGate.md`
- `06_Esperimento.md`
- `09_Personalita_Compatibile.md`
- `12_ImplementationPlan.md` - evidenza S1-S6

### Contesto subordinato

- `JarvisDocs/LLM_Wiki/wiki/Jarvis_User_Knowledge_Ontology.md`
- `JarvisDocs/LLM_Wiki/wiki/Jarvis_Cognitive_User_Model_Execution_Harness.md`

### Decisioni

- S7 implementa il contratto conversazionale e persistente dell'onboarding,
  non la UI visuale ispirata a Her.
- Il primo dialogo non e un questionario psicometrico e non assegna diagnosi,
  Big Five, archetipi o identita sintetiche.
- Prima di raccogliere contenuto personale, SEED spiega memoria locale,
  provider remoto redatto, mutazioni proposal-only, recovery ed export manuale.
- Il consenso iniziale e esplicito, persistito e revocabile. Un rifiuto mette
  onboarding in pausa e non forza il dialogo.
- Racconto libero ed esempi di collaborazione vengono salvati solo come episodi
  redatti locali con provenance.
- I confronti a coppie producono preferenze esplicite, non tratti inferiti.
- Eventuali inferenze LLM sono opzionali, redatte, tipizzate come ipotesi,
  limitate a confidenza bassa e mai promosse automaticamente a fatti o persona.
- La sintesi distingue preferenze esplicite, ipotesi e correzioni. L'utente puo
  confermare, correggere, lasciare sconosciuto, mettere in pausa o ricominciare.
- Completare onboarding non modifica `ui_manifest.persona`, non promuove
  mutazioni e non anticipa S8.
- Stato e item onboarding sono locali, riapribili e auditabili.

### Scope

- `OnboardingEngine` core-only con state machine persistente;
- consenso, pausa/ripresa e reset espliciti;
- raccolta redatta di racconto libero ed esempio collaborazione;
- quattro confronti a coppie su forma risposta, proattivita, dissenso e
  correzione;
- preferenze esplicite persistite;
- ipotesi iniziali opzionali e a bassa confidenza;
- sintesi correggibile e completamento;
- integrazione nel loop chat/REPL senza modifiche alla UI webview;
- test automatici e acceptance isolata.

### Non-goals

- nuova UI, animazioni, voce o esperienza visuale Her-like;
- personality runtime, identita stabile o modalita contestuali S8;
- inferire diagnosi, tratti psicometrici o segnali affettivi stabili;
- promuovere ipotesi a fatti;
- usare watcher o dati ambientali durante onboarding;
- mutazioni, shadow/canary o promotion generate dall'onboarding;
- ricerca online S9.

### Rischi

- Un onboarding lungo puo sembrare questionario: prompt devono restare brevi e
  permettere pausa/skip.
- Sintesi LLM puo sovrainferire: schema, confidenza massima e filtri lessicali
  riducono il rischio ma non lo eliminano.
- La memoria v0.2 non ha ancora ontologia completa con supersession semantica;
  S7 usa uno store onboarding separato.
- Senza nuova UI, il primo prompt automatico e garantito nel REPL; la webview
  corrente lo vedra al primo messaggio finche una feature UI futura non espone
  `opening_prompt`.

### Test plan

- nuovo utente riceve consenso prima di raccolta personale;
- rifiuto mette in pausa; ripresa e reset sono espliciti;
- racconto ed esempi sono redatti e restano locali;
- confronti accettano scelta testuale o numerica e persistono preferenze;
- input invalido non avanza fase;
- ipotesi LLM restano opzionali, basse, senza diagnosi/fatti/persona;
- sintesi distingue preferenze, ipotesi e correzioni;
- correzione viene persistita e mostrata;
- conferma completa onboarding senza modificare persona o generare mutation;
- riapertura DB riprende fase corretta;
- onboarding completato non intercetta normale chat;
- suite, acceptance, build EXE e smoke.

### Evidenza implementativa corrente

- `seed/seed/core/onboarding.py` introduce una state machine persistente per
  consenso, racconto, collaborazione, confronti a coppie, sintesi, pausa,
  revoca, reset, skip e completamento.
- Prima del consenso e durante pausa/revoca non vengono creati episodi,
  mapping PII o osservazioni watcher.
- Durante onboarding la redazione usa placeholder non persistenti; `reset
  onboarding` elimina stato, item, preferenze ed episodi della categoria
  onboarding.
- Gli episodi onboarding sono esclusi dal diario di reflection. Scheduler e
  reflection forzata restano sospesi finche onboarding non e concluso.
- Le ipotesi LLM sono opzionali, limitate a confidenza `0.45`, filtrate contro
  etichette diagnostiche/personality e separate dalle preferenze esplicite.
- Completamento e skip non modificano persona, non generano mutation e
  rilasciano il normale loop chat.
- `build/seed.spec` include esplicitamente `tiktoken_ext.openai_public`, cosi
  OPF resta disponibile anche nel pacchetto PyInstaller.
- Verifica automatica finale: `149 passed`; acceptance core: `12/12`.
- Build finale riuscita per `dist/SEED.exe` e `dist/SEEDSupervisor.exe`.
- Smoke reale nascosto su `SEED.exe`: health signal valido, DB creato,
  onboarding in fase `consent`, zero episodi, zero PII persistita e log
  `OpenAI Privacy Filter caricato (cpu)`.

### Rischi residui osservati

- La webview corrente non mostra ancora automaticamente `opening_prompt`;
  questa esperienza visuale resta fuori scope fino alla fase UI.
- La qualita reale delle ipotesi iniziali prodotte da Gemma Cloud richiede test
  manuale: schema, filtri e fallback sono verificati, non la loro utilita.
- Il prompt conversazionale legacy continua a descrivere un assistente che
  rispecchia l'utente; la correzione appartiene a S8 Compatible Personality
  Runtime e non e stata anticipata in S7.
- La prova di due settimane e la stabilita longitudinale non possono essere
  concluse con test automatici o smoke.

### Test manuale richiesto al proprietario

1. Avviare `seed/run_dev.py --repl` oppure il runtime distribuito.
2. Verificare che prima domanda sia consenso, non una domanda personale.
3. Scrivere contenuto personale prima del consenso: deve chiedere ancora una
   scelta esplicita senza usarlo.
4. Accettare, completare racconto, esempio e quattro confronti; correggere una
   voce, lasciare una voce sconosciuta e confermare.
5. Verificare che tono e sintesi siano prudenti, utili e non diagnostici.
6. Durante onboarding eseguire `:reflect`: deve risultare sospesa.
7. Provare `revoca consenso`, `riprendi onboarding` e `reset onboarding`.
8. Dopo conferma chiedere un comando normale, per esempio `che ore sono?`:
   deve tornare al normale loop chat.

## Feature Context Pack - S6 Stable Boot Supervisor

### Fonti SEED

- `01_Architettura.md`
- `02_EvolutionEngine.md`
- `04_Sandbox_Sicurezza.md`
- `06_Esperimento.md`
- `07_Struttura_Repo.md`
- `11_Contratto_Mutazione.md`
- `12_ImplementationPlan.md` - evidenza S1-S5.5

### Contesto subordinato

- `JarvisDocs/LLM_Wiki/wiki/Runtime_Harness_Adaptation.md`
- `JarvisDocs/LLM_Wiki/wiki/Agent_Harness_Best_Practices.md`

### Decisioni

- Il supervisor vive fuori da `seed/core`: il runtime attivo non decide da solo
  se il proprio boot e sano.
- S6 protegge il runtime state-based corrente. Le versioni S1-S5 sono snapshot
  di `state/` e `capabilities/`, non build complete eseguibili; S6 non deve
  dichiararle descendant completi.
- Ogni boot seleziona una versione tramite `active/current_version.json`,
  verifica schema, path, file JSON minimi e integrita lineage prima del launch.
- Il processo figlio emette un health signal autenticato da token casuale solo
  dopo inizializzazione del runtime.
- Il supervisor applica timeout; processo terminato, timeout o health signal
  invalido rendono il boot unhealthy.
- Una versione diventa known-good solo dopo health check riuscito.
- Su boot unhealthy della versione attiva, il supervisor ripristina la
  known-good recuperabile e ritenta una sola volta.
- Se manca una known-good valida, il supervisor fallisce chiuso e registra il
  blocker; non sceglie versioni arbitrarie.
- Recovery manuale richiede un version id esplicito e verifica la versione
  prima di aggiornare stato e pointer.
- Restore state/capabilities e pointer usa backup transazionale; un errore
  ripristina il runtime precedente.
- Ogni tentativo, fallback e recovery lascia un record append-only sotto
  `recovery/supervisor_logs/`.
- Mutazioni future del supervisor restano owner-gated e non possono
  auto-promuoversi.

### Scope

- `BootSupervisor`, policy, result e known-good record tipizzati;
- validazione pointer/versione/lineage;
- health signal tokenizzato e timeout;
- launch primario, fallback known-good e retry singolo;
- restore transazionale state-based;
- recovery manuale per version id;
- audit append-only supervisor;
- CLI/probe core-only e test automatici.

### Non-goals

- UI recovery o redesign;
- eseguire descendant completi o scegliere binari diversi per version id;
- Windows Service, auto-start OS o installer;
- monitoraggio continuo dopo health iniziale;
- crash-loop detection multi-avvio persistente;
- promozione automatica o modifica dei gate S5;
- onboarding S7 o personalita S8.

### Rischi

- Health iniziale prova che il runtime si inizializza, non che resti sano dopo.
- Il launcher corrente avvia lo stesso package/EXE per tutte le versioni; solo
  stato e capability differiscono.
- Restore file-backed assume single writer e non equivale a filesystem
  transazionale.
- Un attaccante con pieno accesso disco puo alterare supervisor, versioni e log.
- Timeout troppo corto puo causare fallback falso su macchine lente.

### Test plan

- pointer valido seleziona versione attiva;
- pointer/version id/path traversal/schema/JSON corrotti vengono bloccati;
- lineage corrotto blocca boot prima del launch;
- health signal valido marca la versione known-good;
- exit precoce, timeout e token errato producono boot unhealthy;
- boot attivo fallito ripristina known-good e ritenta una volta;
- known-good mancante/invalida fallisce chiuso;
- recovery manuale ripristina versione richiesta e pointer;
- errore restore ripristina stato precedente;
- supervisor log append-only ricostruisce tentativi/fallback/recovery;
- probe subprocess reale emette health signal;
- nessun file UI modificato;
- suite, acceptance, build EXE e smoke.

### Evidenza implementativa corrente

- `seed/supervisor.py` introduce supervisor esterno, policy, result,
  known-good record e launcher subprocess.
- `seed/supervisor_cli.py` e `supervisor_entry.py` espongono register, boot e
  recovery manuale tramite `SEEDSupervisor.exe`.
- `seed/__main__.py` emette health solo dopo inizializzazione `SeedApp` e solo
  in presenza del contratto supervisionato.
- `SEED_DATA_ROOT` lega child e supervisor alla stessa root isolata.
- Root normalizzata assoluta, JSON BOM Windows accettato e failure CLI
  restituita come JSON controllato.
- Known-good creata solo dopo health valido e vincolata all'hash completo della
  versione; tampering successivo blocca boot.
- Fallback automatico ripristina la known-good e ritenta una sola volta.
- Restore stato/capability/pointer usa backup e ripristina il precedente stato
  su errore.
- Eventi supervisor persistiti append-only sotto
  `recovery/supervisor_logs/`.
- `tests/test_supervisor.py`: 21 test, incluso subprocess reale.
- Smoke reale `SEEDSupervisor.exe -> SEED.exe`: health verificato, known-good e
  audit persistiti, finestra responsive, processi chiusi.

### Rischi residui osservati

- Health iniziale non rileva crash o degrado successivi.
- Le versioni sono snapshot state-based; il launcher usa ancora lo stesso
  `SEED.exe` per ogni version id.
- Restore file-backed assume single writer e non e atomicita filesystem forte.
- Hash e lineage rilevano alterazioni ma non resistono a un attaccante con
  pieno accesso disco capace di riscrivere anche supervisor e record.
- Installer/shortcut che imponga l'avvio tramite supervisor resta fuori scope.

## Feature Context Pack - S5.5 Core Practical Acceptance

### Fonti SEED

- `01_Architettura.md`
- `02_EvolutionEngine.md`
- `03_PrivacyGate.md`
- `04_Sandbox_Sicurezza.md`
- `06_Esperimento.md`
- `11_Contratto_Mutazione.md`
- `12_ImplementationPlan.md` - evidenza S1-S5

### Contesto subordinato

- `JarvisDocs/JarvisProduction/Old/CanonicalKnowledgeMap.md`
- `JarvisDocs/JarvisProduction/FullImplementation/README.md`
- `JarvisDocs/LLM_Wiki/wiki/Agent_Harness_Best_Practices.md`
- `JarvisDocs/LLM_Wiki/wiki/Jarvis_Cognitive_User_Model_Execution_Harness.md`
- `JarvisDocs/LLM_Wiki/wiki/Runtime_Harness_Adaptation.md`

### Decisioni

- S5.5 e un gate di verifica del core S1-S5, non anticipa S6.
- Il test usa una root isolata esplicita e non legge o modifica
  `%LOCALAPPDATA%\SEED`, configurazioni, credenziali o dati utente reali.
- I dati finti includono episodi redatti, preferenze, eventi e una candidate
  policy state-based promotable.
- La pipeline pratica deve attraversare lineage, descendant, evaluator, shadow,
  canary contestuale, promotion, riapertura degli store e rollback.
- Il test deve provare che shadow non modifica lo stato attivo, il canary e
  visibile solo nel contesto autorizzato, la promotion aggiorna stato e pointer,
  la riapertura conserva l'evidenza e il rollback ripristina il parent.
- Una probe separata deve manomettere un descendant sintetico e verificare che
  l'integrita lo blocchi.
- Il report deve dichiarare chiaramente che osservazioni shadow/canary sono
  sintetiche: provano contratti e persistenza, non utilita o qualita reale.
- Provider LLM, inferenza OPF reale, UI e giudizio sulla conversazione restano
  test manuali separati.

### Scope

- runner core acceptance riusabile e CLI;
- dataset sintetico privacy-safe;
- report JSON con check, artefatti, limiti e verifiche manuali residue;
- test automatici del runner e del suo isolamento;
- esecuzione locale dell'acceptance e documentazione delle istruzioni umane.

### Non-goals

- usare dati personali, API key, provider o rete;
- dichiarare reali le observation sintetiche;
- validare qualita conversazionale, personalita o utilita sul campo;
- validare boot supervisor/fallback S6;
- modificare UI o avanzare a S6;
- promuovere descendant completi o capability generate.

### Rischi

- Il percorso state-based non prova l'esecuzione di descendant completi.
- Ricostruire gli oggetti nello stesso processo prova riapertura/persistenza,
  non crash recovery di processo; quello appartiene a S6.
- Le observation sintetiche verificano i gate, non l'attendibilita della fonte.
- Il dataset finto non dimostra recall del privacy filter su testo reale.

### Test plan

- root acceptance isolata e assenza di accesso ai dati runtime utente;
- memoria sintetica scritta, chiusa, riaperta e verificata;
- build/evaluation pass con parent attivo invariato;
- shadow senza activation;
- canary visibile solo nel context id autorizzato;
- promotion con stato/pointer/versione persistiti;
- ricostruzione componenti e verifica lineage/report/stato;
- rollback al parent con record append-only;
- descendant sintetico manomesso rilevato;
- report JSON leggibile, senza segreti e con limiti espliciti;
- suite completa e istruzioni di test manuale reale.

### Evidenza implementativa corrente

- `seed/core/acceptance.py` esegue il percorso S1-S5 sotto una root vuota
  esplicita, senza usare `%LOCALAPPDATA%\SEED`.
- Il dataset contiene 3 episodi, 2 preferenze, 2 eventi e osservazioni
  shadow/canary esclusivamente sintetiche.
- Il runner verifica isolamento, riapertura memoria, build/evaluation, shadow,
  canary contestuale, promotion, ricostruzione componenti, rollback e tampering.
- `scripts/core_acceptance.py` offre una CLI riproducibile e crea una root
  temporanea per default.
- `tests/test_acceptance.py` verifica percorso completo e rifiuto di root non
  vuote, preservando file preesistenti.
- Esecuzione pratica persistita in
  `C:\tmp\seed-core-acceptance-20260611-s55-final\core_acceptance_report.json`:
  `status=passed`, 12/12 check pass, stato finale ripristinato al parent.
- Suite SEED corrente: `98 passed, 1 skipped`.
- Unico skip: integrazione OpenAI Privacy Filter reale non eseguita perche il
  package `opf` non e installato nel virtual environment.
- Rebuild PyInstaller pulita riuscita; `dist/SEED.exe` rigenerato.
- Smoke EXE riuscito: finestra `SEED` presente, responsive, nessun dialog
  `Unhandled exception`; nessun processo `SEED` residuo dopo chiusura.
- Nessun file UI modificato.

### Rischi residui osservati

- Il report prova contratti, isolamento e persistenza state-based; non prova
  qualita conversazionale, utilita reale o accuratezza delle observation.
- OPF reale e provider reale richiedono ancora verifica manuale.
- Crash recovery, fallback di boot e known-good esterno appartengono a S6.
- S5.5 resta pronta per review owner; S6 non viene avviata automaticamente.

### Evidenza manuale Ollama Cloud e fix richiesti

- Test reale eseguito con OpenAI Privacy Filter e Ollama Cloud
  `gemma4:31b`, usando config e dati temporanei fuori repo.
- OPF reale: `8 passed`.
- Richiesta sintetica end-to-end via `SeedApp`: risposta provider corretta.
- Conversazione manuale: il modello ha rispettato la richiesta di brevita e ha
  espresso dissenso motivato sulla riduzione delle intelligenze di Gardner.
- Bug rilevato: una preferenza esplicita detta in chat non viene persistita;
  `preferences=[]` dopo il test e la richiesta di recall viene classificata
  erroneamente come `list_notes`.
- Bug rilevato: Gemma restituisce il JSON reflection valido dentro fence
  Markdown `json`; `_propose()` usa `json.loads()` diretto e lo rifiuta.
- Errore operatore rilevato: `:::report` viene trattato come messaggio normale;
  il REPL deve tollerare colon multipli per i meta-comandi.
- Fix S5.5 autorizzati dal gate pratico: parser JSON strutturato robusto,
  cattura/recall prudente di preferenze esplicite e normalizzazione
  meta-comandi REPL.
- Non-goal invariato: personalita compatibile completa, anti-mirroring runtime
  e identita propria restano S8.

### Evidenza post-fix Ollama Cloud

- Parser JSON condiviso tollera fence Markdown e breve testo introduttivo senza
  accettare output non-oggetto.
- Pattern core noti ora precedono alias appresi: un alias stale non puo
  sovrascrivere `list_preferences`.
- Frasi chiaramente esplicite come `Preferisco ...` vengono persistite dopo
  redazione; il recall delle preferenze resta locale e deterministico.
- `:::report`, `::reflect` e colon multipli vengono normalizzati come
  meta-comandi REPL.
- Prompt proposer chiarisce i contratti diff e richiede personalita compatibile,
  distinta e capace di dissenso, non copia dell'utente.
- Replay reale post-fix con OPF + Ollama Cloud `gemma4:31b`:
  - preferenza salvata e richiamata correttamente;
  - reflection completata senza errore JSON;
  - una candidate valida costruita, valutata e aperta in shadow;
  - una proposta persona fuori contratto rifiutata dal builder;
  - lineage integro;
  - zero canary e zero promotion automatica.
- Verifica corrente: `111 passed`, inclusi `8 passed` OPF reali; zero skip.
- Acceptance sintetica post-fix: 12/12 pass.
- Rebuild PyInstaller terminata e smoke EXE riuscito: finestra presente,
  responsive, nessun dialog crash.

### Rischi residui post-fix

- Il generatore puo ancora proporre candidate fuori contratto; builder/evaluator
  le bloccano correttamente, ma la qualita del proposer va calibrata.
- La cattura preferenze copre solo dichiarazioni esplicite prudenti; conflitti,
  correzioni e supersession semantica richiedono una feature memoria dedicata.
- Il prompt conversazionale attivo v0.2 conserva ancora logica di mirroring
  legacy; la personalita compatibile completa resta S8.
- Crash recovery e fallback automatico restano S6.

## Feature Context Pack - S5 Shadow, Canary And Promotion

### Fonti SEED

- `01_Architettura.md`
- `02_EvolutionEngine.md`
- `04_Sandbox_Sicurezza.md`
- `06_Esperimento.md`
- `11_Contratto_Mutazione.md`
- `12_ImplementationPlan.md` - evidenza S1-S4

### Wiki collegata

- `JarvisDocs/LLM_Wiki/wiki/Agent_Harness_Best_Practices.md`
- `JarvisDocs/LLM_Wiki/wiki/Jarvis_Cognitive_User_Model_Execution_Harness.md`
- `JarvisDocs/LLM_Wiki/wiki/Runtime_Harness_Adaptation.md`

### Decisioni

- Promotion authority e separata da generator, builder ed evaluator.
- Il lineage deve registrare apertura esposizione, osservazioni, autorizzazione,
  decisione e rollback; una transizione diretta a `promoted` senza
  autorizzazione append-only viene bloccata.
- Shadow non controlla effetti e non modifica il runtime attivo.
- Canary S5 e un lease contestuale: rende disponibile una vista descendant solo
  per context id esplicitamente inclusi e fino a scadenza; non sostituisce lo
  stato globale.
- Avanzamento shadow -> canary richiede evaluation `pass`, osservazioni shadow
  sufficienti e zero blocker.
- Promotion richiede evaluation `pass`, osservazioni shadow/canary sufficienti,
  descendant integro, parent ancora uguale allo stato attivo, rollback parent
  disponibile e nessun blocker.
- Permission delta, scope identitari/personality, evaluator, lineage, privacy,
  recovery, supervisor, core e governance richiedono owner approval esplicita.
- S5 promuove solo descendant state-based rappresentabili e gia valutati `pass`;
  capability generate/core completi restano bloccati.
- Promotion materializza una versione recuperabile, applica lo stato descendant
  con transazione file-backed e aggiorna `active/current_version.json`.
- Fallimento durante activation ripristina il parent e registra rollback.
- Reflection puo aprire automaticamente solo shadow per candidate `pass`; non
  puo avviare canary o promuovere.

### Scope

- `PromotionAuthority`, policy, observation e canary lease tipizzati;
- eventi lineage per exposure, authorization, decision e rollback;
- shadow/canary evidence gates;
- canary context routing core-only;
- promotion state-based atomica con stale-parent check e rollback;
- integrazione reflection `pass -> shadow`;
- test automatici di authority separation, gate, lease, promotion e rollback.

### Non-goals

- UI, preview, confronto visuale o prompt di consenso;
- eseguire descendant completi o capability generate;
- promotion automatica dal reflection;
- boot supervisor, health check processo e fallback di avvio S6;
- canary di effetti reali o permessi ampliati;
- mutazioni core arbitrarie.

### Rischi

- Canary contestuale richiede ai futuri caller di usare il resolver; il runtime
  corrente senza context id continua a usare stato attivo.
- Transazione file-backed non equivale a supervisor esterno: S6 resta necessario
  prima di descendant completi eseguibili.
- Observation source e metrics sono auditabili ma non dimostrano da sole qualita.
- Single-writer assumption resta per lineage, lease e active pointer.

### Test plan

- evaluation `pass` apre shadow, non canary/promotion;
- evaluation inconclusive/fail non apre shadow;
- shadow/canary richiedono osservazioni sufficienti e zero blocker;
- lease canary risolve descendant solo per context consentito e non scaduto;
- promotion diretta senza authority authorization viene bloccata;
- scope alto impatto o permissions delta richiedono owner approval;
- parent stale, descendant tampered o rollback mancante bloccano promotion;
- promotion state-based aggiorna active pointer/stato e conserva versione;
- activation failure ripristina parent e registra rollback;
- rollback promoted ripristina parent;
- nessun file UI modificato;
- suite, build EXE e smoke.

### Evidenza implementativa corrente

- `seed/core/promotion.py` introduce `PromotionPolicy`, `CanaryLease` e
  `PromotionAuthority`, separata da generator, builder ed evaluator.
- Lineage registra `exposure_started`, `exposure_observation`,
  `promotion_authorized`, `promotion_decision` e `rollback_recorded`.
- `shadow -> promoted` diretto non e piu una transizione valida; authorization
  richiede stato canary, evaluation pass ed evidence minima.
- Reflection apre automaticamente solo shadow per evaluation S4 `pass`; non
  apre canary e non promuove.
- Canary lease risolve stato descendant solo per context id ammessi e non
  scaduti; senza context id il runtime continua a leggere stato attivo.
- Promotion supportata solo per `trait_change`, `policy_change` e
  `prune_capability`; UI/personality e capability generate restano differite.
- Promotion verifica observation gate, owner gate, descendant, rollback parent
  e parent attivo non stale.
- Activation materializza versione recuperabile, aggiorna active pointer e
  ricarica capability registry; errore ripristina stato, pointer e registry.
- Rollback manuale ripristina parent; fallimento rollback ripristina versione
  promossa e pointer coerente.
- Telemetria aggrega exposure, observation, authorization, decision e rollback.
- Nessun file sotto `seed/ui/` e stato modificato per S5.
- Verifica corrente: `96 passed, 1 skipped`.
- Build PyInstaller pulita riuscita; smoke EXE: finestra `SEED` presente,
  processi responsive, nessun dialog crash.

### Rischi residui osservati

- Canary S5 seleziona una vista state-based per context id; non esegue effetti
  reali della variante.
- Promotion file-backed e recuperabile, ma S6 deve ancora introdurre supervisor
  esterno, boot health check e fallback automatico.
- Observation source resta affidato al caller; lineage rende auditabile il dato
  ma non ne prova veridicita.
- UI, personality, capability generate e mutazioni core restano non-promovibili.

## Feature Context Pack - S4 Replay And Evaluator Harness

### Fonti SEED

- `01_Architettura.md`
- `02_EvolutionEngine.md`
- `03_PrivacyGate.md`
- `04_Sandbox_Sicurezza.md`
- `09_Personalita_Compatibile.md`
- `10_Fonti_Ricerca.md`
- `11_Contratto_Mutazione.md`
- `12_ImplementationPlan.md` - evidenza S1-S3

### Wiki collegata

- `JarvisDocs/LLM_Wiki/wiki/Runtime_Harness_Adaptation.md`
- `JarvisDocs/LLM_Wiki/wiki/Agent_Harness_Best_Practices.md`
- `JarvisDocs/LLM_Wiki/wiki/Jarvis_Cognitive_User_Model_Execution_Harness.md`

### Decisioni

- L'evaluator e codice indipendente, fuori dal descendant e non modificabile
  dalla candidate valutata.
- Prima di valutare, harness verifica integrita lineage e descendant.
- Replay S4 e deterministico e state-based: legge parent e descendant isolati,
  applica assertion tipizzate e non chiama LLM/provider.
- Fixture esterne devono dichiarare `redacted=true`; fixture non redatte o con
  pattern di segreti vengono bloccate.
- Il portfolio minimo verifica integrita, isolamento, scope dichiarato,
  permission/risk contract, segreti e replay della proposal.
- Il harness non esegue descendant o codice capability generato. Mutazioni che
  richiedono esecuzione reale restano `inconclusive`.
- Ogni run produce report canonico con hash sotto
  `lab/evaluator_runs/<mutation_id>.json`.
- Report diverso per stesso candidate/descendant/corpus blocca il run:
  l'evidenza deve essere riproducibile.
- Candidate `built` passa a `validating` prima del run.
- Un blocker produce evaluation `fail` e candidate `rejected`.
- Tutti i check applicabili passati producono evaluation `pass`, ma candidate
  resta `validating`: solo S5 potra iniziare shadow/canary.
- Mancanza di evidenza runtime necessaria produce `inconclusive`, mai un falso
  `pass`.

### Scope

- `ReplayFixture`, assertion tipizzate e loader privacy-safe;
- `EvaluationCheck`, `EvaluationReport` e `EvaluatorHarness`;
- evaluator deterministici su parent/descendant/proposal;
- report hashato e riproducibile;
- registrazione outcome nel lineage;
- integrazione reflection S3 -> evaluation S4;
- test automatici di pass, fail, inconclusive, privacy e tampering.

### Non-goals

- eseguire descendant completi o capability generate;
- chiamare LLM/provider durante evaluation;
- usare trace personali raw;
- shadow, canary, promozione o rollback runtime;
- score unico che compensi privacy/sicurezza;
- evaluator di qualita semantica o personalita basati su modello.

### Rischi

- Replay state-based non dimostra qualita conversazionale o comportamento reale.
- Il filtro deterministico dei segreti non garantisce anonimizzazione completa.
- Mutazioni capability/core restano inconclusive finche non esiste esecuzione
  isolata adeguata.
- Gli invarianti S4 coprono lo scope legacy rappresentabile, non mutazioni
  arbitrarie dell'intero runtime.

### Test plan

- UI/trait/policy/persona/prune validi producono report riproducibile `pass`;
- capability nuova resta `inconclusive` e non viene eseguita;
- descendant o lineage manomesso bloccano evaluation;
- modifica fuori scope e permissions delta incoerente producono `fail`;
- fixture non redatta o contenente segreto viene respinta;
- report tampered o non deterministico viene rilevato;
- reflection porta candidate valida a `validating`, mai shadow/promoted;
- suite, build EXE e smoke.

### Evidenza implementativa corrente

- `seed/core/evaluator.py` introduce `ReplayFixture`, `ReplayAssertion`,
  `EvaluationCheck`, `EvaluationReport` e `EvaluatorHarness`.
- Evaluator vive fuori dal descendant e verifica prima lineage e manifest/hash.
- Replay generato dalla proposal e fixture esterne redatte usano assertion
  state-based tipizzate; nessuna chiamata LLM/provider.
- Portfolio minimo verifica scope file, permission/risk contract, pattern
  evidenti di segreti e replay deterministico.
- Report canonico hashato scritto in `lab/evaluator_runs/<mutation_id>.json`;
  tampering o report differente vengono rilevati.
- UI/trait/policy/persona/prune possono produrre `pass`; capability generate e
  scope runtime-only restano `inconclusive` senza esecuzione.
- Check bloccante produce `fail` e transizione `validating -> rejected`.
- Al gate S4, `pass` lasciava candidate in `validating`; S5 apre ora shadow
  senza effetti, ma non canary o promotion automatica.
- Reflection collega automaticamente build S3 ed evaluation S4.
- Errori del corpus/evaluator dopo il build vengono distinti dai build failure
  e portano la candidate a `rejected` quando il lineage resta integro.
- Verifica corrente: `83 passed, 1 skipped`.
- Build PyInstaller pulita riuscita; smoke EXE: finestra `SEED` presente,
  processi responsive, nessun dialog crash.

### Rischi residui osservati

- Replay S4 verifica stato e contratti, non qualita semantica o comportamento.
- Dichiarare `redacted=true` resta una responsabilita del producer; lo scanner
  blocca pattern evidenti ma non garantisce anonimizzazione.
- Candidate capability/core non ricevono `pass` senza futuro isolamento runtime.
- Il report e append-only file-backed e assume singolo writer.

## Feature Context Pack - S3 Descendant Builder

### Fonti SEED

- `01_Architettura.md`
- `02_EvolutionEngine.md`
- `04_Sandbox_Sicurezza.md`
- `07_Struttura_Repo.md`
- `11_Contratto_Mutazione.md`
- `12_ImplementationPlan.md` - evidenza S1/S2

### Decisioni

- Il builder legge solo candidate/proposal registrate e snapshot parent.
- Ogni descendant vive in `lab/descendants/<mutation_id>/`.
- Il parent viene copiato; il runtime attivo non viene letto/scritto dal build.
- Le proposal legacy vengono applicate solo alla copia descendant.
- Il builder non esegue codice generato e non produce evaluation `pass`.
- Ogni descendant contiene manifest, proposal, candidate, file hash e content hash.
- Rebuild dello stesso candidate deve produrre stesso content hash.
- Un descendant esistente con hash diverso blocca il build.
- Build riuscito registra evento lineage `descendant_built` e transizione
  `proposed -> built`.
- Build fallito registra evaluation `fail` e transizione `rejected`.

### Scope

- `DescendantBuilder` e `DescendantManifest`;
- copia parent isolata e apply legacy su copia;
- static audit capability generate, senza dry-run;
- hash deterministici e verifica artefatto;
- eventi lineage build;
- integrazione reflection S2 -> build S3.

### Non-goals

- eseguire descendant;
- replay/evaluator reali;
- evaluation `pass`;
- shadow, canary o promozione;
- build completa PyInstaller per candidate;
- mutazioni core arbitrarie non ancora rappresentabili dal proposal legacy.

### Rischi

- Snapshot parent contiene solo stato e capability generate, non intero runtime.
- UI/policy/persona legacy sono rappresentabili; mutazioni core complete arriveranno
  dopo estensione proposal e build.
- Static audit non garantisce sicurezza del codice.
- Build file-backed assume singolo writer.

### Test plan

- build UI modifica solo descendant;
- parent e runtime attivo invariati;
- manifest/hash verificabili e rebuild riproducibile;
- tampering descendant rilevato;
- parent mancante e proposal invalida respinti;
- capability code auditato ma non eseguito;
- reflection produce candidate `built`, mai promoted;
- suite, build EXE e smoke.

### Evidenza implementativa corrente

- `seed/core/descendant.py` introduce `DescendantBuilder`,
  `DescendantManifest`, verifica hash e isolamento.
- Build sotto `lab/descendants/<mutation_id>/`, mai nel runtime attivo.
- Descendant contiene copia parent, candidate, proposal, manifest e hash file.
- Manifest dichiara sempre `executable=false` e `active=false`.
- Rebuild stesso candidate/proposal produce stesso content hash.
- Tampering su file o contratto manifest viene rilevato.
- `parent_version`, `mutation_id` e capability id bloccano path traversal.
- Proposal legacy supportate: trait, UI, persona, policy, capability nuova e
  prune capability.
- Codice capability riceve static audit, ma non viene eseguito.
- Reflection S2 costruisce descendant, registra evento `descendant_built` e
  transiziona `proposed -> built`.
- Build fallito produce evaluation `fail` e candidate `rejected`.
- Verifica: `72 passed, 1 skipped`.

### Rischi residui osservati

- Descendant non e ancora eseguibile: e una rappresentazione isolata di stato,
  capability e proposal.
- Snapshot parent non contiene ancora intero source/runtime.
- Static audit capability non sostituisce dry-run o sandbox execution.
- Nessun evaluator puo ancora produrre un `pass`; candidate `built` restano
  non-promovibili.

## Feature Context Pack - S2 Legacy Reflection Migration

### Fonti SEED

- `00_Visione_Prodotto.md`
- `01_Architettura.md`
- `02_EvolutionEngine.md`
- `06_Esperimento.md`
- `11_Contratto_Mutazione.md`
- `12_ImplementationPlan.md` - evidenza S1

### Decisioni

- `run_reflection()` non applica piu direttamente mutazioni.
- Il selettore legacy resta temporaneamente, ma le mutazioni selezionate
  diventano `MutationCandidate` registrate nel lineage.
- Ogni reflection crea uno snapshot parent univoco e recuperabile.
- La proposta legacy completa resta nel record lineage, separata dal contratto
  typed, per permettere future build descendant.
- La validazione legacy e registrata come `inconclusive`, non come evaluation
  `pass`: non puo sbloccare la promozione.
- Proposte invalide vengono registrate e poi transizionate a `rejected`.
- Digest e scheduler mostrano candidate proposte; `applied` resta vuoto.
- Pruning automatico diretto viene sostituito da note/proposte.
- `_validate_and_apply()` e rollback legacy restano disponibili solo per
  compatibilita e migrazione, ma non vengono chiamati dal reflection.

### Scope

- integrare `LineageStore` in `EvolutionEngine`;
- conversione proposal legacy -> candidate typed;
- snapshot parent univoci;
- validation-only boundary;
- digest `proposed`;
- UI/scheduler compatibili con candidate proposte;
- test di assenza applicazione diretta e audit lineage.

### Non-goals

- build descendant;
- evaluator reali con outcome `pass`;
- promozione, shadow o canary;
- rimozione definitiva del codice apply legacy;
- mutazioni al core attive.

### Rischi

- Il selettore LLM legacy continua a ridurre le proposte prima del lineage.
- La proposta completa puo contenere codice generato non ancora auditato.
- Gli snapshot parent copiano stato/capability ma non sono build complete.
- Nessuna candidate puo essere attivata finche S3-S5 non esistono.

### Test plan

- reflection registra candidate valida senza applicarla;
- proposta invalida viene registrata e rifiutata;
- candidate conserva proposal legacy e parent snapshot;
- snapshot multipli non si sovrascrivono;
- pruning non cambia stato capability;
- digest e scheduler riconoscono `proposed`;
- suite completa e smoke EXE.

### Evidenza implementativa corrente

- `EvolutionEngine.run_reflection()` non chiama piu `_validate_and_apply()`.
- Le proposte selezionate diventano `MutationCandidate` nel lineage.
- Il proposal payload completo resta ricostruibile dal candidate id.
- La validazione legacy produce `inconclusive` oppure `fail`, mai `pass`.
- Candidate invalide vengono transizionate a `rejected`.
- Snapshot parent hanno id timestamp univoco e non vengono sovrascritti.
- Pruning automatico diretto sostituito da `dormant_proposal` /
  `prune_proposal`.
- Scheduler e UI digest riconoscono candidate `proposed`.
- Report aggregato espone integrita, conteggio candidate/evaluation e stati,
  senza esportare proposal o evidence.
- Verifica: `59 passed, 1 skipped`.
- Build PyInstaller pulita riuscita; smoke EXE: finestra `SEED` responsive,
  nessun dialog crash.

### Rischi residui osservati

- Il selettore legacy conserva cap fisso e categorie limitate.
- Candidate restano non attivabili finche S3-S5 non introducono descendant,
  evaluator e promotion authority.
- `_validate_and_apply()` resta nel codice per test/rollback migrazione, ma non
  e raggiunto dal reflection.
- Proposal contenente codice resta locale nel lineage prima dell'audit S3/S4.

## Feature Context Pack - S1 Lineage Foundation

### Fonti SEED

- `00_Visione_Prodotto.md`
- `01_Architettura.md`
- `02_EvolutionEngine.md`
- `07_Struttura_Repo.md`
- `10_Fonti_Ricerca.md`
- `11_Contratto_Mutazione.md`

### Wiki collegata

- `JarvisDocs/LLM_Wiki/wiki/Runtime_Harness_Adaptation.md`
- `JarvisDocs/LLM_Wiki/wiki/Agent_Harness_Best_Practices.md`
- `JarvisDocs/LLM_Wiki/wiki/Jarvis_Cognitive_User_Model_Execution_Harness.md`

### Decisioni

- Una mutation candidate e un record typed, non un dizionario libero.
- Il lineage e append-only e deve rilevare manomissioni accidentali o dirette.
- Ogni evento conserva parent, candidate/version reference, tipo e payload.
- Il generatore non puo promuovere direttamente la propria candidate.
- Una candidate senza evidenza puo essere esplorata, non promossa.
- La fondazione non cambia ancora il comportamento legacy di `EvolutionEngine`:
  prima si introduce il nuovo boundary, poi si migra il reflection pass.

### Scope

- dataclass `MutationCandidate`;
- validazione campi, stati e segnali attesi;
- store lineage file-backed append-only con hash chain;
- transizioni di stato governate;
- promotion gate minimo;
- verifica integrita e test automatici.

### Non-goals

- costruzione descendant;
- evaluator reali;
- shadow/canary;
- supervisor e recovery;
- migrazione del reflection pass legacy;
- mutazioni al core attive.

### Rischi

- File store non gestisce ancora writer multipli tra processi.
- Hash chain rileva alterazioni, ma non sostituisce firma crittografica.
- Il runtime legacy resta capace di applicare mutazioni dirette finche la
  feature successiva non migra `EvolutionEngine`.

### Test plan

- round-trip candidate;
- validazione campi mancanti e valori invalidi;
- blocco promozione senza evidenza o rollback;
- transizioni illegali respinte;
- eventi append-only ordinati;
- verifica hash chain;
- rilevazione tampering.

### Evidenza implementativa corrente

- `seed/seed/core/lineage.py` introduce:
  - `MutationCandidate` typed;
  - validazione contratto e segnali attesi;
  - transizioni di stato esplicite;
  - blocchi minimi di promozione;
  - record evaluator;
  - lineage file-backed append-only con hash chain SHA-256;
  - rilevazione di contratto candidate modificato dopo la registrazione;
  - verifica integrita e tampering.
- `seed/tests/test_lineage.py` contiene 10 test dedicati.
- Verifica eseguita dopo fix packaging: `56 passed, 1 skipped` sulla suite SEED.

### Rischi residui osservati

- Il lineage non e ancora collegato a `EvolutionEngine`; il reflection legacy
  continua ad applicare direttamente.
- Lo store assume un singolo writer; manca lock multi-processo.
- Hash chain senza firma rileva modifiche, ma un attaccante con pieno accesso al
  disco potrebbe riscrivere l'intera catena.
- Non esistono ancora descendant build, evaluator reali o promotion authority.

## Storico ordine S1-S11

1. `S1 Lineage Foundation`
2. `S2 Legacy Reflection Migration`
3. `S3 Descendant Builder`
4. `S4 Replay And Evaluator Harness`
5. `S5 Shadow, Canary And Promotion`
6. `S6 Stable Boot Supervisor`
7. `S7 Her-like Onboarding`
8. `S8 Compatible Personality Runtime`
9. `S9 Online Research Lane`
10. `S10 Model Role Separation And Design Governor`
11. `S11 Optional Voice Lane`

Questa sequenza e' storica. S9 e S10.1-S10.5 sono implementate; S11.1-S11.2
sono implementate e S11.3 resta nella futura fase UI. I gate owner restano
invariati. La feature attiva corrente e dichiarata in cima al documento.

## Storico feature - S9 Online Research Lane

SEED deve poter cercare informazioni aggiornate online tramite un adapter
provider-neutral. I primi provider previsti sono
[Exa Search API](https://docs.exa.ai/) e
[Tavily](https://docs.tavily.com/); la scelta concreta resta configurabile e
non deve entrare nella logica conversazionale centrale.

Contratto minimo pianificato:

- tool call tipizzata per search, extract e ricerca approfondita;
- query redatta dal privacy gate prima dell'invio remoto;
- API key conservata solo in `core_config`, mai in prompt, trace o lineage;
- risultati con URL, titolo, data/freshness quando disponibile e provenance;
- risposta finale con citazioni verificabili e distinzione tra fonte e
  inferenza del modello;
- timeout, rate limit, budget/cost cap e fallback esplicito tra provider;
- nessun browsing autonomo continuo o raccolta indiscriminata di dati;
- evaluator dedicati a grounding, qualita fonti, prompt injection e leakage.

S9 fu avviata dopo approvazione manuale S8.

### Stato implementazione S9 (2026-06-12)

Verifica preliminare: nessun adapter Exa/Tavily era presente nel runtime
(l'assunzione "adapter gia presenti" non corrispondeva al codice). La lane e
stata implementata da zero in `seed/core/research.py`:

- contratto tipizzato `ResearchResult`/`ResearchOutcome`; operazioni search,
  extract e deep search (`search_depth`/`type` lato provider);
- `ExaAdapter` e `TavilyAdapter` dietro la stessa interfaccia; il provider
  primario e `research.provider` in config, fallback esplicito sull'altro;
- query SEMPRE redatta dal privacy gate prima dell'uscita, piu' leakage check
  difensivo sulle key configurate (blocco `leakage` se il regex non copre);
- API key solo in `core_config` (`research.exa_api_key`/`tavily_api_key`);
  l'audit `research_call` registra solo aggregati: mai query, key o testo;
- timeout per provider, cap giornaliero `daily_call_cap` (blocco `budget`),
  nessun browsing autonomo: una richiesta utente = una chiamata;
- risultati con url, titolo, snippet, data quando disponibile e provenance
  provider; scanner anti prompt-injection flagga i contenuti sospetti;
- risposta finale: sintesi LLM grounded con citazioni `[n]` verificate da
  `grounding_report` (citazioni invalide -> sintesi scartata, fallback
  deterministico alle sole fonti); inferenze marcate `(inferenza)`;
- evaluator dedicati come funzioni pure: `grounding_report`,
  `source_quality_report`, `scan_injection`, `leakage_check`;
- integrazione: intent deterministici `research_search` ("cerca online ...",
  "cerca ... sul web") e `research_deep` ("approfondisci ...") registrati da
  `SeedApp`, zero token per il routing.

Evidenza: `tests/test_research.py`, 21 test offline (adapter parsing, privacy,
budget, fallback, injection, grounding, router). Suite completa: 175 passed,
1 skipped (preesistente). Nessuna promotion, nessuna mutazione del lineage:
S9 e codice core proposto, soggetto al gate di Cristian.

Aggiornamento 2026-06-12 (post smoke test Cristian, esito ok):

- tiering pagine analizzate: `quick` (3) per query corte/fattuali, `basic` (5)
  default, `deep` (10) per "approfondisci ..."; valori in config
  (`max_results_quick`/`max_results`/`max_results_deep`), euristica
  deterministica `ResearchLane.classify_depth`, zero token;
- il report telemetria aggrega ora la sezione `research` (calls, ok, fallback,
  per provider, per depth, blocchi): solo aggregati, mai query o key;
- la capability builtin `web_search` (scrape DuckDuckGo senza citazioni ne'
  budget) e' stata messa `dormant`: la lane S9 e' l'unico percorso web
  governato. Riattivabile da Cristian dal manifest;
- ampiezza legata alla preferenza esplicita dell'utente: comandi "analizza
  piu/meno fonti", "fonti standard" regolano `research:breadth` (persistente,
  correggibile, auditato). Floor fisso a 3 fonti per ogni tier (anti fiducia
  cieca), nessun massimo verso l'alto: il deep scala quanto serve
  (quick 3+b, basic 5+2b, deep 10+4b).

### Riepilogo finale S9 (2026-06-12)

Scope consegnato, in sintesi:

| Componente | Dove | Stato |
|---|---|---|
| Lane provider-neutral (Exa/Tavily, search/extract/deep) | `seed/core/research.py` | fatto |
| Privacy gate sulla query + leakage check + audit aggregato | `research.py` | fatto |
| Timeout, cap giornaliero, fallback esplicito | `research.py` + config | fatto |
| Citazioni verificate, fonte vs inferenza, anti-injection | `research.py` | fatto |
| Tiering quick/basic/deep (3/5/10) + euristica deterministica | `research.py` | fatto |
| Ampiezza su preferenza utente, floor 3, no tetto deep | `research.py` + intent | fatto |
| Intent deterministici (cerca/approfondisci/piu-meno fonti) | `seed/core/app.py` | fatto |
| Report telemetria sezione `research` (solo aggregati) | `seed/core/telemetry.py` | fatto |
| Builtin `web_search` dormant (lane unico percorso web) | `capabilities_builtin` | fatto |
| 32 test offline dedicati; suite 186 passed, 1 skipped | `tests/test_research.py` | verde |

Non incluso (per scelta, fuori scope S9): browsing autonomo continuo,
estrazione multi-pagina ricorsiva, cache dei risultati, UI dedicata.

- [x] Chiusura gate S9 e via libera a S10 - owner gate Cristian
  (implementazione e smoke test completati 2026-06-12; spunta riservata a Cristian)

## Feature future - S10/S11 Model Roles e Voice

Piano completo in `13_ModelRoles_Voice_Plan.md`.

- S10 separa conversation, tool builder e design reviewer. Reviewer resta
  read-only e non diventa promotion authority.
- Baseline Ollama da benchmarkare: `gemma4:31b`, `qwen3-coder-next`,
  `gpt-oss:120b`, fallback reviewer `nemotron-3-super`.
- S11 aggiunge ElevenLabs STT/TTS opzionale con consenso, chiave scoped in
  `core_config`, retention minima e fallback testuale.
- Nessuna chiave ElevenLabs reale e stata fornita o inserita.
- S10/S11 non sono attive e non anticipano implementazione durante S9.
