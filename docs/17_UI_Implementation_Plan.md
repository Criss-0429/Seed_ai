# 17 - UI Implementation Plan (da SEED_UI)

> **Stato (2026-06-13, UI Integration Hardening):** U0-U7 (incl. S11.3 in U3)
> **implementate e pronte per review owner**. `seed/ui/surface/index.html` e' la
> **riproduzione fedele del
> design `SEED Prototype.dc.html` (+ Brand)** — palette oklch, DM Sans/DM Mono,
> orb seme+anelli, conversazione, superfici Modello Utente/Permessi, voice
> overlay, toast — **reimplementata in JS vanilla** perche' il prototipo usa
> runtime DC/React via CDN + `window.claude` (non offline): l'app resta
> **Python/pywebview con build EXE**, la chat passa dal backend `JsApi`. U7
> `ui_governance` (P0-P5 + ui_directives nel DesignDirectivePack). Suite
> `443 passed`. **Nessun checkbox spuntato**; smoke owner su EXE + maturazione
> brand reale restano owner. Design autorevole in `SEED_UI/`.

## Sorgenti di design (autorevoli)

`SEED_UI/`:

- **`SEED Design Guidelines.dc.html`** — regole UI/UX (Laws of UX A-01..A-10,
  euristiche Nielsen B-*, gerarchia di precedenza P0-P5). Scritte esplicitamente
  per DUE lettori: l'utente E SEED stesso. **Ogni mutazione UI generata dai
  modelli deve consultarle, citarle e dichiarare ogni deroga.**
- **`SEED Brand Identity.dc.html`** — marchio (seme + anelli di crescita),
  palette (acromatico -> colore guadagnato con la relazione, hue dell'utente),
  motion (respiro, ≥1.2s, interrompibile <100ms, reduce-motion), tipografia
  (due voci: parlato vs sistema).
- **`SEED Wireframes.dc.html`** — 4 modalita': A presenza pura, B colonna
  conversazione, C scena divisa, D overlay-first.
- **`SEED Prototype.dc.html`** + **`support.js`** — prototipo interattivo: orb +
  stati, superfici (Modello Utente, Permessi e Privacy), modalita' voce.

## Governance: le regole UI guidano i modelli (richiesta esplicita)

Le Design Guidelines diventano **direttive del design reviewer** (S10). Concreto:

- estendere il `DesignDirectivePack` (S10.2) con una sezione `ui_directives`
  derivata dalle Guidelines: gerarchia P0-P5 + Laws of UX + euristiche;
- il `design_reviewer` (S10.3) valuta ogni mutazione che tocca UI/`ui_manifest`
  contro queste direttive; una mutazione che viola P0 (controllo/sicurezza) o P1
  (accessibilita') **non e' candidabile**; una che contraddice P4 deve dichiarare
  l'evidenza P2-P3 che la giustifica;
- cosi' i modelli (conversation/tool_builder) che propongono cambi UI seguono
  regole di UI/UX verificabili, non estetica arbitraria.

### Gerarchia di precedenza (P0-P5, non negoziabile)

P0 controllo/sicurezza utente · P1 accessibilita' · P2 correzione/preferenza
esplicita recente · P3 esito comportamentale ripetuto · P4 best practice ·
P5 estetica. P0-P1 mai derogabili.

## Vincoli trasversali (da Guidelines/Brand)

- **Ack < 400ms sempre** (Doherty A-05): l'orb cambia stato e dice "ricevuto",
  mai silenzio durante il lavoro. Si aggancia all'ack gia' previsto in AGENTS.
- **Stato sempre visibile** (Nielsen B-01): risveglio / ascolto / pensiero /
  azione / ritorno percepibili nell'orb in ogni dimensione.
- **Una sola enfasi per superficie** (Von Restorff A-08); poche azioni a vista
  (Hick A-02); convenzioni note (Jakob A-03: input in basso, Esc chiude, invio
  invia).
- **Accessibilita' P1**: hit target ≥24px (44px touch), contrasto, focus,
  reduce-motion (niente loop, stati distinti per opacita').
- **Colore guadagnato**: chroma cresce con eventi reali della relazione
  (correzioni, mutazioni promosse), regredisce dopo rollback; hue fissata in
  onboarding.
- **Motion = respiro**, mai spettacolo; l'evoluzione si annuncia a parole.

## Stato attuale

`seed/ui/shell.py` (pywebview) + `seed/ui/surface/index.html` offline e reattiva.
`ui_manifest.json` e' lo stato UI mutabile (persona/greeting) gia' governato da
descendant/evaluator (S3/S4). La UI ricca derivata da SEED_UI vive qui senza
rompere il contratto state-based.

### Evidenza UI Integration Hardening (2026-06-13)

- rimossi Google Fonts e ogni URL/asset remoto: la surface UI e' 100% offline,
  con stack tipografico locale;
- corretto il doppio focus arancione: l'input usa il focus del contenitore,
  mentre controlli e tastiera mantengono focus visibile;
- boot UI collegato allo stato onboarding reale: primo avvio mostra il prompt
  della state machine, profilo gia' inizializzato mostra il greeting;
- U3 collegata al backend voce reale: MediaRecorder -> bridge base64 ->
  `SeedApp.voice_message()` (STT/emotion/chat) -> `voice_reply_audio()` (TTS),
  sempre dietro consenso esplicito e senza persistenza audio;
- U5 presenza pura e U6 overlay-first sono modalita' finestra reali pywebview;
  `Ctrl+Spazio` e' registrato globalmente su Windows; l'overlay cresce a presenza
  quando parte una richiesta;
- superficie Evoluzione operativa: digest, versioni recuperabili e rollback
  esplicito; nessuna promotion automatica;
- Guidelines A-01..A-10, B-01..B-10, C-01..C-06, D-01..D-12, E-01..E-05 +
  Brand codificate in `ui_governance`; i pack UI le includono automaticamente;
  candidate UI reali producono review evidence e il gate deterministico P0/P1/P4
  puo' bloccare lo shadow senza dare promotion authority al reviewer LLM.
- verifica: `443 passed`, acceptance core `12/12`, `compileall` e sintassi JS
  ok; `dist/SEED.exe` e `dist/SEEDSupervisor.exe` ricostruiti.

### Limiti reali ancora aperti

- smoke owner necessario per microfono/permesso WebView, ElevenLabs STT/TTS e
  hotkey globale nell'EXE;
- hue e chroma sono ora aggiornati deterministicamente dal core sulla base di
  identita' onboarding e conteggi di eventi locali confermati; non dipendono da
  impressioni arbitrarie dell'LLM e restano reversibili via manifest/versioni;
- observation context-aware resta OFF e permission-gated finche' l'utente non
  abilita le singole classi; il collector non legge titoli, URL o contenuti;
- nessun gateway esterno: per decisione owner, SEED resta dentro `SEED.exe`.

## Decisione modalita'

Base **B (colonna conversazione)** come default — pattern noto, cronologia
leggibile, "matura meglio con piccole mutazioni" (Wireframes). **A (presenza
pura)** e **modalita' voce** come toggle. **D (overlay-first)** opzionale come
complemento di sistema (Ctrl+Spazio), legato al permesso di osservazione (doc 16).

## Fasi

| Fase | Scope | Gate |
|---|---|---|
| U0 | Tokens + scaffold: palette/tipografia/motion da Brand come CSS vars; orb component con i 5 stati; reduce-motion | owner |
| U1 | Chat testuale semplice (modalita' B): colonna, input in basso, ack<400ms, stati orb, Esc/invio; **chat scritta resta semplice** | owner |
| U2 | Superfici (Ctrl+.): **Modello Utente** ("cosa penso di sapere di te" — claim K1 con tipo/provenance/dots, "e' vero"/"non e' cosi'" -> correzione/supersession) + **Permessi e Privacy** ("cosa posso osservare", esporta/cancella tutto) | owner |
| U3 | **Pannello chat vocale (= S11.3)**: hold-to-talk STT, orb grande, trascrizione live, TTS espressivo, stato emozione (S11.2) SOLO qui | owner |
| U4 | Maturazione brand: chroma/anelli legati a eventi reali (promotion/rollback), hue onboarding | owner |
| U5 | Modalita' A (presenza pura) come toggle; testo effimero opzionale | owner |
| U6 | Overlay-first D (Ctrl+Spazio, context-aware) — solo con permesso osservazione attivo (doc 16) | owner |
| U7 | Integrazione governance: `ui_directives` nel DesignDirectivePack; reviewer valuta mutazioni UI contro P0-P5 | owner |

## Acceptance minima

- ack <400ms e stato orb sempre visibile;
- chat scritta semplice (solo chat; hold-key STT, TTS dopo risposta);
- superficie Modello Utente mostra i claim con provenance e permette correzione
  che esegue supersession (K1/M2); le ipotesi non diventano fatti;
- superficie Permessi mostra cosa SEED osserva + esporta/cancella;
- reduce-motion rispettato; hit target ≥24px; focus/contrasto P1;
- una mutazione UI che viola P0/P1 e' bloccata dal reviewer;
- nessuna regressione del contratto `ui_manifest` state-based.

## Non-goals

- reinventare convenzioni note senza evidenza P2-P3 dichiarata;
- colore/anelli piu' maturi della relazione reale;
- avatar/volto/personaggio (il marchio e' presenza, non personaggio);
- spostare logica provider/segreti nella UI.

## Fonti

`SEED_UI/*`, `09_Personalita_Compatibile.md`,
`00_Visione_Prodotto.md`, AGENTS.md (conversation-first: ack/status/final).

## Pass distribuzione P4 - 2026-06-14

La surface distribuita completa la base U0-U7 con brand locale, onboarding
visuale, stati operativi accessibili, indicatore provider/modello/fallback e
stato installazione/update/recovery. Permission e rollback usano copy piu
umano senza cambiare i gate esistenti.

Verifica automatica: test mirati `40 passed`, suite completa `496 passed`,
acceptance core `12/12`, Ruff, compileall e sintassi JavaScript verdi. La review
visuale owner nell'EXE e la resa finale dell'icona installata restano aperte; il
browser integrato ha bloccato lo smoke locale per policy.
