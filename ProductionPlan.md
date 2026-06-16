# Piano SEED: Prototipo Distribuibile Ai Tester

## Decisioni Fissate

- Distribuzione: futuro sito SEED → download installer Windows.
- Release e aggiornamenti ospitati tramite GitHub Releases.
- Installer e applicazione **senza certificato code-signing acquistato**.
- Avviso SmartScreen accettato e spiegato ai pochi tester.
- Nessun certificato autofirmato installato nei Trusted Root.
- Ollama significa sempre **Ollama Cloud**.
- Ollama Cloud è provider consigliato e fallback predefinito.
- OpenRouter e Vercel disponibili come alternative PAYG.
- Claude/Anthropic escluso.
- Ogni tester usa proprie key.
- Chat bloccata finché almeno un provider BYOK non viene configurato e validato.
- Tutte dipendenze ML, checkpoint emotion recognition, embedding e relativi pacchetti vengono installati insieme all’app.
- Nessun download ML o gate bloccante dopo installazione.

## P0 — Onboarding E Provider

### Onboarding BYOK Obbligatorio

Flusso primo avvio:

1. Presentazione SEED e pilot di 14 giorni.
2. Spiegazione privacy, memoria locale, mutazioni e rollback.
3. Scelta provider:
   - Ollama Cloud: consigliato, piano Free disponibile;
   - OpenRouter: PAYG;
   - Vercel AI Gateway: PAYG.
4. Link ufficiali per creare account e key.
5. Inserimento e validazione reale key.
6. Recupero modelli disponibili.
7. Applicazione modelli consigliati oppure scelta avanzata.
8. Test conversazione reale.
9. Consensi opzionali per observation, voce e ricerca.
10. Onboarding personale conversazionale.
11. Riepilogo correggibile.
12. Accesso alla chat.

Key invalida o provider irraggiungibile impediscono completamento onboarding.

### Provider Hub Multi-Provider

Supportare profili separati per:

- Ollama Cloud;
- OpenRouter;
- Vercel AI Gateway.

Funzioni:

- key cifrate tramite DPAPI;
- test connessione;
- elenco modelli;
- modello configurabile per ruolo;
- preset SEED;
- audit aggregato senza prompt o key;
- fallback automatico esclusivamente verso Ollama Cloud;
- mai fallback automatico verso provider PAYG.

Ruoli:

- `conversation`
- `reflection`
- `tool_builder`
- `design_reviewer`
- `design_reviewer_fallback`

### Impostazioni

Utente può sempre:

- cambiare o revocare key;
- aggiungere provider;
- cambiare modello per ruolo;
- ripristinare preset;
- testare configurazione;
- vedere provider e modello attivi;
- vedere utilizzo/fallback;
- aprire dashboard provider.

## P1 — Installer Completo E Aggiornamenti

### Installer Windows

Usare Inno Setup con distribuzione `onedir`.

Installer include:

- `SEED.exe`;
- `SEEDSupervisor.exe`;
- tutte dipendenze Python;
- Torch CPU;
- Transformers;
- Sentence Transformers;
- NumPy, SciPy, Librosa e dipendenze richieste;
- checkpoint embedding;
- checkpoint emotion recognition attualmente usato da SEED;
- asset UI e capability builtin.

Nota: il runtime attuale usa `wav2vec2`, non `emotion2vec`. Emotion2vec verrà incluso solo qualora diventi backend scelto e testato.

L’installazione deve:

- funzionare completamente senza download successivi;
- creare shortcut che avvia sempre supervisor;
- preservare dati durante upgrade;
- inizializzare configurazione;
- eseguire migrazioni;
- offrire uninstall con scelta conserva/elimina dati;
- mostrare requisiti di spazio prima dell’installazione.

### SmartScreen

Pilot distribuito unsigned.

Sito e istruzioni tester mostrano:

- perché appare SmartScreen;
- nome e versione installer;
- SHA-256 ufficiale;
- procedura per verificare hash;
- procedura per avviare installer;
- nessuna richiesta di installare certificati.

### Aggiornamenti

GitHub Releases contiene:

- installer completo;
- pacchetto update;
- manifest release;
- SHA-256;
- note rilascio;
- versione schema dati.

SEED:

1. rileva nuova versione;
2. informa utente;
3. richiede conferma;
4. scarica update;
5. verifica hash;
6. crea backup;
7. applica update tramite supervisor;
8. esegue migrazioni;
9. verifica health;
10. ripristina known-good su errore.

## P2 — Lint E Riduzione Dimensioni

### Quality Gate

Introdurre:

- `ruff check`;
- `ruff format --check`;
- typecheck progressivo core;
- dependency audit;
- secret scan;
- import-cycle check;
- test completi;
- core acceptance;
- compileall;
- build PyInstaller;
- report dimensioni;
- smoke EXE e installer.

Correggere codice duplicato, import inutilizzati, dipendenze inutilizzate e warning PyInstaller.

### Ottimizzazione Installer Completo

Poiché tutti modelli e pacchetti ML devono essere inclusi, obiettivo non è installer piccolo: obiettivo è evitare peso inutile.

Azioni:

- virtualenv release pulito;
- Torch CPU-only;
- rimuovere backend GPU;
- rimuovere test, documentazione, cache e moduli ML inutilizzati;
- includere solamente checkpoint effettivamente usati;
- eliminare duplicazioni tra installer e runtime;
- compressione installer LZMA2;
- preferire build `onedir`;
- niente UPX finché non verificato con antivirus;
- regression budget: crescita superiore al 5% richiede motivazione.

Produrre report separato:

- peso download installer;
- peso installato;
- peso per dipendenza;
- tempo installazione;
- tempo primo avvio;
- RAM utilizzata.

## P3 — Collegamenti Core

### Heartbeat

- attivo solo mentre SEED è aperto;
- attività reviewable;
- silenzio e cooldown predefiniti;
- stato visibile;
- nessun servizio Windows always-on.

### Tool Builder Da Chat

```text
richiesta naturale
→ specifica tipizzata
→ conferma scope
→ generazione isolata
→ audit
→ test
→ design review
→ proposta installazione
→ approvazione owner
```

Il builder non puo installare, approvare o promuovere cio che genera. Una
authority indipendente puo auto-attivare una capability verificata soltanto
entro autorita gia concesse; nuove autorita e azioni irreversibili richiedono
sempre consenso esplicito. La specifica completa della policy futura e in P7.

### Apprendimento Selettivo Delle Capability

Il Tool Builder non e soltanto reattivo alla richiesta in chat e non deve
trasformarsi in un catalogo uguale per tutti. SEED usa salienza, workflow,
frizioni, outcome e correzioni per decidere **cosa conviene imparare e cosa
no** per lo specifico utente.

```text
evidenza specifica dell'utente
-> ipotesi di bisogno
-> confronto con non fare nulla o usare una soluzione piu semplice
-> proposta di capability, tool o integrazione
-> verifica isolata
-> consenso e permessi proporzionati
-> canary e outcome reale
-> mantenimento, correzione, dormienza o rimozione
```

- nessuna lista universale di integrazioni da implementare;
- nessun bridge creato soltanto perche tecnicamente possibile;
- servizi e casi d'uso sono esempi, mai branch hardcoded;
- collegare account o aumentare permessi richiede sempre consenso esplicito;
- due istanze SEED devono poter imparare capability completamente diverse;
- anche `non imparare questa capability` e un esito corretto e auditabile.

### Planner NL → Task Graph

- traduce richiesta reale in grafo tipizzato;
- usa sole capability allowlistate;
- mostra anteprima per azioni con effetti;
- esegue nodi isolati;
- produce status intermedi;
- verifica risultato;
- rollback su errore.

### Canary Reale

Consentito solo per effetti:

- reversibili;
- allowlistati;
- con dry-run;
- con expected observation;
- con rollback verificato;
- approvati dall’utente.

Nel runtime P3/legacy la promotion finale resta sempre owner-gated. La futura P7
potra introdurre attivazione automatica indipendente soltanto entro autorita gia
concesse, dopo evaluator, shadow/canary e subset check deterministico.

## P4 — UI/UX

Implementare:

- logo e icona Windows;
- onboarding visuale completo;
- impostazioni provider e modelli;
- stati coerenti per loading, errore, offline, quota finita e fallback;
- indicatore discreto provider/modello;
- accessibilità P0-P5;
- overlay rifinito;
- linguaggio umano per permessi, recovery e rollback;
- stato installazione e aggiornamento chiaramente visibile.

## P5 — Test E Pilot

### Test Automatici

Coprire:

- onboarding obbligatorio;
- provider/key/model validation;
- fallback verso Ollama Cloud;
- divieto fallback PAYG;
- cifratura credenziali;
- migrazione config legacy;
- installer e uninstall;
- aggiornamento, corruzione e rollback;
- caricamento locale di tutti checkpoint ML;
- assenza download runtime;
- tool builder NL;
- planner task graph;
- canary reversibile;
- accessibilità;
- size regression.

### Test Reali

Verificare su almeno tre PC:

- installazione pulita;
- spazio richiesto;
- SmartScreen;
- onboarding Ollama/OpenRouter/Vercel;
- voce ed emotion recognition senza download;
- embedding senza download;
- observation e revoca;
- Docker live;
- crash e recovery;
- aggiornamento;
- migrazione;
- uninstall;
- Defender;
- avvio, RAM e prestazioni.

### Sequenza Pilot

1. Lint e dependency audit.
2. Baseline dimensioni.
3. Provider Hub.
4. Onboarding BYOK.
5. Impostazioni.
6. Installer completo.
7. Aggiornamenti.
8. UI/accessibilità.
9. Collegamenti core.
10. Build optimization.
11. Pilot interno 3 giorni.
12. Correzione blocker.
13. Pilot esterno 14 giorni.
14. Debrief giorno 15.

## P6 - Adaptive Web Rendering

> Fase post-pilot. Non fa parte del gate di distribuzione iniziale P5.
> Specifica completa: [`docs/18_Adaptive_Web_Rendering_Plan.md`](docs/18_Adaptive_Web_Rendering_Plan.md).
> E una dimostrazione profonda dell'apprendimento selettivo, non una feature che
> ogni istanza deve necessariamente attivare.

SEED puo proporre e, solo dopo consenso, aprire una superficie fullscreen
isolata che ripresenta contenuti web secondo preferenze, necessita di
accessibilita o obiettivi dell'utente.

La capability viene proposta soltanto quando emerge fitness per lo specifico
utente. Un'istanza puo evolvere questo renderer; un'altra puo non concepirlo mai
e imparare capability differenti.

La capability deve essere **generativa e aperta**, non una raccolta di temi o
casi hardcoded:

```text
richiesta, preferenza o bisogno confermato
-> acquisizione esplicita della pagina
-> analisi strutturale e sanitizzazione
-> piano di trasformazione tipizzato
-> anteprima fullscreen isolata
-> verifica accessibilita, sicurezza e fedelta del contenuto
-> consenso utente
-> attivazione reversibile oppure scarto
```

Requisiti:

- pannello fullscreen separato con uscita, pausa, confronto con originale e
  ripristino sempre accessibili;
- trasformazioni CSS, layout e DOM governate da un piano tipizzato, con
  motivazione ed evidenza, senza alterare la pagina originale;
- priorita invariabile: sicurezza e controllo P0, accessibilita P1, preferenza
  esplicita P2, estetica P5;
- input pagina solo tramite URL richiesto, HTML fornito o bridge browser
  opt-in; nessuna lettura silenziosa di tab, cookie, sessioni o credenziali;
- sanitizzazione, isolamento script/network, privacy gate, audit locale,
  versionamento e rollback;
- fallback esplicito quando login, DRM, CSP, iframe cross-origin o web app
  complesse impediscono una riproduzione affidabile;
- nessuna promessa di rimuovere perfettamente contenuti indesiderati o
  riprodurre ogni sito senza regressioni;
- test con preferenze e bisogni sintetici differenti, inclusi adattamenti
  estetici, riduzione del rumore e accessibilita, trattati solo come esempi.

## P7 - Selective Capability Forge

> Programma futuro, non implementato e non attivo.
> Specifica completa:
> [`docs/19_Selective_Capability_Forge_Plan.md`](docs/19_Selective_Capability_Forge_Plan.md).

P7 rende operativo il principio fondamentale dell'apprendimento selettivo:
SEED osserva workflow consensuali, formula bisogni, confronta `non fare nulla`,
capability esistenti, MCP, adapter e tool custom, quindi costruisce e valuta
soltanto cio che dimostra fitness per lo specifico utente.

La regola normativa e **mai auto-espansione dell'autorita**:

- builder, reviewer ed evaluator non possono promuovere cio che generano;
- una activation authority indipendente puo auto-attivare una capability
  verificata entro un authority envelope gia concesso;
- nuovi account, scope, dati, destinazioni o tipi di effetto richiedono
  consenso umano in linguaggio naturale;
- azioni irreversibili o ad alto impatto richiedono sempre conferma;
- password e segreti sono discard-only;
- MCP e connettori vengono verificati, isolati, pinnati e messi in quarantena
  su drift.

Fasi previste, tutte gated e una alla volta:

```text
P7.0 contratti e policy
P7.1 local evidence engine
P7.2 need e fitness engine
P7.3 connector discovery e vetting
P7.4 capability builder V2
P7.5 independent evaluator
P7.6 connection broker
P7.7 activation authority e autopilot
P7.8 user experience
P7.9 maintenance e pilot
```

La documentazione di P7 non autorizza la sua implementazione prima
dell'approvazione di P6 o di un override esplicito dell'owner.

## Gate Distribuzione

Non distribuire se presente uno di questi problemi:

- perdita dati;
- key esposta;
- crash non recuperabile;
- update non reversibile;
- checkpoint ML mancante;
- download runtime inatteso;
- onboarding aggirabile senza provider;
- fallback PAYG automatico;
- uninstall cancella dati senza consenso.

Prima dell’implementazione, aggiungere questo programma come nuovo Feature Context Pack in `12_ImplementationPlan.md`. Nessun checkbox viene spuntato automaticamente.
