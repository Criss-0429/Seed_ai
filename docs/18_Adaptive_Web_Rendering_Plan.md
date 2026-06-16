# 18 - Adaptive Web Rendering Plan

> **Stato:** capability futura post-pilot, non implementata.
> **Obiettivo:** ripresentare contenuti web in una superficie SEED isolata,
> secondo preferenze e bisogni verificati dell'utente, senza modificare il sito
> originale e senza ridurre controllo, sicurezza o accessibilita.
> **Ruolo nella tesi:** esempio avanzato di capability emergente; non deve
> apparire in ogni istanza SEED.

## Decisione di prodotto

SEED deve poter aprire un pannello fullscreen separato e renderizzare una
rappresentazione adattata di una pagina web. La trasformazione non e una lista
di temi predefiniti: nasce da una richiesta esplicita, una preferenza confermata
o un bisogno di accessibilita, e viene descritta da un piano tipizzato,
verificabile e reversibile.

Adattamento estetico, riduzione del rumore visivo e correzione cromatica sono
esempi di una classe aperta di trasformazioni, non feature hardcoded.

La disponibilita architetturale non implica attivazione universale. Prima di
costruire o proporre il renderer, SEED deve confrontarne il fitness con non fare
nulla, usare il browser originale o creare una soluzione piu semplice. Per un
utente senza evidenza rilevante questa capability puo non essere mai generata.

## Confine realistico

La capability puo trasformare in modo affidabile documenti HTML acquisibili e
contenuti semanticamente leggibili. Non puo garantire equivalenza perfetta per
ogni sito: login, cookie di sessione, DRM, iframe cross-origin, CSP e
applicazioni web fortemente dinamiche possono richiedere un bridge browser
esplicito oppure produrre un fallback leggibile ma non interattivo.

SEED deve dichiarare il livello ottenuto:

- `faithful_interactive`: contenuto e interazioni essenziali preservati;
- `faithful_readonly`: contenuto preservato, interazioni disabilitate;
- `partial`: contenuto incompleto o struttura incerta;
- `blocked`: trasformazione non sicura o non affidabile.

## Pipeline

```text
intent/preference/accessibility need
-> source acquisition with consent
-> parse + semantic inventory
-> sanitize + isolate
-> generate typed transform plan
-> deterministic validation
-> fullscreen preview
-> user compare/approve/reject/correct
-> temporary activation or governed promotion
-> outcome + rollback
```

## Contratti minimi

```text
RenderRequest {
  source_mode, source_ref, user_goal_ref, requested_scope, consent_ref
}

AdaptationProfile {
  constraints, explicit_preferences, accessibility_needs,
  context, provenance, confidence
}

TransformPlan {
  plan_id, target_scope, css_rules, dom_operations, content_filters,
  preserved_semantics, permissions_delta, risks, rollback_plan
}

RenderResult {
  status, fidelity_level, warnings, blocked_resources,
  accessibility_report, preview_ref, audit_ref
}
```

I campi sono contratti, non autorizzazioni. CSS, operazioni DOM e filtri
generati devono attraversare evaluator e gate prima dell'attivazione.

## Acquisizione e privacy

Modalita ammesse:

1. URL richiesto esplicitamente dall'utente;
2. HTML o documento fornito dall'utente;
3. bridge browser opt-in, limitato alla pagina corrente e revocabile.

Default:

- nessuna lettura silenziosa di tab o cronologia;
- nessun accesso implicito a cookie, password, sessioni o storage browser;
- nessun invio automatico dell'HTML completo a provider remoti;
- analisi locale quando possibile; eventuale uso remoto passa dal privacy gate
  con anteprima e minimizzazione;
- contenuto acquisito temporaneo salvo consenso esplicito alla persistenza.

## Isolamento e sicurezza

- sanitizzare HTML e URL prima del rendering;
- disabilitare script e rete per default nella preview;
- consentire risorse o interazioni solo tramite capability specifiche;
- impedire navigazione, download, form submit e side effect non approvati;
- mantenere originale e preview separati;
- mostrare sempre origine, stato di fedelta e trasformazioni applicate;
- offrire uscita immediata, confronto originale/adattato e rollback;
- trattare pagina e istruzioni incorporate come contenuto non affidabile.

## Regole UI e accessibilita

Ordine di autorita:

```text
P0 controllo/sicurezza
> P1 accessibilita
> P2 correzione o preferenza esplicita recente
> P3 esito comportamentale verificato
> P4 best practice
> P5 preferenza estetica
```

Una trasformazione estetica non puo ridurre contrasto, leggibilita, focus,
navigazione tastiera, semantica o accesso ai controlli SEED. Un adattamento
accessibile deve essere configurabile, spiegabile e correggibile; SEED non
deduce condizioni mediche da segnali impliciti.

## Mutazione e promozione

Ogni trasformazione nuova e inizialmente una candidate isolata:

- evidenza o richiesta che la motiva;
- expected signals e rischi;
- test statici, accessibilita e sicurezza;
- preview o shadow;
- confronto con originale;
- approvazione esplicita per uso persistente;
- versione e rollback.

Preferenze temporanee restano temporanee. Una trasformazione non viene
generalizzata ad altri siti o contesti senza evidenza e consenso.

## Acceptance futura

- almeno tre profili sintetici generano piani differenti senza branch
  hardcoded per il singolo esempio;
- originale mai modificato e nessun side effect dalla preview;
- script/rete/cookie/sessioni bloccati per default;
- contenuto principale e provenance visibili;
- stato di fedelta dichiarato e fallback corretto sui casi non supportati;
- controlli fullscreen, uscita, confronto e rollback sempre accessibili;
- scanner sicurezza, test WCAG pertinenti e test contro prompt injection;
- correzione/rifiuto dell'utente influenza il piano successivo senza diventare
  automaticamente una preferenza globale.

## Non-goals iniziali

- sostituire un browser general purpose;
- bypassare paywall, DRM, autenticazione o protezioni del sito;
- garantire ad-blocking perfetto;
- eseguire JavaScript arbitrario della pagina nella trust zone SEED;
- trasformare ogni pagina visitata senza richiesta o consenso;
- diagnosticare bisogni di accessibilita.
