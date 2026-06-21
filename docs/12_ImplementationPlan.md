# 12 - Piano implementativo SEED

> Questo piano governa lo sviluppo di SEED. Non modifica lo stato o i gate del
> progetto JARVIS.

## Feature Context Pack - P0 Onboarding E Provider

**Feature esatta:** `P0 - Onboarding E Provider`, prima fase del programma
[`../ProductionPlan.md`](../ProductionPlan.md) autorizzato dall'owner il
2026-06-14. P1-P5 restano fuori scope fino a review separata.

### Fonti e decisioni estratte

- `ProductionPlan.md`: onboarding BYOK obbligatorio; Ollama Cloud consigliato e
  unico fallback automatico; OpenRouter e Vercel AI Gateway alternative PAYG;
  chat bloccata finche almeno un provider non e configurato e validato; key
  cifrate DPAPI; modelli configurabili per ruolo; audit senza prompt o key.
- `00_Visione_Prodotto.md`: primo avvio conversazionale, privacy e controllo
  spiegati prima della raccolta; ipotesi correggibili; superficie primaria
  minimale e conversation-first.
- `03_PrivacyGate.md`: nessun contenuto personale remoto prima del privacy gate;
  credenziali escluse da prompt, trace, lineage e report.
- `13_ModelRoles_Voice_Plan.md`: ruoli distinti `conversation`, `tool_builder`,
  `design_reviewer`, `design_reviewer_fallback`; cambio modello auditato;
  reviewer e builder senza promotion authority.
- `11_Contratto_Mutazione.md`: separazione autorita, evidenza e rollback restano
  invarianti; configurare provider non autorizza mutazioni o promozioni.

### Scope P0

1. Provider Hub locale con profili separati Ollama Cloud, OpenRouter e Vercel.
2. Key persistite cifrate tramite DPAPI; nessuna key nel config JSON leggibile,
   audit, log, prompt, trace o lineage.
3. Test connessione reale, discovery modelli e test conversazione.
4. Preset SEED e mapping modelli per ruolo, configurabili e ripristinabili.
5. Fallback automatico consentito solo verso Ollama Cloud; mai verso PAYG.
6. Gate di avvio: onboarding personale e chat remota bloccati senza provider
   validato; comandi locali di configurazione/recovery restano accessibili.
7. Bridge UI per stato, configurazione, revoca, test e link dashboard.
8. Migrazione compatibile della configurazione legacy single-provider.

### Non-goals P0

- installer, aggiornamenti, GitHub Releases e SmartScreen (P1);
- lint/build optimization e bundle ML offline (P2);
- planner NL, tool builder da chat e canary reale (P3);
- redesign visuale completo e accessibilita finale (P4);
- smoke su tre PC e pilot esterno (P5);
- fallback automatico verso OpenRouter o Vercel;
- inserimento di key reali nel repository o nei test.

### Test plan P0

- key cifrata a riposo e assente da output/audit;
- profili provider separati, revoca e migrazione legacy;
- discovery modelli, validazione e test conversazione con fake HTTP;
- preset e mapping ruolo validati;
- fallback solo verso Ollama Cloud e divieto fallback PAYG;
- onboarding/chat bloccati senza provider validato;
- comandi locali e recovery disponibili durante il blocco;
- suite completa, core acceptance e compileall.

### Rischi e assunzioni

- DPAPI lega le credenziali all'utente Windows; copie del file provider su un
  altro account non sono decifrabili.
- Cataloghi e nomi modello cambiano lato provider: preset mancanti producono
  errore esplicito e richiedono scelta utente, non sostituzione silenziosa.
- Test automatici usano fake HTTP; validazione con provider/key reali resta
  smoke owner prima del gate distribuzione.
- Il bridge P0 espone funzioni complete; rifinitura visuale appartiene a P4.

### Evidenza P0 pronta per review (2026-06-14)

- `seed/core/provider_hub.py`: profili separati Ollama Cloud/OpenRouter/Vercel,
  key DPAPI-at-rest, discovery modelli, test conversazione, preset, mapping
  ruolo, revoca e policy fallback `ollama_cloud_only`.
- `seed/core/config.py`: gate distribuzione `provider_hub.required`; il template
  tester lo abilita. Config legacy importata nel Provider Hub come non validata
  e key in chiaro rimossa dal config installato.
- `seed/core/model_router.py`: fallback cross-provider possibile solo tramite
  client Ollama Cloud esplicito; nessun percorso automatico verso PAYG.
- `seed/core/onboarding.py` + `seed/core/app.py`: consenso prima del setup;
  onboarding personale e chat remota bloccati finche un provider non supera
  discovery e test conversazione. Comandi locali/recovery restano disponibili.
- `seed/ui/shell.py` + `seed/ui/surface/index.html`: superficie Provider con
  stato attivo, configurazione, test, revoca, preset, ruoli e dashboard.
- `tests/test_provider_hub.py`: cifratura/no leakage, validazione, catalogo,
  revoca, fallback Ollama-only e gate onboarding.
- Verifica: suite completa `469 passed`; core acceptance `12/12`; `compileall`
  verde; `git diff --check` verde.

### Rischi residui P0

- Nessun provider/key reale e stato usato durante questa fase: smoke Ollama
  Cloud, OpenRouter e Vercel resta owner-gated prima della distribuzione.
- La configurazione avanzata ruoli usa una superficie funzionale minimale; la
  rifinitura UX e accessibilita completa appartengono a P4.
- P0 non produce installer ne bundle ML offline: l'app non e ancora
  distribuibile ai tester finche P1/P2 e i gate P5 non vengono eseguiti.
- Il gate P0 resta aperto in attesa di review owner; P1 non e autorizzata da
  questa evidenza.

## Feature Context Pack - P1 Installer Completo E Aggiornamenti

**Feature esatta:** `P1 - Installer Completo E Aggiornamenti`, seconda fase del
programma [`../ProductionPlan.md`](../ProductionPlan.md), autorizzata
esplicitamente dall'owner il 2026-06-14 dopo esecuzione P0.

### Fonti e decisioni estratte

- `ProductionPlan.md`: Windows installer Inno Setup; distribuzione PyInstaller
  `onedir`; shortcut avvia sempre supervisor; dipendenze e checkpoint ML
  inclusi; nessun download post-installazione; dati preservati durante upgrade;
  uninstall con scelta conserva/elimina; release/update manifest e SHA-256;
  update confermato, verificato, con backup, migrazione, health e recovery.
- `11_Contratto_Mutazione.md`: runtime attivo non sovrascritto senza rollback;
  health indipendente, fallback known-good e audit obbligatori.
- `04_Sandbox_Sicurezza.md` e `03_PrivacyGate.md`: dati/config/credenziali fuori
  dal payload applicativo; update non riceve autorita implicita su dati utente.
- `12_ImplementationPlan.md` S6/R7: supervisor esterno, operations
  transazionali, backup/restore e migrazioni sono boundary gia esistenti da
  estendere, non duplicare.

### Scope P1

1. Convertire SEED e supervisor a build `onedir`.
2. Creare staging release riproducibile con runtime, supervisor, asset,
   dipendenze e checkpoint ML dichiarati.
3. Generare manifest release, pacchetto update, SHA-256, schema dati e note.
4. Estendere updater supervisor a directory package atomico con backup e
   rollback su health fallita.
5. Script Inno Setup unsigned: shortcut sempre al supervisor, upgrade che
   preserva `%LOCALAPPDATA%\SEED`, spazio richiesto, uninstall conserva/elimina.
6. Documentazione tester SmartScreen/hash senza certificati autofirmati.
7. Test packaging/update/manifest e smoke disponibile localmente.

### Non-goals P1

- lint/dependency audit e ottimizzazione peso (P2);
- planner/tool builder/canary da chat (P3);
- rifinitura UI/accessibilita finale (P4);
- pilot su tre PC e pubblicazione GitHub Release reale (P5);
- acquisto certificato code-signing o installazione certificati root.

### Test plan P1

- build onedir per app e supervisor;
- staging release contiene asset e checkpoint richiesti, senza key/config utente;
- manifest e SHA-256 verificabili;
- update directory: hash mismatch blocca, backup creato, applicazione atomica,
  health failure ripristina runtime precedente;
- installer compila quando Inno Setup disponibile;
- shortcut punta al supervisor; upgrade non tocca dati; uninstall richiede
  scelta esplicita per dati;
- suite completa, core acceptance, compileall e smoke EXE/supervisor.

### Rischi e assunzioni P1

- Inno Setup non era installato al rilevamento iniziale; e stato installato
  localmente da fonte ufficiale per compilare l'artefatto P1.
- Checkpoint ML locali possono essere molto grandi; P1 privilegia completezza.
  Report dimensioni e rimozione peso inutile appartengono a P2.
- Installer unsigned attivera SmartScreen; istruzioni e hash mitigano il rischio
  ma non eliminano il warning.
- Pubblicazione su GitHub Releases resta fuori scope P1 e richiede gate P5.

### Evidenza implementativa P1 - 2026-06-14

- Build PyInstaller convertite a `onedir` per runtime e supervisor.
- `seed/scripts/build_release.py` produce layout applicativo separato, bundle
  checkpoint ML offline, update ZIP, manifest release, versione schema dati e
  SHA-256; supporta finalizzazione dell'hash installer.
- `seed/installer/SEED.iss` produce installer Inno Setup unsigned, preserva i
  dati durante upgrade, crea shortcut solo verso supervisor e chiede conferma
  esplicita prima di eliminare dati in uninstall.
- `seed/installer/TESTER_GUIDE.md` documenta SmartScreen e verifica SHA-256
  senza installare certificati.
- Model resolver forza modalita Hugging Face/Transformers offline quando trova
  il bundle installato per privacy filter, emotion wav2vec2 ed embedding mpnet.
- Supervisor applica update ZIP directory con estrazione protetta, backup,
  verifica hash, health check e rollback runtime su errore.
- Release locale generata: `seed/release/0.3.0-pilot`, 5243 file applicativi,
  circa 5.10 GB installati; update ZIP SHA-256
  `c5e6e7864a4eb1e3d591f26b7d50b4cdcdd05e1ad4b5775758a28007c3bd67d8`.
- Installer unsigned finale: 3,343,607,920 byte, SHA-256
  `06fd769d0404dd9f18a987569ace4f07ba411595180bf6e12879c41de7ff178c`.
- Verifiche: suite completa `475 passed`; compileall passato; core acceptance
  `12/12`; tutti gli hash release verificati; smoke install completo e
  `SEEDSupervisor.exe --help` passati; smoke uninstall silenzioso ha rimosso
  l'applicazione temporanea preservando il marker dati locale.

### Rischi residui P1

- Installer e payload sono intenzionalmente unsigned: SmartScreen resta atteso.
- Install/upgrade/uninstall su macchine pulite resta un gate manuale P5.
- Lo smoke uninstall iniziale ha esposto e poi corretto un default distruttivo:
  uninstall silenzioso ora conserva sempre i dati e il prompt interattivo usa
  `No` come default. Il test ha rimosso la configurazione locale di sviluppo,
  che deve essere riconfigurata manualmente senza riportare key nei log.
- Il pacchetto e molto grande per dipendenze ML/checkpoint inclusi; riduzione
  peso e warning PyInstaller appartengono esplicitamente a P2.
- Pubblicazione GitHub Release, note definitive e hash ufficiale richiedono
  approvazione owner dopo review dell'artefatto locale.

### Follow-up P1 - GitHub Release Update Manager (2026-06-20)

**Autorizzazione owner:** completare il percorso gia previsto da P1 dalla
GitHub Release fino allo staging locale, senza avanzare lo scope della feature
attiva D0 e senza modificare i gate manuali.

Decisioni operative:

- la fonte remota e solo `releases/latest` del repository ufficiale SEED;
- il confronto usa la versione del manifest installato, non il nome del tag;
- il controllo e read-only e puo avvenire all'apertura delle impostazioni;
- download e applicazione richiedono consenso esplicito dell'utente;
- viene scaricato solo `runtime-update.zip`; modelli invariati e dati utente
  non vengono riscaricati o modificati;
- il pacchetto viene scritto prima come `.part`, supporta ripresa tramite HTTP
  Range, poi viene verificato SHA-256 e spostato nello staging Operations;
- errori rete, manifest malformato, downgrade, asset mancante o hash errato
  falliscono chiusi e non creano `pending_update.json`;
- dopo lo staging, il riavvio passa dal supervisor esistente, che applica il
  pacchetto, esegue health check e rollback automatico su errore;
- l'aggiornamento separato del supervisor resta fuori da questo follow-up:
  sostituire in sicurezza il processo che sta eseguendo richiede un bootstrap
  dedicato. Le release che cambiano il supervisor devono richiedere il nuovo
  bootstrap invece di dichiarare un update runtime-only.

Test richiesti:

- nessun update quando le versioni coincidono o la remota e precedente;
- manifest/asset GitHub valido produce proposta con versione, byte e note;
- consenso assente non scarica e non crea marker;
- download completo e ripreso verifica hash e crea marker supervisor;
- hash errato, risposta Range incoerente e rete fallita lasciano il runtime
  corrente intatto;
- UI espone controllo, conferma, progresso, update pronto e riavvio.

Evidenza implementativa del follow-up:

- `seed/core/release_updater.py` implementa discovery della release ufficiale,
  confronto versione manifest, validazione asset, download riprendibile,
  progresso, SHA-256 e staging tramite `OperationsManager`;
- `OperationsManager` calcola gli hash in streaming e conserva il marker
  esistente consumato dal supervisor;
- `supervisor_cli --wait-pid` impedisce la sostituzione del runtime mentre il
  processo corrente e ancora aperto;
- il pannello Sistema espone controllo, consenso, percentuale, stato pronto e
  riavvio supervisionato;
- versione baseline impostata a `0.3.2-pilot-p2`; installazioni precedenti
  richiedono un ultimo bootstrap per acquisire updater e supervisor coordinato;
- verifica locale: `660` test passati in quattro processi isolati, `ruff` verde,
  `compileall` verde, check live read-only della release `0.3.1` riuscito.

Rischi residui:

- il primo aggiornamento automatico end-to-end richiede una futura release
  successiva a `0.3.2`; fino ad allora il percorso e coperto con transport
  simulato, staging reale locale e discovery live read-only;
- aggiornamenti del supervisor continuano a richiedere il bootstrap; l'Update
  Manager applica intenzionalmente solo il runtime directory package;
- interruzioni ripetute conservano il `.part` per la ripresa e possono occupare
  temporaneamente fino alla dimensione del pacchetto runtime.

### Follow-up P1 - Update In-Place E Retention Sicura (2026-06-21)

**Autorizzazione owner:** verificare e correggere il push `82c1c5a`, destinato a
impedire crescita locale non limitata durante aggiornamenti e uso prolungato.
Il follow-up resta manutenzione P1 e non avanza la feature attiva D0.

Decisioni operative:

- il runtime aggiornato resta sempre nella stessa directory installata
  `.../SEED/runtime`; non vengono create directory runtime versionate;
- l'applicazione resta atomica: estrazione in directory temporanea, backup
  transitorio, sostituzione della directory corrente, health check e rollback;
- i backup runtime transitori e i marker update hanno retention limitata;
- i pacchetti update applicati o falliti non restano indefinitamente nello
  staging; un package referenziato da `pending_update.json` e sempre protetto;
- backup manuali/UI dell'utente non vengono eliminati automaticamente;
- versioni attiva, rollback, known-good e versioni richieste da candidate non
  terminali non possono essere eliminate, indipendentemente dal limite;
- descendant ed evaluator run si eliminano soltanto per candidate terminali;
  stato lineage assente, invalido o ambiguo implica conservazione fail-closed;
- memoria, config, credenziali, lineage append-only e `.part` riprendibili non
  vengono toccati.

Test richiesti:

- due update consecutivi modificano gli stessi path runtime senza creare
  sibling versionati e mantengono rollback funzionante;
- active/rollback/known-good e parent di candidate aperte sopravvivono alla
  retention anche quando sono i piu vecchi;
- backup manuali sopravvivono, backup automatici e runtime backup rispettano i
  limiti;
- package pending e `.part` sopravvivono, package orfani e history eccedente
  vengono rimossi;
- candidate non terminali conservano descendant/evaluation; artefatti di
  candidate terminali possono essere rimossi oltre il limite.

Evidenze di verifica (2026-06-21):

- `670` test distinti passati in processi separati, inclusi `8` test con OPF
  reale, updater, supervisor, rollback, packaging, UI, voice e worker sandbox;
- due update consecutivi sostituiscono la stessa directory `runtime` e il test
  esclude directory sibling `runtime-v*`;
- la retention dei runtime backup usa il timestamp monotono nel nome creato dal
  supervisor, non l'`mtime` ereditato da `copytree`: il backup appena creato non
  puo essere scambiato per il piu vecchio prima del health check;
- watcher OPF terminabile e weak-reference: lo shutdown non accumula thread e
  non attende indefinitamente un modello ancora in caricamento;
- `ruff check seed scripts tests`, `compileall seed scripts` e
  `git diff --check` passati; rimosso un import inutilizzato che bloccava lint.

Rischi residui:

- i file `.part` vengono conservati per permettere resume dopo interruzione;
  possono occupare temporaneamente fino alla dimensione del runtime, ma non
  vengono duplicati per tentativi ripetuti della stessa versione;
- backup manuali e artefatti con formato sconosciuto restano fail-closed e non
  vengono rimossi automaticamente, quindi richiedono pulizia esplicita se
  creati fuori dai flussi gestiti;
- la release installabile deve essere rigenerata dopo merge per distribuire il
  fix ai tester; questa verifica riguarda il sorgente e il workflow locale.

### Follow-up P1 - Reinstallazione Pulita Tester Con Memoria Preservata (2026-06-21)

**Autorizzazione owner:** fornire al tester una procedura una tantum per
rimuovere installazioni SEED duplicate e ripartire dall'installer completo
aggiornato, preservando esclusivamente la memoria locale.

Decisioni operative:

- lo script opera solo sotto `%LOCALAPPDATA%` e sui path SEED riconosciuti;
- la memoria canonica e `data/seed.db`; eventuali sidecar SQLite
  `seed.db-wal` e `seed.db-shm` vengono preservati insieme;
- prima della cancellazione viene creata una copia verificata tramite SHA-256
  fuori da `%LOCALAPPDATA%/SEED`; la copia resta disponibile dopo il reset;
- processi SEED e supervisor vengono arrestati prima della copia SQLite;
- vengono rimossi installazioni runtime/modelli, duplicati riconoscibili,
  dati rigenerabili, config e credenziali, lineage, workspace, backup, shortcut
  e avvio automatico HKCU;
- la root dati viene ricreata contenendo soltanto i file memoria preservati;
- nessun repository, documento utente o path fuori da `%LOCALAPPDATA%` viene
  enumerato o cancellato;
- modalita `-WhatIf` mostra il piano senza modificare il PC; l'esecuzione reale
  richiede conferma testuale o parametro esplicito `-Yes`.

Test richiesti:

- parsing PowerShell valido;
- presenza di guardie path, `-WhatIf`, conferma e backup hashato;
- allowlist memoria limitata a `seed.db`, `seed.db-wal`, `seed.db-shm`;
- cleanup di startup e shortcut dichiarato;
- build release copia lo script tester e lo include in `SHA256SUMS.txt`.

Rischi e limiti:

- provider key, preferenze non ancora consolidate nel DB, capability generate,
  lineage e file workspace vengono intenzionalmente persi;
- una memoria SQLite gia corrotta viene copiata ma non riparata; lo script
  verifica identita byte-per-byte, non integrita semantica del database;
- installazioni collocate manualmente fuori da `%LOCALAPPDATA%` non vengono
  rimosse automaticamente per evitare cancellazioni eccessive.

Evidenze di verifica (2026-06-21):

- parser Windows PowerShell 5.1 valido;
- simulazione locale `-WhatIf -Yes` riuscita: rilevata una installazione
  canonica e `data/seed.db`, zero modifiche eseguite;
- `25` test packaging e distribution gate passati;
- `ruff check seed scripts tests`, `compileall seed scripts` e
  `git diff --check` passati;
- il release builder copia `Reset-SEED-Keep-Memory.ps1`; il bootstrap manifest
  lo dichiara come `tester_reset` e `SHA256SUMS.txt` lo include automaticamente.

### Follow-up P1 - Release 0.3.3 E Latest Site (2026-06-21)

**Autorizzazione owner:** pubblicare `v0.3.3-pilot-p2` con retention sicura,
update in-place e reset tester, quindi renderla latest per sito e updater.

Decisioni operative:

- bump coerente di package, bootstrap e default build a `0.3.3-pilot-p2`;
- build dal commit `main` definitivo dopo merge e CI verde;
- runtime, supervisor, bootstrap, manifest, somme, guida e reset script vengono
  rigenerati; nessun monolitico oltre i limiti GitHub viene pubblicato;
- modelli invariati vengono riutilizzati byte-per-byte, ma devono essere
  disponibili come asset della nuova release o tramite contratto esplicito
  verificato dal bootstrap; una latest incompleta non viene pubblicata;
- `release-manifest.json` e `SHA256SUMS.txt` devono descrivere tutti gli asset
  effettivamente scaricati dal bootstrap;
- il sito continua a usare GitHub `releases/latest` e l'API latest: nessun tag
  versione viene hardcodato nella pagina; la pubblicazione aggiorna download,
  versione, data, dimensione e SHA-256 automaticamente;
- la release precedente resta disponibile per rollback, ma non latest.

Test richiesti:

- suite mirata version/build/release, Ruff, compileall e diff check;
- manifest e somme verificati localmente;
- bootstrap/runtime smoke non distruttivo;
- release GitHub pubblicata con asset richiesti e nessun file oltre 2 GiB;
- URL `releases/latest/download/SEED-Bootstrap-Setup-Unsigned.exe` HTTP 200;
- API latest e sito mostrano `v0.3.3-pilot-p2` con hash installer corretto.

Rischi residui:

- upload dei modelli invariati puo essere lungo anche senza ricompressione;
- asset e installer restano unsigned, quindi SmartScreen e atteso;
- non viene modificato o aggiornato Graphify.

Evidenza implementativa pre-release:

- i modelli invariati sono pin-nati a `v0.3.2-pilot-p2` nel manifest con URL
  `https://github.com/Criss-0429/Seed_ai/releases/download/...` e hash originali;
- il bootstrap accetta URL riusati soltanto con HTTPS, host `github.com`, owner
  e repository SEED esatti, senza query o fragment; URL esterni falliscono;
- runtime, supervisor, bootstrap, reset script, manifest, somme e guida restano
  asset nuovi della `0.3.3`; i circa 3,9 GB di modelli non vengono duplicati;
- `34` test packaging/distribution/updater passati, inclusi URL pin-nato valido,
  URL malevolo bloccato, asset mancante bloccato e generazione metadata riuso.

Evidenza pubblicazione:

- release `v0.3.3-pilot-p2` pubblicata come latest dal commit
  `460316a2e9afdcf360af0729683e070182ab6452`;
- pubblicati sette asset nuovi per circa 248 MB: bootstrap, runtime, supervisor,
  manifest, somme, guida tester e reset script; digest e dimensioni GitHub
  corrispondono ai file locali;
- i quattro asset modello restano nella release `v0.3.2-pilot-p2`; tutti gli URL
  pin-nati rispondono HTTP 200 e il bootstrap ne verifica gli hash originali;
- smoke del runtime e del supervisor pacchettizzati conclusi con exit code `0`;
- il sito usa l'API latest per versione, link, dimensione e digest SHA-256
  dell'installer, mantenendo il download diretto alla release latest;
- corretto il workflow release per validare anche i tag Git annotati senza
  conflitto sul ref locale.

## Feature Context Pack - P2 Lint E Riduzione Dimensioni

**Feature esatta:** `P2 - Lint E Riduzione Dimensioni`, terza fase del programma
[`../ProductionPlan.md`](../ProductionPlan.md), autorizzata esplicitamente
dall'owner il 2026-06-14 dopo review P1.

### Fonti e decisioni estratte

- `ProductionPlan.md`: introdurre quality gate con Ruff, format check,
  typecheck progressivo core, dependency audit, secret scan, import-cycle
  check, test, acceptance, compileall, build e smoke; rimuovere solo peso
  inutile, mantenendo dipendenze e checkpoint ML richiesti.
- `ProductionPlan.md`: release env pulito, Torch CPU-only, niente backend GPU,
  niente test/documentazione/cache/moduli ML inutilizzati, niente UPX finche
  non verificato; crescita oltre 5% richiede motivazione.
- `03_PrivacyGate.md` e `04_Sandbox_Sicurezza.md`: secret scan e build non
  devono leggere o incorporare config/key/dati utente.
- `11_Contratto_Mutazione.md`: ottimizzazione packaging non modifica authority,
  rollback, supervisor o known-good boundary.
- Evidenza P1: baseline locale circa 5.10 GB installati e installer unsigned
  3,343,607,920 byte; warning PyInstaller e duplicazioni richiedono audit P2.

### Scope P2

1. Introdurre quality gate riproducibile e reportabile.
2. Misurare baseline per installer, installato, dipendenze, modelli, avvio e RAM.
3. Usare ambiente release pulito e dipendenze CPU-only.
4. Rimuovere test, documentazione, cache, backend GPU e moduli non richiesti dal
   payload, senza rimuovere funzionalita o checkpoint richiesti.
5. Correggere warning/import inutilizzati/duplicazioni rilevanti per release.
6. Rigenerare release, confrontare dimensioni e applicare budget regressione 5%.
7. Eseguire test completi, acceptance, compileall, build e smoke EXE/installer.

### Non-goals P2

- nuove capability runtime, heartbeat, planner, tool builder o canary (P3);
- redesign visuale/accessibilita (P4);
- pilot su tre PC, pubblicazione release o firma codice (P5);
- rimozione di checkpoint ML o dipendenze necessarie per uso offline;
- UPX o cambiamenti funzionali non richiesti dalla riduzione payload.

### Test plan P2

- quality gate eseguibile con esito e report espliciti;
- nessuna key/config/dato utente nel payload;
- import e dependency audit senza blocker non documentati;
- build onedir e installer completi;
- modelli offline presenti e caricabili;
- report dimensioni baseline/finale e crescita <=5% oppure motivata;
- suite completa, core acceptance, compileall e smoke release/installer.

### Rischi e assunzioni P2

- Torch e checkpoint dominano il payload; riduzione possibile senza cambiare
  funzionalita puo essere limitata.
- Ruff/typecheck su codice storico possono produrre debito fuori scope: il gate
  progressivo deve bloccare nuove regressioni senza refactor indiscriminato.
- Ricompilare installer LZMA2 completo richiede circa un'ora sulla macchina
  corrente; viene eseguito solo dopo verifiche rapide.
- Ambiente release pulito puo richiedere download dipendenze; nessuna key utente
  deve essere usata o copiata durante build/audit.
- `pip-audit` segnala `CVE-2025-3000` per Torch 2.12 senza fix/version bounds,
  mentre la descrizione advisory riguarda `torch.jit.script` in Torch 2.6.0.
  SEED non usa `torch.jit.script` e carica checkpoint locali `safetensors`;
  il gate ignora esplicitamente solo questo ID e resta bloccante per ogni altra
  vulnerabilita.
- `winsdk` non pubblica wheel Python 3.14 e la build sorgente fallisce con il
  compilatore disponibile. Era gia facoltativo con fallback euristico: viene
  escluso dall'ambiente release pulito, senza rimuovere capability core.

### Evidenza implementativa P2 - 2026-06-14

- Quality gate riproducibile in `seed/scripts/quality_gate.py`: Ruff check,
  format progressivo sui boundary P2, mypy progressivo core, dependency
  consistency/audit, secret scan, import-cycle scan, compileall, suite completa
  e core acceptance.
- Ambiente release pulito creato da `seed/scripts/create_release_env.ps1` con
  sole dipendenze runtime/build; tooling dev separato in
  `requirements-dev.txt`.
- `librosa`, `numba` e `llvmlite` rimossi dal runtime: emotion WAV usa ora
  `soundfile` + `scipy.signal.resample_poly`, gia richiesti.
- Build/staging rimuove test, cache, documentazione modello e pacchetti audio
  inutilizzati; mantiene Torch CPU e tutti tre checkpoint ML richiesti.
- `SEED.exe --smoke` aggiunge verifica runtime non interattiva per release.
- Report finale in `seed/release/0.3.0-pilot-p2/SIZE_REPORT.md`:
  - installer: 3,303,358,272 byte, circa 40,25 MB meno della baseline P1;
  - installato: 4,975,893,031 byte, `-2.481%`;
  - runtime: 650,107,763 byte;
  - modelli: 4,303,647,588 byte;
  - primo avvio smoke: 1,0 s; RAM picco: 54,059,008 byte;
  - installazione tester locale: 340,7 s.
- Hash finali verificati:
  - installer SHA-256
    `e07d4c9116ca094fe6ac324e42564ef4481c10ce7bd97ba7fb563d83a39fd8f5`;
  - update SHA-256
    `ac42cb24511454b768ea5610eb0bd3d20a5f82553c7d8ef856404a56cbcad041`.
- Smoke install, runtime installato, supervisor, hash entrypoint e uninstall
  silenzioso con preservazione dati: passati.
- Gate finale: `478 passed`, core acceptance `12/12`, compileall, lint,
  typecheck progressivo, dependency audit, secret scan e import-cycle verdi.

### Rischi residui P2

- Modelli richiesti dominano ancora il payload (circa 4,30 GB); ridurli
  violerebbe il requisito offline P1.
- Installer resta intenzionalmente unsigned e richiede SmartScreen guidance.
- Warning PyInstaller residui sono import opzionali di librerie terze
  (`tensorboard`, `pycparser` table, `scipy.special._cdflib`, Linux libgomp);
  smoke runtime installato e suite non mostrano dipendenze mancanti operative.
- `CVE-2025-3000` resta eccezione audit documentata: advisory senza fix/version
  bounds, descritta per `torch.jit.script` 2.6.0; SEED non usa quel percorso.
- Test su tre PC, Defender e pubblicazione release restano P5.

## Feature Context Pack - P4 UI/UX

**Feature esatta:** `P4 - UI/UX`, quinta fase del programma
[`../ProductionPlan.md`](../ProductionPlan.md), autorizzata esplicitamente
dall'owner il 2026-06-14 dopo review e hardening P3. P5 resta fuori scope.

### Fonti e decisioni estratte

- `ProductionPlan.md`: P4 richiede logo/icona Windows, onboarding visuale,
  impostazioni provider/modelli, stati coerenti loading/errore/offline/quota/
  fallback, indicatore discreto provider/modello, accessibilita P0-P5, overlay
  rifinito, linguaggio umano per permessi/recovery/rollback e stato
  installazione/aggiornamento visibile.
- `00_Visione_Prodotto.md`: primo avvio minimale e relazionale; SEED spiega
  controllo, osservazione e annullamento in linguaggio semplice; inferenze
  correggibili; superficie primaria conversazionale e superfici operative
  secondarie.
- `03_PrivacyGate.md` e `11_Contratto_Mutazione.md`: UI e onboarding non
  espongono key o memoria raw; permessi, recovery, rollback e promotion devono
  restare espliciti, interrogabili e owner-gated.
- `17_UI_Implementation_Plan.md` e `SEED_UI/`: la base B conversazionale,
  presenza, overlay, orb, superfici secondarie e governance P0-P5 sono gia
  implementate; P4 deve completarle senza redesign o dipendenze remote.
- `DESIGN_PRINCIPLES.md` e `JARVIS_v6_WORKFLOW.md`: conversation-first,
  ack/stato/finale leggibili, privacy per architettura, stato sempre visibile e
  silenzio mai ambiguo durante task iniziati dall'utente.

### Gap P4 verificati

1. Nessun asset logo/icona applicazione riusabile da surface, PyInstaller e
   installer Windows.
2. Il primo avvio mostra il prompt conversazionale ma non una progressione
   visuale comprensibile di provider, consensi e accesso alla chat.
3. Gli stati operativi non hanno un contratto visuale unico per
   loading/errore/offline/quota/fallback.
4. Provider/modello sono visibili, ma fallback e stato di disponibilita non
   sono comunicati in modo coerente.
5. Update pending e backup sono sepolti nel pannello Sistema; versione,
   installazione e recovery non hanno una sezione chiara.
6. Dialog e copy tecnici usano ancora formulazioni poco umane in alcuni flussi
   di permission, rollback e mutation.

### Scope P4

- introdurre asset brand locali e collegarli a surface, build PyInstaller e
  installer Windows;
- aggiungere onboarding visuale progressivo senza sostituire la conversazione;
- introdurre un contratto UI per stati operativi e renderlo nella surface;
- completare indicatore provider/modello/fallback e pannello Sistema con stato
  installazione, versione, update, backup e recovery;
- migliorare copy di permessi, recovery e rollback mantenendo approval e gate;
- aggiungere test di contratto UI/accessibilita/packaging e verifica visuale
  locale della surface.

### Non-goals P4

- pilot su tre PC, Defender, SmartScreen reale, pubblicazione release o smoke
  provider/voce reali (P5);
- nuova build installer completa multi-GB salvo necessita stretta;
- modifica di policy fallback, provider, trust, mutation o rollback;
- dipendenze web, font remoti, framework frontend o raccolta dati aggiuntiva;
- spunta checkbox o avanzamento automatico a P5.

### Test plan P4

- asset logo/icona presenti e referenziati da UI/build/installer;
- onboarding visuale mostra stato provider e passi successivi senza sbloccare
  la chat indebitamente;
- stati loading/error/offline/quota/fallback leggibili e accessibili;
- indicatore provider/modello/fallback e stato installazione/update visibili;
- copy permission/recovery/rollback esplicito e owner-controlled;
- test UI/packaging mirati, Ruff, suite completa, core acceptance, compileall,
  sintassi JS e smoke visuale locale.

### Rischi e assunzioni P4

- l'icona Windows generata localmente resta unsigned come l'app;
- gli stati quota/offline dipendono dagli errori provider disponibili: la UI
  deve degradare in categorie comprensibili senza inventare diagnosi;
- smoke visuale in WebView verifica layout locale; microfono, SmartScreen e
  macchine pulite restano gate P5.

### Evidenza implementativa P4 - 2026-06-14

- aggiunti asset brand locali SVG/ICO e collegati a surface, PyInstaller,
  supervisor e installer Windows;
- aggiunti onboarding visuale, stato operativo accessibile, visibilita
  provider/modello/fallback e stato installazione/update/recovery;
- migliorato il copy umano di permission e rollback senza cambiare authority,
  policy o gate;
- test mirati UI/packaging: `40 passed`;
- suite completa: `496 passed`; core acceptance: `12/12`;
- Ruff mirato, `compileall`, sintassi JavaScript e `git diff --check`: passati;
- lo smoke visuale automatico non e stato eseguito: il browser integrato ha
  bloccato sia il server locale sia `file://` per policy. Contratti HTML/JS e
  test automatici sono verdi, ma resta necessaria la review visuale owner;
- non e stata prodotta una nuova build installer multi-GB: la resa finale
  dell'icona nell'EXE/installer e il pilot su macchina pulita restano gate P5.

### Rischi residui P4

- layout WebView, icona Windows installata e copy nei dialog reali richiedono
  smoke manuale owner;
- quota/offline/fallback sono classificazioni conservative degli errori
  disponibili e non diagnosi certe;
- P4 e pronta per review owner; nessun checkbox e stato modificato e P5 non e
  stata avviata.

### Nota di roadmap futura - Adaptive Web Rendering

Su richiesta owner del 2026-06-14 e stata predisposta la fase post-pilot
`P6 - Adaptive Web Rendering`, specificata in
[`18_Adaptive_Web_Rendering_Plan.md`](18_Adaptive_Web_Rendering_Plan.md).

La capability futura apre una superficie fullscreen isolata e applica piani di
trasformazione generici a contenuti web acquisiti con consenso. Adattamenti
estetici, riduzione del rumore e accessibilita sono esempi, non branch
hardcoded. Originale, cookie e sessioni restano separati; script/rete sono
bloccati per default; fedelta, limiti, confronto e rollback devono essere
visibili. P6 non e implementata e non modifica il gate corrente P4/P5.

**Correzione owner del 2026-06-15:** P6 non rappresenta il passo obbligatorio
verso un catalogo di capability comune. La proprieta fondamentale di SEED e
decidere cosa conviene imparare e cosa no per ogni singolo utente. Bridge,
integrazioni, tool, superfici e persino il renderer P6 devono emergere da
salienza e fitness specifici, confrontati anche con `non fare nulla`; servizi e
casi citati restano esempi non hardcoded. Consenso e permessi restano separati
dalla decisione di proporre l'apprendimento.

## Feature Context Pack - P5 Test E Pilot (sottoinsieme automatico)

**Feature esatta:** `P5 - Test E Pilot`, sesta fase del programma
[`../ProductionPlan.md`](../ProductionPlan.md). L'owner ha approvato P4 il
2026-06-14 accettando il rischio della review visuale EXE ancora aperta e ha
autorizzato l'avvio del **solo sottoinsieme di test automatici** di P5. I test
reali su tre PC (installazione pulita, SmartScreen, Defender, onboarding provider
reale, voce/emotion/embedding senza download, Docker live, crash/recovery,
aggiornamento/migrazione/uninstall su macchina reale) e l'intera sequenza pilot
restano **owner e fuori scope** in questa fase.

### Fonti e decisioni estratte

- `ProductionPlan.md` sezione `P5 - Test E Pilot` lista i test automatici da
  coprire (onboarding obbligatorio, provider/key/model validation, fallback solo
  Ollama Cloud, divieto fallback PAYG, cifratura credenziali, migrazione config
  legacy, installer/uninstall, aggiornamento/corruzione/rollback, caricamento
  locale checkpoint ML, assenza download runtime, tool builder NL, planner task
  graph, canary reversibile, accessibilita, size regression).
- `ProductionPlan.md` sezione `Gate Distribuzione`: nove condizioni che bloccano
  la distribuzione (perdita dati, key esposta, crash non recuperabile, update non
  reversibile, checkpoint ML mancante, download runtime inatteso, onboarding
  aggirabile senza provider, fallback PAYG automatico, uninstall cancella dati
  senza consenso).
- `AGENTS.md`: nessun checkbox spuntato; nessun avanzamento di feature senza
  approvazione owner; verifica eseguita e rischi annotati.

### Stato di copertura verificato (pre-esistente)

I test automatici elencati in P5 sono gia in larga parte coperti dalle fasi
P0-P4, costruite incrementalmente. Mappa verificata:

| Voce P5 | Copertura esistente |
|---|---|
| onboarding obbligatorio / aggirabile senza provider | `test_provider_hub.py::test_required_provider_blocks_personal_onboarding_but_not_local_recovery` |
| provider/key/model validation | `test_provider_hub.py` (validate_and_save, roles catalog) |
| fallback solo Ollama / divieto PAYG | `test_provider_hub.py::test_model_router_external_fallback_is_explicit_ollama_only` |
| cifratura credenziali / key esposta | `test_provider_hub.py::test_profile_is_validated_encrypted_and_public_output_has_no_key` |
| installer / uninstall consensuale | `test_packaging.py::test_inno_shortcuts_always_launch_supervisor_and_preserve_data` |
| aggiornamento / corruzione / rollback | `test_supervisor_update.py` (apply, digest-mismatch fail-closed, onedir rollback, path traversal) |
| checkpoint ML locale / assenza download | `test_model_bundle.py`, `test_packaging.py::test_release_builder_requires_all_three_ml_bundles` |
| tool builder NL / planner task graph / canary | `test_runtime_completion.py`, `test_skills.py`, `test_promotion.py`, `scripts/core_acceptance.py` |
| accessibilita | `test_ui.py` (reduce-motion, hit target, focus, P0/P1 gate) |
| size regression | `test_packaging.py::test_runtime_pruning_removes_tests_caches_and_unused_audio_stack` |

### Gap reali individuati

1. `seed/core/config.py::scrub_legacy_provider_keys` (migrazione config legacy che
   azzera le key single-provider in chiaro dopo l'adozione del Provider Hub) non
   aveva alcun test diretto. E' rilevante sia per la voce P5 "migrazione config
   legacy" sia per il gate "key esposta".
2. Le nove condizioni del `Gate Distribuzione` non avevano un artefatto di
   verifica unico: le garanzie esistono ma sparse per feature, non asserite come
   gate di rilascio unitario.

### Scope P5 (questa fase)

- aggiungere `tests/test_distribution_gate.py`: un test per ciascuna delle nove
  condizioni del `Gate Distribuzione`, cablato ai moduli reali (ProviderHub,
  ModelRouter, BootSupervisor, model_bundle, SeedApp, installer Inno, config),
  cosi il gate diventa un contratto unico verificabile;
- coprire il gap reale `scrub_legacy_provider_keys` (migrazione + redazione key);
- nessuna modifica di codice di produzione, policy, gate o build.

### Non-goals P5 (questa fase)

- test su macchine reali, SmartScreen, Defender, pilot interno/esterno e debrief;
- smoke provider/voce/embedding reali e Docker live;
- nuova build installer o pubblicazione release;
- spunta checkbox o dichiarazione di feature completata;
- duplicare i test gia esistenti se non per consolidarli a livello di gate.

### Test plan P5 (questa fase)

- `tests/test_distribution_gate.py` verde su tutte e nove le condizioni gate;
- copertura nuova di `scrub_legacy_provider_keys` (azzera key in chiaro, atomica,
  opera solo sul config installato, ritorna False senza key legacy);
- suite completa, core acceptance, Ruff mirato e compileall verdi.

### Rischi e assunzioni P5

- i test gate cablano moduli reali con HTTP/registry fake: provano gli invarianti
  software, non sostituiscono lo smoke su hardware reale (resta owner/P5 reale);
- il gate test consolida garanzie gia provate altrove: parte e cross-check
  esplicito dal punto di vista del gate, non semplice duplicazione;
- nessuna key reale entra in repository o test; gli HTTP sono fake locali.

### Evidenza implementativa P5 - 2026-06-15

- aggiunto `tests/test_distribution_gate.py` (13 test): un blocco per ciascuna
  delle nove condizioni del `Gate Distribuzione`, cablato ai moduli reali
  (ProviderHub round-trip senza key in chiaro, ModelRouter fallback Ollama-only e
  divieto PAYG, BootSupervisor apply+rollback e corrupt-update fail-closed,
  model_bundle resolve locale + `HF_HUB_OFFLINE=1`, SeedApp onboarding non
  aggirabile senza provider, installer Inno uninstall consensuale e dati sotto
  `%LOCALAPPDATA%`);
- chiuso il gap reale: tre test nuovi su `config.scrub_legacy_provider_keys`
  (azzera le key single-provider in chiaro, idempotente, e rifiuta file fuori
  dalla root `core_config`);
- nessuna modifica a codice di produzione, policy, gate o build;
- verifica: suite completa `509 passed` (era 496, +13); core acceptance `12/12`;
  Ruff sul nuovo file e `py_compile` verdi;
- restano owner/P5 reale: test su tre PC, SmartScreen, Defender, onboarding
  provider reale, voce/embedding senza download, Docker live, pilot interno ed
  esterno. Nessun checkbox e stato modificato.

### Hardening heartbeat daemon (D1) - 2026-06-15

Su richiesta owner, potenziata la struttura del background heartbeat per servire
"stato visibile" (P4) e "attivita reviewable" (P3 / doc 16), senza toccare la
logica di decisione, i gate o il default del daemon:

- `daemon.py`: nuova funzione pura `heartbeat_health(running, last_heartbeat_at,
  now, heartbeat_seconds)` -> `stopped | stale | healthy` + `seconds_since_heartbeat`
  (`stale` se l'ultimo battito supera `heartbeat_seconds * STALE_FACTOR=2.5`,
  tollerando un tick perso). `review()` ora espone `health`,
  `seconds_since_heartbeat`, `heartbeat_stale` per l'indicatore di stato UI;
- ultimo battito ora **persistito** (`memory.daemon_heartbeat`, tabella separata
  `CREATE TABLE IF NOT EXISTS`, nessuna ALTER/migrazione): `save_heartbeat` nel
  tick + `last_heartbeat()`; `review()` include `last_heartbeat` cosi conteggi
  decisione e flag dei confini D1 restano rivedibili anche dopo riavvio;
- il battito persistito resta aggregato e privacy-safe (mai `topic_ref` o testo);
- verifica: `tests/test_daemon.py` +4 (health stopped/healthy/stale, no-beat=stale,
  review espone health+last_heartbeat, persistenza cross-reopen aggregata); suite
  completa `513 passed`; core acceptance `12/12`; Ruff e compileall verdi.

### Chiusura gap automatico P2 - budget dimensioni - 2026-06-15

Audit P0-P5 per residui automatizzabili: l'unico vero buco era il budget di
regressione dimensioni (P2). `scripts/size_report.py` aveva la soglia >5% inline
in `main()` (non testabile senza un albero di release reale) e **nessun modo di
superarla con motivazione documentata**, nonostante ProductionPlan dica "crescita
superiore al 5% richiede motivazione".

- estratta funzione pura `size_regression_verdict(installed_bytes, baseline_bytes,
  reason=None, threshold_percent=5.0)` -> `{delta_percent, exceeds_budget, reason,
  allowed}`; `allowed` solo se entro soglia OPPURE con motivazione esplicita;
- `main()` usa il verdetto, accetta `--reason`, include `budget` nel report e
  blocca solo se non `allowed`;
- nuovo `tests/test_size_report.py` (9): verdetto entro/oltre soglia, soglia
  esatta non-regressione, blocco senza motivazione, sblocco con motivazione,
  reason vuota non sblocca, baseline non positiva -> errore, e i tre rami di
  `main()` (entro budget scrive report, regressione senza reason blocca, con
  reason ammette);
- verifica: suite completa `522 passed`; core acceptance `12/12`; Ruff e
  `py_compile` verdi. Nessun altro gap automatizzabile residuo P0-P5: il resto e
  esecuzione owner su hardware reale (3 PC, SmartScreen, Defender, provider reali,
  Docker live, pilot). Nessun checkbox spuntato.

## Feature Context Pack - P6 Adaptive Web Rendering

**Feature esatta:** `P6 - Adaptive Web Rendering`, fase post-pilot del programma
[`../ProductionPlan.md`](../ProductionPlan.md), specificata in
[`18_Adaptive_Web_Rendering_Plan.md`](18_Adaptive_Web_Rendering_Plan.md).
L'owner ha chiesto di avviare P6 in anticipo rispetto al pilot reale (override di
sequenza: P6 e' dichiarata post-pilot e fuori dal gate P5). Si procede **una fase
alla volta**, tutto default-OFF e gated; questa iterazione copre **solo la fase
fondazionale P6.0** (contratti + sanitizzazione + fedelta' + fitness gate), senza
alcuna acquisizione web reale.

### Fonti e decisioni estratte

- `18_Adaptive_Web_Rendering_Plan.md`: pannello fullscreen isolato che ripresenta
  contenuti web via piano tipizzato, verificabile, reversibile; mai modifica
  l'originale; quattro livelli di fedelta' (`faithful_interactive`,
  `faithful_readonly`, `partial`, `blocked`); pipeline intent->acquisizione
  consenso->parse->sanitize/isolate->piano->validazione->preview->confronto/
  approvazione->attivazione temporanea o promozione governata->rollback.
- Correzione owner 2026-06-15 (in questo doc): capability **generativa e aperta**,
  emergente da salienza e fitness del singolo utente, **confrontata con "non fare
  nulla"**; nessun branch hardcoded per caso/sito; puo' non essere mai generata
  per un utente senza evidenza.
- `03_PrivacyGate.md`: nessuna lettura silenziosa di tab/cronologia/cookie/
  sessioni; nessun invio automatico dell'HTML completo a provider remoti; analisi
  locale, eventuale uso remoto solo via privacy gate con minimizzazione.
- `04_Sandbox_Sicurezza.md` + `11_Contratto_Mutazione.md`: script/rete disabilitati
  di default nella preview; pagina e istruzioni incorporate trattate come
  contenuto NON affidabile (prompt-injection); ogni trasformazione nuova e' una
  candidate isolata con evidenza, test, preview, approvazione, versione, rollback.
- `17_UI_Implementation_Plan.md`: gerarchia di precedenza P0-P5 (P0 controllo/
  sicurezza > P1 accessibilita' > ... > P5 estetica); un'estetica non puo' ridurre
  contrasto, leggibilita', focus, navigazione tastiera o accesso ai controlli SEED.

### Fasi P6 (forecast, tutte gated, una alla volta)

| Fase | Scope | Stato |
|---|---|---|
| **P6.0** | Contratti tipizzati + sanitizzazione HTML/URL deterministica + classificazione fedelta' + fitness gate (vs "non fare nulla"/browser) + precedenza P0-P5. **Nessuna rete, nessun browser, default OFF.** | **questa iterazione** |
| P6.1 | Acquisizione sorgente con consenso (URL esplicito / HTML fornito / bridge browser opt-in revocabile), temporanea salvo consenso persistenza | owner-gate |
| P6.2 | Generatore di `TransformPlan` tipizzato (css_rules/dom_operations/content_filters) emergente da `AdaptationProfile`, non hardcoded | owner-gate |
| P6.3 | Evaluator deterministico + gate sicurezza/WCAG/anti-injection sul piano prima dell'attivazione | owner-gate |
| P6.4 | Preview fullscreen isolata (script/rete OFF), confronto originale/adattato, uscita/rollback sempre accessibili | owner-gate |
| P6.5 | Candidate->promozione governata (preferenze temporanee restano temporanee; nessuna generalizzazione automatica ad altri siti) | owner-gate |

### Scope P6.0 (questa iterazione)

- `seed/core/web_render.py`: dataclass contratti `RenderRequest`,
  `AdaptationProfile`, `TransformPlan`, `RenderResult` + enum/costanti fedelta';
- `sanitize_html(raw)` deterministico: rimuove `<script>/<style on*>`, attributi
  evento `on*`, URL pericolosi (`javascript:`, `data:` eseguibili), `<iframe>/
  <object>/<embed>`, link/risorse remote; ritorna HTML inerte + elenco rimozioni;
- `classify_fidelity(...)` -> uno dei quattro livelli in base a cio' che resta
  leggibile/interattivo dopo sanitizzazione;
- `decide_render_fitness(...)` (principio owner): genera/propone il renderer SOLO
  se il valore atteso supera "non fare nulla" e l'uso del browser originale;
  altrimenti `skip`. Default = non generare;
- riuso della precedenza P0-P5 (`ui_governance`): un piano che riduce P0/P1 non e'
  ammissibile;
- config `web_render` **default OFF**; nessun comando attivo che tocchi la rete.

### Non-goals P6.0

- nessuna acquisizione web reale (URL fetch, browser bridge): e' P6.1;
- nessun generatore di piano, preview, o promozione: P6.2-P6.5;
- nessun rendering nella trust zone di JavaScript della pagina;
- nessun bypass di paywall/DRM/auth; nessun ad-block garantito; nessuna diagnosi
  di accessibilita';
- nessun branch hardcoded per sito/tema; niente attivazione di default.

### Test plan P6.0

- sanitizer rimuove script/handler/iframe/url-pericolosi e preserva contenuto
  semantico; idempotente; tratta HTML ostile (prompt-injection inline) come
  inerte;
- classificazione fedelta' deterministica sui quattro livelli;
- fitness gate: skip quando il valore non supera "non fare nulla"/browser;
- un piano che viola P0/P1 non e' ammissibile (riuso `ui_governance`);
- contratti validano i campi minimi; default config OFF;
- suite completa, core acceptance, Ruff e compileall.

### Rischi e assunzioni P6.0

- P6 e' dichiarata post-pilot: avviarla ora e' override owner di sequenza; le fasi
  con rete/browser (P6.1+) restano gated e non incluse qui;
- la sanitizzazione e' la prima linea di difesa: implementata conservativa
  (allowlist-oriented), ma il rendering reale isolato arriva solo in P6.4;
- nessuna garanzia di equivalenza perfetta dei siti: i livelli `partial`/`blocked`
  sono parte del contratto, non un difetto.

### Evidenza implementativa P6.0 - 2026-06-15

- nuovo `seed/core/web_render.py` (fondazione pura, **niente rete/browser/os**):
  - `sanitize_html(raw)` allowlist-oriented: scarta script (con contenuto),
    handler `on*`, `style` inline, container pericolosi (iframe/object/form/...),
    commenti (possibili iniezioni), URL pericolosi (`javascript:`/`data:`/...) e
    neutralizza risorse/link remoti; tiene tag/attributi sicuri e `aria-*` (P1);
    deterministica e idempotente; `url_is_unsafe()` rileva schemi offuscati;
  - `classify_fidelity(...)` -> `faithful_interactive|faithful_readonly|partial|
    blocked` (in P6.0 interazioni OFF -> max `faithful_readonly`);
  - `decide_render_fitness(...)`: genera/propone SOLO se il valore atteso supera
    "non fare nulla" e il browser; senza evidenza utente = skip (default skip);
  - `plan_respects_precedence(...)` riusa `ui_governance`: piano che viola P0/P1
    non ammissibile, P4 richiede evidenza P2/P3;
  - contratti `RenderRequest` (consenso obbligatorio), `AdaptationProfile`,
    `TransformPlan` (rollback obbligatorio), `RenderResult` (fedelta' valida);
- config `WebRenderConfig` **default OFF** (`enabled`, `network_acquisition_enabled`,
  `browser_bridge_enabled` tutti False) + sezione in `config.example.json` +
  `redacted_summary`;
- nuovo `tests/test_web_render.py` (21): sanitizzazione (script/handler/iframe/
  url/commenti/remote, HTML ostile prompt-injection reso inerte, idempotenza),
  fedelta', fitness gate, precedenza P0-P5, contratti, default OFF, e assenza di
  import rete/subprocess/os via AST;
- verifica: suite completa `543 passed`; core acceptance `12/12`; Ruff e
  compileall verdi.

### Evidenza implementativa P6.1-P6.5 - 2026-06-15

Owner: "falle tutte una alla volta, seguendo precisamente i principi UI/UX di
SEED_UI". Implementate tutte e cinque le fasi in `seed/core/web_render.py`,
default-OFF, gated, una alla volta; i principi UI/UX sono imposti **per
costruzione** (riuso `ui_governance` P0-P5 + Laws of UX A-E; preview con stato
sempre visibile, controlli uscita/confronto/rollback sempre accessibili, target
>=44px, reduce-motion):

- **P6.1 acquisizione** `acquire_source(...)`: consenso obbligatorio; `html` usa
  HTML fornito (nessuna rete); `url` richiede gate `allow_network` + `fetch`
  INIETTATO (la rete non e' importata dal modulo) + blocco URL non sicuri;
  `browser_bridge` richiede gate `allow_browser` + bridge iniettato; contenuto
  temporaneo, nessuna lettura silenziosa di tab/cookie/sessioni;
- **P6.2 piano** `build_transform_plan(...)`: `TransformPlan` EMERGENTE da bisogni
  di accessibilita' + preferenze esplicite via registry allowlistato per
  semantica (mai per sito); tre profili sintetici -> tre piani diversi senza
  branch hardcoded; bisogni sconosciuti ignorati; semantica preservata + rollback
  + zero `permissions_delta`;
- **P6.3 evaluator/gate** `evaluate_transform_plan(...)`: deterministico,
  fail-closed; blocca injection (`<script`/`javascript:`/`@import`/`url(http`/
  `expression(`), riduzioni P1 (`outline:none`...), tentativi di nascondere i
  controlli SEED (P0); verifica reversibilita' e semantica preservata; report
  WCAG-rilevante;
- **P6.4 preview isolata** `build_preview(...)`: documento HTML inerte con CSP
  `script-src 'none'; connect-src 'none'` (script/rete OFF), chrome SEED (stato
  `aria-live`, controlli `data-seed-action` uscita/confronto/rollback sempre
  accessibili, target >=44px, `prefers-reduced-motion`), CSS del piano scoping su
  `.seed-adapted`, originale separato e non modificato. Nessun JS nella preview:
  le azioni sono dichiarative, il guscio host le collega (P0/isolamento garantiti);
- **P6.5 promozione governata** `RenderCandidate` + `propose_render_candidate` +
  `promote_render`: candidate isolata e temporanea; promozione solo con
  `owner_approved` E `evaluation_passed`; `persist` solo se esplicito; `generalize`
  cross-site sempre rifiutato; default = non promosso;
- `tests/test_web_render.py` ora 40 (acquisizione gated, 3 profili->3 piani,
  gate injection/P1/P0, preview script-free/CSP/controlli/scoping, promozione
  governata, pipeline completa P6.1->P6.5);
- verifica: suite completa `562 passed`; core acceptance `12/12`; Ruff e
  `py_compile` verdi.

### Wiring live UI P6 - 2026-06-15 (completa e funzionante, gated OFF)

Integrata la capability nell'app reale, end-to-end, default OFF, seguendo i
principi SEED_UI:

- `app.py`: `ui_web_render_status` + `ui_web_render_preview` (pipeline governata
  acquire->sanitize->plan->evaluate->preview, fail-closed senza `web_render.enabled`
  e senza consenso; rete reale dietro i flag, non iniettata; audit AGGREGATO senza
  HTML grezzo) + `ui_web_render_promote` (promozione owner-gated dell'ultima
  candidate, temporanea di default, mai cross-site);
- `ui/shell.py` `JsApi`: `web_render_status` / `web_render_preview` /
  `web_render_promote`;
- `ui/surface/index.html`: superficie **"Resa adattiva"** (voce nel selettore);
  anteprima in **`<iframe sandbox="">`** (niente script, niente rete, isolata),
  originale separato e confrontabile, controlli sempre accessibili
  (Confronta / Mantieni-owner / Esci) con target >=44px, stato `aria-live` (B-01),
  reduce-motion dal documento; mostra le rimozioni della sanitizzazione; nessun
  asset remoto;
- config `web_render` aggiunto a `config.example.json` (tutto OFF);
- test: `test_web_render.py` +5 (bridge app: OFF di default, consenso obbligatorio,
  pipeline produce anteprima isolata script-free, url bloccato senza gate rete,
  promote senza candidate); `test_ui.py` +1 (superficie isolata e gated);
- verifica: suite completa `568 passed`; core acceptance `12/12`; Ruff,
  `py_compile` e sintassi JavaScript (estratta, `node --check`) verdi.
- **Resta owner (come P4)**: review visuale nell'EXE e attivazione reale (flag ON,
  acquisizione di rete/bridge browser) richiedono lo smoke owner; nessun flag
  attivato, nessun checkbox spuntato.

## Feature Context Pack - P7 Selective Capability Forge

**Feature esatta:** `P7 - Selective Capability Forge`, programma futuro
specificato in
[`19_Selective_Capability_Forge_Plan.md`](19_Selective_Capability_Forge_Plan.md).

**Stato:** documentato, non implementato e non attivo. La presenza di questo
Context Pack non autorizza l'avvio di P7. P6 resta la fase corrente; P7 parte
soltanto dopo approvazione owner di P6 oppure con override esplicito di
sequenza.

### Decisione owner e correzione normativa

SEED deve poter capire quali strumenti servono allo specifico utente,
costruirli, verificarli e usarli senza richiedere che l'utente conosca token,
API, OAuth o MCP.

La precedente formula `mai self-install automatico` viene sostituita, per
l'architettura obiettivo P7, dalla regola piu precisa:

> **mai auto-espansione dell'autorita**

Il builder continua a non poter installare, approvare o promuovere cio che
genera. Una `CapabilityActivationAuthority` indipendente puo pero attivare
automaticamente una capability verificata quando l'autorita richiesta e un
sottoinsieme deterministico di quella gia concessa. Nuovi account, scope,
categorie di dati, destinazioni o tipi di effetto richiedono consenso. Azioni
irreversibili o ad alto impatto richiedono sempre conferma contestuale.

I riferimenti storici nei precedenti context pack a `mai self-install` restano
come evidenza dello scope e della policy applicata nelle fasi gia eseguite. Non
autorizzano P3 o tool legacy ad auto-attivarsi e non vengono riscritti
retroattivamente. P7 introduce una nuova authority e nuovi contratti prima di
modificare il comportamento runtime.

### Fonti e decisioni estratte

- `00_Visione_Prodotto.md`: SEED non ha un catalogo finale di feature; salienza
  e fitness decidono cosa imparare; generator e promotion authority restano
  separati; l'autorita non puo essere auto-espansa.
- `01_Architettura.md`: candidate/active e il confine principale; Evolution Lab,
  evaluator, lineage, supervisor e trust zone restano separati; connector host
  e Connection Broker non espongono credenziali ai tool generati.
- `02_EvolutionEngine.md`: il bisogno precede la soluzione; `non fare nulla`,
  composizione di capability esistenti, MCP, adapter e tool custom sono
  alternative da confrontare; nessun singolo score compensa blocker.
- `03_PrivacyGate.md`: payload remoti minimi e redatti; password, token, cookie
  di sessione e recovery code sono discard-only; dati sensibili restano locali.
- `04_Sandbox_Sicurezza.md`: codice e connettori non fidati richiedono
  isolamento, provenienza, dependency lock, test avversariali, rete limitata,
  drift detection e quarantena.
- `05_ActivityWatcher.md`: osservazione consensuale, revocabile e limitata;
  pattern e workflow possono sostenere ipotesi ma non autorizzano effetti.
- `11_Contratto_Mutazione.md`: generator, reviewer ed evaluator non possono
  promuovere; l'attivazione authority-contained richiede subset check
  deterministico, eval, shadow/canary, recovery e audit.
- `16_Agentic_Daemon_Plan.md`: pattern Hermes per registry/skills/MCP e OpenClaw
  per daemon/sessioni restano reference subordinate; SEED Core governa.
- `18_Adaptive_Web_Rendering_Plan.md`: P6 e un esempio avanzato di capability
  emergente, non una feature universale; P7 generalizza il processo con cui
  capability differenti possono nascere.
- MCP Authorization, Security Best Practices e Registry: discovery non equivale
  a fiducia; OAuth, token handling, SSRF, scope e server/tool drift richiedono
  boundary espliciti.

### Obiettivo operativo P7

```text
osservazione consentita
-> WorkflowEvidence locale
-> NeedHypothesis
-> FitnessDecision con alternative e no-op
-> ConnectorDescriptor verificato
-> CapabilityPlan
-> build isolato
-> CapabilityEvaluationReport indipendente
-> shadow
-> authority subset check
-> awaiting_connection oppure canary/active
-> outcome, drift, dormienza, quarantena o rollback
```

P7 non costruisce un catalogo universale. Due utenti con la stessa base devono
poter evolvere capability diverse e una terza istanza deve poter decidere di
non costruire nulla.

### Contratti pubblici pianificati

| Contratto | Responsabilita |
|---|---|
| `WorkflowEvidence` | Evidenza derivata locale di ricorrenza, attrito, contesto e outcome; nessun segreto o raw persistente implicito |
| `NeedHypothesis` | Bisogno falsificabile, con evidenze, controevidenze, incertezza e scadenza |
| `FitnessDecision` | Confronto multi-obiettivo tra no-op, riuso, connessione e costruzione |
| `CapabilityPlan` | Comportamento, connector, action contract, autorita, eval, osservazione e recovery |
| `ConnectorDescriptor` | Tipo, provenienza, publisher, versione, digest, schema hash, destinazioni e drift policy |
| `ConnectionRequirement` | Richiesta umana comprensibile di nuova connessione o autorita |
| `AuthorityEnvelope` | Account, dati, effetti, scope, destinazioni, schedule, limiti e durata autorizzati |
| `CapabilityManifestV2` | Manifest riproducibile con connector, schemas, autorita, dipendenze, test, health e rollback |
| `CapabilityEvaluationReport` | Evidenza indipendente deterministica, avversariale, privacy, runtime e recovery |
| `CapabilityLifecycleState` | Stati e transizioni auditabili della capability |

Lifecycle pianificato:

```text
observed -> framed -> researching -> planned -> building -> evaluating
-> shadow -> awaiting_connection | canary -> active
-> dormant | quarantined | rejected | archived
```

### Confini di autorita

P7 mantiene quattro autorizzazioni distinte:

1. `Observation consent`: permette comprensione locale di sorgenti specifiche,
   con opt-in, indicatore, revoca, blocklist e cancellazione.
2. `Connection authority`: collega un account, MCP, applicazione o servizio
   tramite un flusso comprensibile e revocabile.
3. `Execution authority envelope`: definisce precisamente cosa la capability
   puo leggere, fare, dove, quando e con quali limiti.
4. `Irreversible/high-impact confirmation`: conferma contestuale obbligatoria,
   mai delegabile permanentemente.

Una capability puo essere auto-attivata solo se:

- report indipendente valido;
- build digest uguale a quello valutato;
- connector verificato, pinnato e senza drift;
- autorita richiesta sottoinsieme di quella gia concessa;
- nessun nuovo account, scope, dato, destinazione o tipo di effetto;
- nessun effetto irreversibile o ad alto impatto;
- shadow e canary verdi;
- health check, expected observation e recovery validi;
- nessun blocker aperto.

Qualunque confronto ambiguo o incompleto fallisce chiuso.

### Evidence engine e privacy

- osservazione ampia soltanto dopo consenso esplicito e per sorgenti revocabili;
- raw locale effimero, poi secret discard, classificazione sensibilita e feature
  derivate;
- password, token, cookie di sessione e recovery code mai persistiti o usati;
- dati personali, sensibili e finanziari elaborati localmente;
- provider remoti ricevono soltanto evidenza redatta, aggregata e minima;
- assenza di percorso locale sicuro = sorgente non usata;
- pattern osservato non diventa fatto, preferenza o autorizzazione.

Default opportunita inferite:

- almeno 3 occorrenze su 2 sessioni;
- almeno 5 occorrenze su 3 sessioni per ambiti sensibili;
- richiesta esplicita puo superare la ricorrenza, non i gate;
- controevidenza forte blocca o rimanda;
- soluzione esistente adeguata impedisce duplicazione;
- feedback negativo sopprime proposte simili.

### Strategia connector e MCP

Ordine di selezione:

```text
non fare nulla
-> capability attive
-> skill esistente
-> MCP esistente verificabile
-> API/plugin/scripting/file exchange/CLI ufficiale
-> MCP o adapter custom isolato
-> UI automation supervisionata come ultima risorsa
```

Un MCP registry e discovery, non trust authority. Ogni connector richiede
provenienza, versione, digest, dependency lock, schema snapshot, scansione,
destinazioni dichiarate, test sintetici/avversariali e quarantena su drift.

MCP locali operano in processo/container ristretto. MCP remoti passano dal
Connection Broker. Tool, builder, reviewer e descendant non ricevono
credenziali; il connector host espone soltanto handle tipizzati e autorizzati.

### Fasi P7 previste

| Fase | Scope | Gate |
|---|---|---|
| **P7.0** | Contratti, policy, lifecycle, config default-OFF e migrazione V1 conservativa | nessun cambiamento runtime; contratti e migrazione verdi |
| **P7.1** | Local Evidence Engine, consenso, raw effimero, secret discard e revoca | segreti scartati; dati sensibili mai remoti |
| **P7.2** | Need & Fitness Engine, alternative e no-op | utenti sintetici divergono senza branch hardcoded |
| **P7.3** | Connector Discovery & Vetting | connector malevoli o mutati bloccati/quarantinati |
| **P7.4** | Capability Builder V2 isolato | nessun segreto o modifica ambiente principale |
| **P7.5** | Independent Evaluator | nessuna shadow senza report valido |
| **P7.6** | Connection Broker e vault | token mai esposti; revoca/scadenza valide |
| **P7.7** | Activation Authority e autopilot | nuova autorita attende consenso; high-impact bloccato |
| **P7.8** | UX spiegabile e controlli | tester non tecnico comprende capacita e limiti |
| **P7.9** | Health, drift, quarantena, dormienza, pruning e pilot | recovery verificato e zero regressioni P0-P6 |

Tutte le fasi sono gated e vengono implementate una alla volta. P7.0 deve
precedere qualunque modifica runtime P7.

### Piano test P7

- schema, lifecycle, migrazione V1 e authority subset check fail-closed;
- builder incapace di accedere a vault o promotion;
- password/token scartati prima di memoria, prompt, lineage e audit;
- dati sensibili mai remoti;
- revoca sorgente interrompe raccolta e uso futuro;
- utenti sintetici differenti producono capability differenti o no-op;
- assenza di branch hardcoded per email, Canva, Photoshop o altri esempi;
- MCP malevolo, SSRF, token passthrough, scope eccessivo e drift bloccati;
- OAuth simulato con PKCE, `state`, audience, scadenza e revoca;
- MCP custom generato e testato con dati sintetici in isolamento;
- auto-attivazione entro authority envelope esistente;
- nuova autorita produce `awaiting_connection`;
- effetti irreversibili sempre bloccati in attesa di conferma;
- azione reversibile in autopilot verifica outcome e rollback;
- crash recovery, quarantena, dormienza e pruning;
- regressione completa P0-P6, core acceptance, lint, compile e build.

### Acceptance P7 futura

- istanze diverse evolvono capability diverse partendo dalla stessa base;
- `non imparare` resta un esito spiegabile e auditabile;
- nessun componente generatore puo aumentare autorita o accedere al vault;
- nessun segreto entra in memoria, prompt, lineage o audit;
- capability verificata entro autorita esistente puo essere auto-attivata;
- nuove connessioni sono richieste in linguaggio naturale;
- effetti irreversibili non possono essere eseguiti automaticamente;
- drift di connector o dipendenze causa quarantena;
- revoca, restrizione, dormienza e rollback funzionano;
- fallimenti di build, connessione o capability non compromettono SEED.

### Non-goals e rischi

- nessun marketplace o catalogo universale di tool;
- nessuna installazione automatica di MCP non verificati;
- nessuna intercettazione di password, credenziali o sessioni;
- nessuna promessa di integrare software privo di accesso legale e affidabile;
- UI automation non equivale a un'API stabile;
- nessuna delega permanente di azioni irreversibili;
- nessuna modifica retroattiva dei gate e delle capability legacy;
- nessuna implementazione P7 autorizzata da questo solo aggiornamento
  documentale.

### Evidenza implementativa P7.0 - 2026-06-15

Owner: "passa alla P7". Avviata con la fase fondazionale **P7.0** (contratti,
policy, lifecycle, config default-OFF, migrazione V1 conservativa). **Nessun
cambiamento di runtime**: il modulo non e' collegato a osservazione, build o
attivazione; e' analisi/policy pura.

- nuovo `seed/core/capability_forge.py` (puro, niente rete/subprocess/os):
  - **lifecycle FSM** `LIFECYCLE_STATES` + `_TRANSITIONS` + `advance_lifecycle`/
    `can_transition`: fail-closed su stati/transizioni ignote, nessun salto di
    gate (es. `observed->active` vietato), `rejected`/`archived` terminali,
    `quarantined` raggiungibile come fail-safe;
  - **authority subset** `authority_subset(requested, granted)` + `AuthorityEnvelope`:
    `strict_subset_or_equal` deterministico e FAIL-CLOSED — connessione diversa,
    data_class/effect/scope/destination/schedule extra, limite superato o chiave
    sconosciuta, scadenza oltre il concesso, o envelope malformato producono
    escalation; una sola escalation blocca l'auto-attivazione (mai
    auto-espansione di autorita');
  - **secret discard** `discard_secrets`/`looks_like_secret`: discard-only
    (password/token/cookie/recovery/jwt/bearer/sk-/hex), ricorsivo, non redige a
    placeholder — scarta;
  - **contratti V2** tipizzati con invarianti critici: `WorkflowEvidence`
    (sensibile non trattiene raw), `NeedHypothesis` (bisogno prima della
    soluzione, uncertainty [0,1]), `FitnessDecision` (hard_blocker non
    compensabile da utilita'), `ConnectorDescriptor` (kind valido + pinning
    digest per mcp/adapter/plugin), `ConnectionRequirement` (human_reason +
    revoca obbligatori), `CapabilityPlan` (rollback + authority validi),
    `CapabilityEvaluationReport` (pass incompatibile con blocker; `inconclusive`
    mai approvazione implicita), `CapabilityManifestV2` (`auto_activation=False`);
  - **migrazione V1 conservativa** `migrate_v1_capability`: i tool legacy
    diventano manifest V2 con `auto_activation=False` e authority vuota — non si
    auto-attivano, nessun gate riscritto;
- config `CapabilityForgeConfig` **default OFF** (`enabled`,
  `auto_activation_enabled` + soglie ricorrenza) + sezione `config.example.json` +
  `redacted_summary`;
- nuovo `tests/test_capability_forge.py` (27): lifecycle valido/fail-closed,
  secret discard (chiavi/valori/nested), authority subset (uguale/extra/limiti/
  connessione/scadenza/malformato fail-closed), contratti, migrazione V1,
  default OFF, modulo puro (no import rete/exec via AST);
- verifica: suite completa `595 passed`; core acceptance `12/12`; Ruff,
  `py_compile` e JSON di esempio verdi.
### Evidenza implementativa P7.1-P7.9 - 2026-06-15 (collegate al runtime, default OFF)

Owner: "implementale e collegale al runtime funzionante una alla volta". Tutte le
fasi P7.1-P7.9 implementate come engine PURI e a dipendenze iniettate (nessuna
rete/subprocess/credenziale nel codice; rete/OAuth reali restano dietro i flag
owner) e collegate all'app, default OFF, fail-closed:

- **P7.1 Evidence Engine** (`forge_runtime.EvidenceEngine`): consent per-sorgente
  obbligatorio, raw effimero, secret discard (riuso P7.0), classificazione
  sensibilita', WorkflowEvidence derivata (mai raw), revoca = purge; fail-closed
  senza consenso o senza percorso locale sicuro; audit aggregato;
- **P7.2 Need & Fitness** (`NeedFitnessEngine`): soglie ricorrenza (piu' alte per
  sensibili), richiesta esplicita supera ricorrenza ma non i gate, soppressione su
  feedback negativo; `decide_fitness` multi-obiettivo con no-op, ordine
  do_nothing<reuse<connect<build, hard_blocker non compensabile; due profili
  sintetici divergono senza branch hardcoded;
- **P7.3 Connector Vetting** (`ConnectorVetter`): allowlist destinazioni
  (anti-SSRF), scan iniettato (token passthrough/scope), pinning digest/schema,
  drift -> quarantena;
- **P7.4 Builder V2** (`CapabilityBuilderV2`): da CapabilityPlan a manifest V2 con
  build_digest riproducibile e dipendenze pinnate; rifiuta segreti negli schema;
  `auto_activation=False`; nessun riferimento a vault/promotion/activation;
- **P7.5 Independent Evaluator** (`IndependentEvaluator`): `pass` solo con tutti i
  check verdi + digest; prove mancanti -> `inconclusive` (mai approvazione
  implicita); un blocker -> `blocked`;
- **P7.6 Connection Broker + Credential Vault** (`forge_connection`): vault cifrato
  (DPAPI), espone solo handle opachi (mai token, no passthrough), scadenza/revoca;
  broker descrive in linguaggio comprensibile, OAuth INIETTATO (richiede
  access_token+code_verifier+state+audience), `awaiting_connection` se flusso
  assente/incompleto;
- **P7.7 Activation Authority** (`ActivationAuthority`): authority separata,
  fail-closed; auto-attiva solo con eval pass + digest match + no drift +
  shadow/canary verdi + autorita' richiesta sottoinsieme di quella concessa;
  escalation -> `awaiting_connection`; irreversibile -> mai auto (conferma
  contestuale); con `auto_activation_enabled=False` resta `canary`;
- **P7.8 UX** (`forge.CapabilityForge` + `app.ui_forge_*` + JsApi `forge_*` +
  superficie "Capability apprese"): timeline `SEED ha imparato/deciso X perche...`,
  stato, controlli (dimentica osservazioni, sopprimi, revoca connessione); default
  OFF mostra solo la nota;
- **P7.9 Maintenance** (`MaintenanceMonitor`): confronto expected/observed, drift
  autorita' -> quarantena, affidabilita' degradata -> dormienza;
- collegamento: `app.forge = CapabilityForge(cfg.capability_forge, memory, cipher
  DPAPI)`; 6 metodi `ui_forge_*` + 6 JsApi `forge_*`; introspezione runtime: 47/47
  bridge JsApi->app risolvono (0 mancanti);
- test: `tests/test_forge.py` (38) + `tests/test_ui.py` +1 (superficie gated);
- verifica: suite completa `629 passed`; core acceptance `12/12`; Ruff,
  `py_compile`, JSON di esempio e sintassi JavaScript (`node --check`) verdi.
- **Resta owner (come P4)**: attivazione reale (flag `capability_forge.enabled` ON,
  `auto_activation_enabled`, OAuth/fetch/scanner reali iniettati) e smoke visuale
  EXE richiedono lo smoke owner; nessun flag attivato, nessun checkbox spuntato.

## Feature Context Pack - P3 Collegamenti Core

**Feature esatta:** `P3 - Collegamenti Core`, quarta fase del programma
[`../ProductionPlan.md`](../ProductionPlan.md), autorizzata esplicitamente
dall'owner il 2026-06-14 dopo review P2.

### Fonti e decisioni estratte

- `ProductionPlan.md`: heartbeat solo mentre SEED e aperto, reviewable, visibile,
  con silenzio/cooldown predefiniti e senza servizio Windows always-on.
- Correzione owner 2026-06-14: SEED puo avviarsi con Windows solo dopo consenso
  esplicito e deve essere disattivabile. Alla chiusura della finestra chiede
  sempre se mantenere attivo il processo heartbeat oppure terminare SEED.
  L'avvio usa il profilo utente Windows, mai un servizio privilegiato.
- `ProductionPlan.md`: Tool Builder da chat deve attraversare specifica
  tipizzata, conferma scope, generazione isolata, audit, test, design review,
  proposta installazione e approvazione owner; mai self-install.
- `ProductionPlan.md`: Planner NL deve produrre un Task Graph tipizzato usando
  sole capability allowlistate, mostrare anteprima degli effetti, eseguire nodi
  isolati, comunicare stato, verificare il risultato e fermarsi su errore.
- `ProductionPlan.md`: canary reale solo reversibile, allowlistato, dry-run,
  expected observation, rollback verificato e approvazione utente; promotion
  finale sempre owner-gated.
- `16_Agentic_Daemon_Plan.md`, `04_Permessi_Sandbox_Privacy.md` e
  `11_Contratto_Mutazione.md`: i collegamenti conversazionali non ricevono
  autorita implicita; preview, approvazione, isolamento, audit e rollback
  restano boundary separati.
- Boundary esistenti verificati: `BackgroundDaemon`, `GovernedToolBuilder`,
  `TaskGraph`/`CapabilityTaskAgent`, `MutationLifecycle` e promotion authority
  implementano gia i gate tecnici. P3 collega questi boundary alla chat senza
  duplicarli o indebolirli.

### Scope P3

1. Rendere interrogabile dalla chat lo stato heartbeat aggregato e reviewable;
   aggiungere avvio Windows opt-in/disattivabile e scelta esplicita alla chiusura
   tra finestra nascosta con heartbeat attivo e terminazione completa.
2. Tradurre una richiesta naturale di nuova tool in specifica tipizzata e
   richiedere conferma scope prima di generare/stagiare.
3. Eseguire audit e test isolato della tool confermata, produrre esito review e
   proposta installazione separata; non installare automaticamente.
4. Tradurre una richiesta naturale di piano in Task Graph tipizzato validato
   contro la allowlist, con anteprima prima dell'esecuzione.
5. Eseguire un piano solo dopo approvazione esplicita, un nodo isolato alla
   volta, fermandosi al primo errore e riportando stato/esito.
6. Rendere il canary avviabile dalla chat solo tramite preview e conferma
   esplicita; non promuovere mai automaticamente.
7. Audit solo aggregato: nessun testo richiesta, prompt, key o dato personale.

### Non-goals P3

- redesign visuale, logo, accessibilita finale e stati UI completi (P4);
- smoke su tre PC, Defender, pilot e pubblicazione release (P5);
- servizio Windows privilegiato o heartbeat attivo dopo la terminazione completa
  del processo;
- capability non allowlistate, shell libera o effetti destructive/critical;
- self-install tool, auto-promotion mutation o apertura automatica dei gate;
- nuova build installer pesante: P3 modifica e verifica il runtime sorgente.

### Test plan P3

- heartbeat naturale mostra stato e confini, senza avviare servizi OS;
- startup Windows resta disabilitato senza consenso, puo essere revocato e usa
  solo il profilo utente; chiusura finestra distingue hide da terminate;
- tool NL produce specifica e attende conferma; conferma produce staging,
  audit/test/review e proposta, senza installazione;
- planner NL produce solo grafi allowlistati; capability fuori allowlist e
  grafi invalidi vengono bloccati;
- esecuzione piano richiede approvazione esplicita, usa isolamento e si ferma
  su errore riportando risultato;
- canary senza conferma non parte; con conferma attraversa il lifecycle ma non
  chiama promotion;
- audit P3 privo di testo grezzo; suite completa, acceptance e compileall.

### Rischi e assunzioni P3

- Generazione tool e planner semantico richiedono un provider configurato; in
  assenza di provider il flusso deve fallire chiuso con errore leggibile.
- Tool Builder e delega restano default OFF nel template tester: la chat puo
  preparare preview/proposte, ma esecuzione e installazione rispettano i gate.
- Il design reviewer reale puo essere disabilitato; un esito inconclusive non
  viene trasformato in approvazione e impedisce installazione automatica.
- Il rollback dei nodi resta responsabilita delle capability allowlistate e dei
  worker governati; un fallimento interrompe il grafo e non autorizza compensazioni
  arbitrarie.
- Il canary usa evidenza evaluator reale registrata e contesto reversibile gia
  governato; P3 non estende il canary a effetti non rappresentati dal contratto.
- La modalita heartbeat alla chiusura mantiene vivo l'intero processo SEED in
  background, non un demone separato: consumo RAM e superfici attive restano
  quelli del runtime e devono essere chiaramente comunicati.

### Evidenza implementativa P3 - 2026-06-14

- `seed/core/connections.py` collega alla chat quattro flussi espliciti:
  heartbeat reviewable, Tool Builder NL, Planner NL -> Task Graph e canary
  governato. Le proposte sono in memoria e richiedono conferma separata con ID.
- Heartbeat naturale mostra stato aggregato e dichiara i confini
  `supervised_process_only`, `os_service=false`, silenzio e cooldown; non crea
  processi o servizi aggiuntivi.
- `seed/core/startup.py` gestisce l'avvio Windows solo per l'utente corrente
  tramite `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`: richiede
  approvazione esplicita, non richiede admin, non crea servizi ed e revocabile
  dal pannello Sistema.
- Lo startup installato continua a passare dal supervisor P1 e inoltra
  `--background`: SEED parte nascosto con heartbeat attivo e resta richiamabile
  tramite `Ctrl+Spazio`.
- Il pulsante chiudi e la chiusura nativa/Alt+F4 chiedono sempre se mantenere
  heartbeat: conferma nasconde la finestra mantenendo il processo; rifiuto
  termina SEED e `shutdown()` arresta heartbeat, scheduler e collector.
- Tool Builder: richiesta redatta -> specifica JSON validata -> conferma scope
  -> generazione -> staging/audit/test isolato -> `DesignReviewer` indipendente
  reale -> record `REVIEW.json`. Non installa; la UI installa solo con
  `design_review_passed=true` e approvazione owner.
- Planner: il modello riceve solo il catalogo allowlistato; il Task Graph viene
  ricostruito e validato localmente per allowlist, dipendenze e cicli. Anteprima
  e ID precedono l'esecuzione; i nodi safe/read vengono eseguiti isolatamente
  solo dopo conferma owner e il grafo si ferma al primo errore.
- Task Graph con effetti viene bloccato finche non esiste un adapter rollback
  reale verificabile; un flag manifest non viene accettato come prova.
- Canary chat: una preview non avanza nulla; la conferma e limitata alla sola
  `mutation_id` approvata. `MutationLifecycle.advance()` supporta ora il filtro
  per ID e continua a non chiamare mai promotion.
- Audit P3 registra solo ID, conteggi, verdict e classi di rischio; non registra
  testo richiesta, prompt, codice generato, key o argomenti del piano.
- I due piccoli contratti PyInstaller `packaging/pyinstaller/seed.spec` e
  `packaging/pyinstaller/supervisor.spec`, rimossi durante la pulizia spazio post-P2, sono stati
  ripristinati senza rigenerare build o staging pesanti.
- Verifiche finali: `487 passed`; core acceptance `12/12`; quality gate,
  dependency audit, secret scan, import-cycle scan, Ruff, mypy progressivo,
  compileall e `git diff --check` verdi.

### Rischi residui P3

- Provider locale e key erano stati rimossi dallo smoke uninstall P1: il flusso
  Tool Builder/Planner e coperto con fake provider, ma lo smoke reale richiede
  riconfigurazione manuale senza riportare key nei log.
- `design_reviewer_real_enabled` e Tool Builder restano default OFF. Con gate
  chiusi la tool arriva a staging ma la review e `inconclusive` e non e
  installabile: comportamento fail-closed intenzionale.
- L'esecuzione Planner con effetti resta bloccata: il runtime possiede worker
  write-safe governati, ma non ancora un adapter Task Graph che esponga
  rollback token, observation e compensazione per nodo. Safe/read funziona.
- Il risultato dei nodi e riportato a fine esecuzione sincrona; uno stream UI
  visuale dei singoli status appartiene alla rifinitura P4.
- La modalita background non possiede ancora un'icona tray dedicata: il processo
  nascosto si riapre con `Ctrl+Spazio`. Icona e rifinitura visuale appartengono
  a P4.
- Nessuna build installer P3 e stata eseguita: non necessaria per modifiche
  sorgente e avrebbe ricreato diversi GB di staging. Il contratto packaging e
  coperto dalla suite; smoke distribuito resta P5.
- P3 resta pronta per review owner; nessun checkbox e stato modificato e P4 non
  e autorizzata da questa evidenza.

### Benchmark shadow harness richiesto dall'owner - 2026-06-14

- Il precedente D0 confrontava solo pattern architetturali dichiarati e non
  eseguiva runtime esterni. E stato aggiunto
  `scripts/shadow_runtime_bench.py`, benchmark eseguibile esclusivamente su
  fixture sintetiche temporanee.
- Baseline custom SEED pre-fix: `12/13` fixture passate. Bloccati segreti ambiente,
  letture/scritture fuori workspace, subprocess, timeout, output non JSON,
  import/call vietati dallo static audit; scrittura confinata al workspace
  permessa.
- Limite reale rilevato: il backend restricted-process permette l'import di
  `socket`; la rete non dichiarata viene bloccata dallo static audit prima
  dell'esecuzione, ma non e imposta network-off dal processo stesso.
- Report in `benchmarks/shadow-runtime/custom-seed-shadow-report.json` e sintesi
  in `benchmarks/shadow-runtime/README.md`. Nessun dato reale, key, provider,
  rete o repository utente usato.
- Su approvazione owner, OpenHarness `0.1.9` e stato installato solo nella
  sandbox temporanea `C:\tmp\seed-openharness-bench` (237,24 MB inclusa cache)
  ed eseguito esclusivamente in dry-run e tramite permission checker su fixture
  sintetiche: `10/12` pass. Zero model call, tool execution, key o dati reali.
- Il permission checker OpenHarness blocca mutazioni in plan mode, richiede
  conferma in default e protegge path sensibili anche in full auto. Sono pero
  emersi due fail high: gli override CLI `--permission-mode plan` e
  `--permission-mode full_auto` lasciano l'effettivo `permission.mode` a
  `default`; lo stesso merge e usato dal runtime live. Inoltre la sandbox OS e
  disabilitata per default.
- Report in `benchmarks/shadow-runtime/openharness-shadow-report.json`. OpenClaw
  e Hermes restano non installati; Docker CLI e presente ma daemon spento.
  Nessun harness esterno viene collegato a SEED sulla base di questo test.
- Su successiva autorizzazione owner, Hermes Agent `0.16.0` e stato testato in
  sandbox temporanea con sole suite offline di sicurezza, registry, skills e
  delega. Il picco 529,61 MB con cache e stato ridotto immediatamente a 328,81
  MB eliminando la cache; zero provider, key, model call o tool live.
- Hermes mostra pattern validi per registry, tool search, skill AST audit e
  delega scoped, ma e bocciato come runtime/boundary Windows: 9 test approval
  confermano che path assoluti `C:\...` possono bypassare il detector per
  scritture verso shell rc, SSH `authorized_keys` e config Hermes. Report:
  `benchmarks/shadow-runtime/hermes-shadow-report.json`.
- OpenClaw `2026.6.2` e stato testato source-only con clone sparse e runner
  Vitest minimo, senza gateway o runtime completo perche Node locale `22.17.0`
  e inferiore al requisito `>=22.19.0`. Le suite selezionate hanno dato
  `131/131` pass su sessioni/allowlist/token heartbeat e `144/144` pass su
  policy heartbeat/message access.
- OpenClaw resta la reference migliore per heartbeat e session lifecycle, ma
  non un boundary di sicurezza SEED: l'audit statico mostra sandbox default
  `off` e exec security host normale default `full`. Report:
  `benchmarks/shadow-runtime/openclaw-shadow-report.json`.

### Feature Context Pack - P3 hardening post benchmark harness

**Feature esatta:** follow-up di `P3 - Collegamenti Core`, autorizzato
esplicitamente dall'owner il 2026-06-14 dopo i benchmark shadow. P4 e P5
restano fuori scope.

Decisione di adozione:

- da OpenHarness si assorbono semantica read-vs-mutate, protezione path
  sensibili anche in modalita ampia, preview/dry-run e permission hook;
  non si adotta il runtime, il merge CLI inefficace o la sandbox default OFF;
- da Hermes si assorbono registry/tool search tipizzati, audit AST delle skill
  riviste e delega scoped; non si adotta runtime, memoria, gateway, shell o il
  detector path Windows risultato bypassabile;
- da OpenClaw si assorbono sessioni bounded/cancellabili, ownership parent,
  active hours, cooldown, visibility, wake e busy suppression per heartbeat;
  non si adotta il runtime, la sandbox default OFF o l'exec host default full;
- SEED Core resta governatore e reimplementa solo pattern verificati dietro i
  boundary esistenti. Nessuna dipendenza o harness esterno entra nel runtime.

Scope immediato:

- chiudere il solo gap custom emerso: `network_allowed=False` deve bloccare le
  operazioni socket anche nel restricted process, non soltanto nello static
  audit;
- mantenere `network_allowed=True` esplicito per capability autorizzate;
- aggiornare benchmark sintetico e test regressione senza effettuare chiamate
  di rete reali.

Rischi e non-goals:

- il blocco socket Python e difesa aggiuntiva del restricted process, non
  isolamento OS contro codice ostile; per quello resta richiesto il backend
  container con rete disabilitata;
- nessuna modifica heartbeat/session/delega in questo pass: i pattern sono
  fissati, ma verranno applicati solo dentro lo scope delle rispettive feature;
- nessun checkbox, attivazione capability, installazione harness o build
  installer pesante.

Evidenza implementativa:

- `IsolationPolicy.network_allowed` viene propagato al restricted process;
  default `False` installa un guard socket fail-closed, mentre `True` deve
  essere richiesto esplicitamente;
- benchmark custom aggiornato: `14/14`, inclusi
  `runtime_network_socket_blocked` e `runtime_low_level_socket_blocked`;
  nessuna connessione reale effettuata;
- regressioni dedicate verificano blocco default e opt-in esplicito;
- verifica: `492 passed`, core acceptance `12/12`, Ruff mirato, compileall e
  `git diff --check` verdi.

## Posizione corrente

**Stato (2026-06-13):** su approvazione esplicita owner ("implementa tutto, una
fase alla volta, ordine come pianificato") sono state implementate end-to-end e
**lasciate pronte per review** tutte le fasi rimanenti del piano daemon e del
piano UI:

- **D0** Runtime Option Benchmark — owner-approvato (testo, checkbox owner);
- **D1** Daemon host PC-on · **D2** Worker adapter READ-only · **D-OBS**
  Observation lane read-only · **D3** Sandbox hardening · **D4** Capability
  WRITE_SAFE · **D5** Skills procedurali + delega; **D6 ritirata dall'owner**;
- **UI U0-U7** (piano 17), incluso **S11.3** pannello voce (U3).

Le capability con effetti o dati sensibili sono **default OFF / dry-run /
consent-gated / owner-gated**. Il daemon in-process D1 e il worker aggregato
READ-only D2 sono invece default ON perche' non possiedono superfici di effetto;
observation, WRITE_SAFE e skills/delega restano OFF. **Nessun checkbox
spuntato** (D0-D6, UI, S11: spunte riservate a Cristian). Verifiche complessive
dopo UI Integration Hardening: suite `443 passed`, acceptance core `12/12`,
`compileall` e sintassi JS ok. Restano owner: smoke reali voce/microfono/provider,
smoke EXE e apertura dei gate. Non avanzare oltre senza nuova approvazione.

**D0 - Runtime Option Benchmark** (precedente, approvata manualmente dall'owner il
2026-06-13): la proposta iniziale indicava OpenHarness come backend; gli shadow
test reali del 2026-06-14 l'hanno superata. SEED custom resta backend,
OpenHarness fornisce solo pattern permission/dry-run, Hermes pattern
registry/skills/delega e OpenClaw pattern daemon/heartbeat/sessioni. SEED Core
resta sempre governatore; prima attivazione futura READ-only. Il
benchmark confronta i pattern solo su fixture sintetiche privacy-safe: non
installa runtime esterni, non usa repo o dati reali e non concede accesso
shell/file.

La fondazione precedente resta disponibile ma non viene dichiarata chiusa senza
gate owner: memoria M1-M4, Cognitive User Knowledge K1-K4, S10 Model Role
Separation, S11.1 backend voce e S11.2 emotion sono implementati e verificati.
S11.3 pannello voce appartiene alla futura fase UI U3.

## Feature Context Pack - Runtime Completion Program R1-R7

**Feature esatta:** `Runtime Completion Program R1-R8`, autorizzata
esplicitamente dall'owner il 2026-06-13. Completa le implementazioni che nei
piani D3/D5 e UI erano rimaste intenzionalmente a livello di contratto,
planning o adapter non-live.

**Correzione owner:** nessun gateway Telegram/mobile/device. SEED resta
interamente nell'app desktop `SEED.exe`; D6 non fa parte di questo programma e
rimane disattivato/non operativo.

### Fonti e decisioni estratte

- `16_Agentic_Daemon_Plan.md`: isolamento prima degli effetti, capability
  specifiche, expected observation, rollback, consenso granulare e degrado
  chiuso.
- `17_UI_Implementation_Plan.md`, `SEED Brand Identity.dc.html` e
  `SEED Design Guidelines.dc.html`: colore guadagnato, maturazione leggibile,
  controllo utente e nessuna UI che nasconda stato o autorizzazioni.
- `01_Architettura.md`, `04_Permessi_Sandbox_Privacy.md`,
  `11_Contratto_Mutazione.md`: SEED Core resta governatore; worker, sub-agent,
  gateway e tool generati non ricevono autorita' implicita.
- `JarvisDocs/LLM_Wiki/wiki/Agent_Harness_Best_Practices.md`,
  `Runtime_Harness_Adaptation.md` e documentazione JARVIS production: adapter
  tipizzati, audit aggregato, ack/status/finale, recovery verificabile.

### Ordine implementativo autorizzato

1. **R1 / D3** - backend reale container e processo ristretto, con limiti,
   workspace esplicito, ambiente senza segreti, timeout e fail-closed.
2. **R2 / Observation** - collector reali e prudenti per foreground/processi;
   browser solo tramite bridge opt-in, mai scraping silenzioso.
3. **R3 / D5** - esecuzione reale di task graph su sub-agent isolato e
   capability allowlistate.
4. **R4 / Tool builder** - proposta, audit, test isolato, review e installazione
   governata; mai self-install senza owner approval.
5. **R5 / Mutation lifecycle** - raccolta automatica evidenze shadow/canary,
   valutazione e proposta di promozione; la promozione finale resta owner-gated.
6. **R6 / Brand evolutivo** - hue iniziale e maturazione deterministica basata
   su eventi reali confermati, reversibile e separata dalla personalita'.
7. **R7 / Gestione operativa** - backup/restore, update staging verificato,
   migrazioni versionate, crash recovery e piano di disinstallazione pulita.

### Invarianti e non-goals

- Tutte le superfici live/pericolose restano default OFF.
- Nessun gateway esterno: conversazione, controllo e notifiche restano dentro
  `SEED.exe`.
- Credenziali e dati personali non entrano in prompt, lineage o audit.
- Docker assente/non avviato, endpoint irraggiungibile o isolamento incompleto
  causano un blocco esplicito, non un fallback meno sicuro.
- Observation richiede consenso per-classe prima della raccolta, non solo prima
  della persistenza; la revoca interrompe i collector e purga i derivati.
- Tool builder e sub-agent non ricevono shell generica: eseguono contratti
  allowlistati in workspace isolati.
- Shadow e canary possono avanzare automaticamente solo su evidenza
  deterministica; nessuna promotion finale automatica senza owner approval.
- Update, restore, migrazione e uninstall sono transazionali e richiedono una
  richiesta esplicita; nessuna cancellazione automatica.
- Nessun checkbox viene spuntato dall'agente.

### Test plan e acceptance

- test unitari fail-closed per ogni gate e adapter;
- test integrazione locali con fake provider/server e filesystem temporanei;
- smoke Docker solo se daemon disponibile, altrimenti preflight bloccato;
- suite completa, compileall, core acceptance e build EXE;
- documentazione di configurazione, rollback e rischi residui aggiornata.

### Evidenza implementativa corrente (2026-06-13)

- `isolation.py` + `process_runner.py`: Docker con network off/read-only/cap
  drop/resource limits e fallback processo ristretto con env senza segreti e
  filesystem confinato al workspace; backend assente = blocco.
- `observation.py`: collector reale consent-first per foreground e categorie
  processi; non raccoglie titoli, URL, screenshot o contenuti.
- `skills.py`: `CapabilityTaskAgent` esegue task graph validati usando solo
  capability attive e allowlistate, ogni nodo nel backend isolato selezionato.
- `tool_builder.py`: candidate staging, audit statico, test isolato e install
  solo con reviewer + owner gate.
- `mutation_lifecycle.py`: evidenza shadow dall'evaluator indipendente,
  canary tramite probe reale e proposta persistente di promozione; non chiama
  mai `promote()`.
- `brand.py`: hue stabile e maturazione/chroma deterministici da eventi locali
  confermati.
- `operations.py`: backup verificabile, restore transazionale, update staging,
  migrazioni versionate con rollback e uninstall confermato.
- D6/gateway ritirata dall'owner: nessuna integrazione esterna collegata
  all'app.

Verifica corrente: suite `444 passed`, core acceptance `12/12`, `compileall`
verde. Docker CLI presente ma daemon non avviato durante la verifica: il test
container live resta bloccato correttamente; il processo ristretto e' coperto
da test reale, incluso blocco lettura fuori workspace.

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
- Decisione proposta storica, poi superata dagli shadow test reali:
  OpenHarness non entra come backend. SEED custom resta il boundary; Hermes,
  OpenHarness e OpenClaw forniscono solo pattern selezionati. Nessun runtime
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

### D6 - Ritirata
- Decisione owner 2026-06-13: nessun gateway Telegram/mobile/device. Il modulo,
  la configurazione e i test gateway sono stati rimossi; SEED resta dentro
  `SEED.exe`.

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
  9, `test_skills` 14, `test_ui` 14.
- suite completa `433 passed`; acceptance core `12/12`; `compileall` ok; EXE
  ricostruiti. Tutte le lane default OFF; nessuna attivazione; nessun checkbox.

### Resta owner (non fatto)
- smoke reali con provider/voce/PC; attivazione delle lane (observation/write-safe/
  skills) e apertura dei gate; test owner UI su EXE.

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
- `packaging/pyinstaller/seed.spec` include esplicitamente `tiktoken_ext.openai_public`, cosi
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
