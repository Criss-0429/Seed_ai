# 08 — Piano test Windows (per Cristian, 2026-06-11)

> Scritto a fine sessione autonoma 2026-06-10 sera. Stato: v0.2,
> 44 test verdi + 8 integration test OPF pronti (auto-skip senza modello).
>
> **Ambito:** questo piano verifica esclusivamente il runtime v0.2 corrente.
> Non valida ancora onboarding conversazionale, personalità compatibile,
> descendant completi eseguibili, canary con effetti reali, UI target o
> supervisor descritti nei documenti `00`, `01`, `02`, `09` e `11`.

## Stato S5.5 - acceptance pratica core

- aggiunto runner isolato `seed/core/acceptance.py`;
- aggiunta CLI `scripts/core_acceptance.py`;
- creati dati finti: 3 episodi, 2 preferenze, 2 eventi, 2 observation shadow e
  2 observation canary;
- eseguiti build, evaluator, shadow, canary contestuale, promotion, riapertura,
  rollback e tamper detection;
- report persistito:
  `C:\tmp\seed-core-acceptance-20260611-s55-final\core_acceptance_report.json`;
- risultato: `status=passed`, 12/12 check pass;
- suite completa: `98 passed, 1 skipped`;
- skip residuo confermato: `OpenAI Privacy Filter non installato`;
- rebuild PyInstaller pulita riuscita;
- smoke `SEED.exe`: finestra presente e responsive, nessun dialog crash, nessun
  processo `SEED` residuo dopo chiusura;
- nessun dato reale, provider, rete o UI usato.

## Cosa deve testare Cristian adesso

### A. Privacy Filter reale - necessario prima del pilot

```powershell
cd C:\Users\Cristian\Documents\Progetti\JARVIS
.\.venv\Scripts\python.exe -m pip install git+https://github.com/openai/privacy-filter
.\.venv\Scripts\python.exe -m pytest FrameworkUtenti\seed\tests\test_opf_integration.py -v -rs
```

Controllare:

- gli 8 casi vengono eseguiti, non saltati;
- nomi, email, telefono, IBAN e API key non sopravvivono alla redazione;
- stesso nome produce placeholder stabile;
- rehydrate restituisce il nome solo localmente;
- testo pulito resta comprensibile.

### B. Conversazione e reflection con provider reale - necessario

Usare una cartella dati temporanea, senza contaminare l'istanza SEED normale:

```powershell
cd C:\Users\Cristian\Documents\Progetti\JARVIS\FrameworkUtenti\seed
$manualRoot = Join-Path $env:TEMP ("seed-manual-" + [guid]::NewGuid())
$manualConfig = Join-Path $env:TEMP ("seed-manual-config-" + [guid]::NewGuid() + ".json")
Copy-Item .\config\config.example.json $manualConfig
notepad $manualConfig
$env:LOCALAPPDATA = $manualRoot
$env:SEED_CONFIG = $manualConfig
..\..\.venv\Scripts\python.exe run_dev.py --repl
```

Nel file aperto da Notepad compilare provider, key e modelli; il file resta
temporaneo fuori repo. Usare solo contenuto finto durante questo test. Provare:

1. `che ore sono`
2. 10-15 messaggi conversazionali finti con preferenze e correzioni
3. `:reflect`
4. `:report`
5. `:q`

Controllare:

- comando ora risponde localmente;
- conversazione provider funziona senza mostrare key o PII;
- correzioni e preferenze restano coerenti nei turni successivi;
- `:reflect` non cambia silenziosamente lo stato attivo;
- candidate/descendant/evaluation sono ricostruibili sotto
  `$manualRoot\SEED\lineage` e `$manualRoot\SEED\lab`;
- nessuna candidate diventa `promoted` automaticamente;
- `:report` e leggibile e non contiene testo personale raw o segreti;
- nessun crash, freeze o errore non gestito.

Se reflection non genera una candidate, non e automaticamente un errore: puo
significare evidenza insufficiente. E errore se applica direttamente una
mutazione, promuove senza gate, perde dati o espone segreti.

### C. Giudizio umano breve - necessario

Dopo 20-30 minuti di uso con dati finti, annotare:

- risposte utili o inutili;
- comportamenti imprevedibili;
- correzioni ignorate;
- eventuale eccesso di compiacenza/mirroring;
- chiarezza del report e delle proposte;
- qualunque modifica percepita senza spiegazione.

Boot crash/fallback e recovery known-good non vanno testati ora: appartengono a
S6 Stable Boot Supervisor.

## Esito test manuale reale 2026-06-11

- Ollama Cloud autenticato; modello disponibile verificato: `gemma4:31b`.
- OPF reale: `8 passed`.
- Conversazione reale: risposte brevi rispettate e dissenso motivato presente.
- Bug trovati dal test:
  - preferenza esplicita non persistita;
  - recall preferenze classificato come note;
  - JSON reflection fenced rifiutato;
  - `:::report` trattato come messaggio.
- Bug corretti e verificati.
- Replay reale post-fix:
  - preferenza salvata: pass;
  - recall locale: pass;
  - reflection parse: pass;
  - candidate valida in shadow: pass;
  - proposta persona invalida bloccata: pass;
  - lineage integro: pass;
  - zero promotion automatica: pass.
- Suite corrente: `111 passed`, zero skip.
- Acceptance pratica sintetica: 12/12 pass.
- Build e smoke `SEED.exe`: pass.
- Non serve altro test manuale per S5.5. Personalita completa e boot recovery
  restano rispettivamente S8 e S6.

## Evidenza S6 - Stable Boot Supervisor, 2026-06-12

- aggiunti `seed/supervisor.py`, `seed/supervisor_cli.py`,
  `supervisor_entry.py`, `scripts/supervisor_probe.py` e
  `build/supervisor.spec`;
- `SEEDSupervisor.exe` e separato dal runtime attivo;
- pointer/versione/JSON/lineage vengono validati prima del launch;
- health signal emesso solo dopo inizializzazione `SeedApp`, autenticato con
  token casuale e rimosso dopo verifica;
- timeout, exit precoce e token errato producono boot unhealthy;
- known-good viene scritta solo dopo health riuscito ed e vincolata all'hash
  completo dello snapshot;
- boot unhealthy ripristina la known-good e ritenta una sola volta;
- recovery manuale e restore con errore ripristinano stato/pointer precedente;
- log supervisor append-only verificati;
- JSON UTF-8 con BOM Windows e root relative normalizzate verificati;
- CLI su root non inizializzabile restituisce errore JSON, senza traceback;
- probe subprocess reale: pass;
- smoke reale `SEEDSupervisor.exe -> SEED.exe`: `status=healthy`,
  `health signal verified`, finestra `SEED` responsive;
- `known_good.json`, `boot_started` e `boot_healthy` persistiti correttamente;
- processi creati dallo smoke chiusi;
- suite finale: `134 passed`, zero skip, inclusi 8 OPF reali;
- build pulite `SEED.exe` e `SEEDSupervisor.exe`: pass.

Non serve test manuale utente per il gate tecnico S6. Prima di distribuire un
pilot va comunque deciso come installer/shortcut invochera sempre il supervisor
invece di permettere il doppio click diretto su `SEED.exe`.

## Evidenza build 2026-06-11

- virtual environment verificato: `.venv\Scripts\python.exe` risponde con
  `Python 3.14.4`;
- installate nel venv le dipendenze build/runtime mancanti:
  `requests`, `psutil`, `pywebview`, `pyinstaller`;
- build PyInstaller completata;
- artefatto creato: `FrameworkUtenti\seed\dist\SEED.exe`;
- primo smoke basato solo su processo vivo risultato insufficiente: il dialog
  PyInstaller "attempted relative import with no known parent package" manteneva
  vivo il processo;
- causa corretta: lo spec eseguiva `seed/__main__.py` come script sciolto;
- nuovo entrypoint `build_entry.py` importa `seed.__main__` come package;
- smoke valido deve verificare anche il titolo finestra `SEED` e l'assenza di
  dialog `Unhandled exception in script`;
- rebuild pulita completata;
- smoke valido: finestra `SEED` presente, responsive; nessun dialog
  `Unhandled exception`; launcher e processo app chiusi dopo il test;
- suite SEED: `56 passed, 1 skipped`.

### Evidenza S2

- rebuild PyInstaller pulita riuscita dopo migrazione reflection;
- smoke EXE riuscito: finestra `SEED` responsive e nessun crash;
- suite SEED: `59 passed, 1 skipped`;
- reflection mock verificato proposal-only: UI invariata, candidate nel lineage,
  evaluation `inconclusive`, nessuna auto-promozione.

### Evidenza S3

- suite SEED: `72 passed, 1 skipped`;
- rebuild PyInstaller pulita riuscita con il descendant builder incluso;
- smoke EXE riuscito: finestra `SEED` presente, processi responsive, nessun
  dialog `Unhandled exception`;
- processi creati dallo smoke chiusi; nessun processo `SEED` residuo;
- discendenti verificati isolati sotto `lab/descendants/<mutation_id>`,
  riproducibili e non eseguibili/non attivi;
- verificati hash manifest, rilevamento tampering, blocco path traversal e
  rifiuto del candidate quando la build fallisce;
- nessuna attivazione o esecuzione di codice discendente appartiene a S3.

### Evidenza S4

- suite SEED: `83 passed, 1 skipped`;
- rebuild PyInstaller pulita riuscita con replay/evaluator incluso;
- smoke EXE riuscito: finestra `SEED` presente, processi responsive, nessun
  dialog `Unhandled exception`;
- evaluator verificato indipendente dal descendant, deterministico e senza
  chiamate LLM/provider;
- UI state-based produce `pass` e resta `validating`; capability generate
  restano `inconclusive` e non vengono eseguite;
- verificati fail/reject per permission mismatch e replay regressivo;
- errore del corpus replay dopo build produce `evaluation_failed` e candidate
  `rejected`, senza restare bloccata in `validating`;
- verificati blocchi su fixture non redatte/segreti, tampering lineage,
  descendant e report;
- nessuna transizione shadow, canary o promoted appartiene a S4.

### Evidenza S5

- suite SEED: `96 passed, 1 skipped`;
- rebuild PyInstaller pulita riuscita con promotion core incluso;
- smoke EXE riuscito: finestra `SEED` presente, processi responsive, nessun
  dialog `Unhandled exception`;
- promotion authority separata da generator, builder ed evaluator;
- evaluation `pass` apre solo shadow senza effetti;
- canary lease verificata per context id e scadenza, senza activation globale;
- promotion diretta e `shadow -> promoted` bloccate;
- promotion state-based verificata con stale-parent check, active pointer,
  versione recuperabile e reload registry;
- rollback manuale e rollback automatico su activation failure verificati;
- rollback failure ripristina stato promosso e pointer coerente;
- UI/personality, capability generate e core completi restano non-promovibili;
- nessun file UI modificato.

Il doppio click diretto su `python.exe` non e un test valido: l'interprete apre
una console e termina quando non riceve uno script. Per l'app usare `SEED.exe`;
per sviluppo usare `python run_dev.py` da PowerShell.

## Cosa ho verificato stanotte (e cosa no)

| Verificato in sandbox Linux | Esito |
|---|---|
| Suite completa core + router | 44/44 verdi |
| `opf` (Privacy Filter) installato REALE, torch 2.12 funzionante | import ok |
| **Contratto adapter**: `RedactionResult`/`DetectedSpan` veri → `_detect_opf` → pseudonimi `[PERSON_1]` → rehydrate | ok |
| Doppio layer in serie (modello + regex) su frase con nome+email | ok |
| Fail-safe: checkpoint non disponibile → `init_opf()=False`, layer regex protegge comunque | ok |

**Non verificato**: l'inferenza vera del modello. HuggingFace e' nella blocklist
di rete della sandbox: il checkpoint non e' scaricabile da qui. Il TUO test di
domani e' esattamente questo pezzo.

## Test 1 — Privacy Filter reale (10 min)

```powershell
cd FrameworkUtenti\seed
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
pip install git+https://github.com/openai/privacy-filter
# prova CLI immediata (scarica il checkpoint al primo uso, qualche minuto):
opf --device cpu "Mi chiamo Cristian La Porta, mail cristian.laporta04@gmail.com"
# poi gli 8 integration test (passano da skip a run automaticamente):
pytest tests/test_opf_integration.py -v
```

Se gli 8 test passano, il privacy gate e' chiuso e validato end-to-end.
Se qualcuno fallisce su nomi italiani: e' il limite "primarily English" del
model card — il layer regex copre comunque email/CF/IBAN/telefoni; valuteremo
il fine-tuning (`opf train`) o pattern aggiuntivi.

## Test 2 — App in REPL senza UI (5 min)

```powershell
copy config\config.example.json config\config.json
# compila: llm.base_url + llm.api_key + llm.model_runtime + llm.model_reflection
python run_dev.py --repl
```

Da provare in ordine:
1. `che ore sono` → risposta locale instantanea, ZERO chiamate API (router seed)
2. `dimmi che ora fa` → 1 chiamata LLM (normalizzatore) → risposta; ripetila →
   stavolta zero chiamate (alias appreso). Verifica in `%LOCALAPPDATA%\SEED\data\traces\`
   il campo `"source": "alias"`.
3. `apri spotify` → dialog permesso in console → apre l'app
4. una frase conversazionale → flusso LLM normale
5. `:reflect` → forza il reflection pass (serve la key) → guarda il digest
6. `:report` → esporta il report aggregato

## Test 3 — UI webview (5 min)

```powershell
python run_dev.py
```

Punti delicati segnalati (li ho scritti, mai eseguiti su Windows):
- dialog permessi via `evaluate_js`+Promise (`ui/shell.py::_ask_permission`)
- watcher: titoli finestre redatti, toggle pausa in header
- banner digest col bottone Ripristina

## Test 4 — Build exe (quando i primi 3 passano)

```powershell
pip install pyinstaller
pyinstaller build/seed.spec    # → dist/SEED.exe
```

## Nota pulizia

In `outputs/pylibs` della sessione cowork ci sono ~4GB di torch+CUDA che ho
installato per i test di contratto in sandbox. Se non ti servono altri miei
test con torch, cancella pure la cartella.
