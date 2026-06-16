# 05 - Activity Watcher

> Il watcher produce segnali contestuali consensuali. Non osserva la persona
> "per scoprire chi e": fornisce evidenze limitate su workflow e contesto.

## Scope corrente

| Segnale | Metodo corrente | Frequenza indicativa |
|---|---|---|
| Processo in foreground | Windows user32 | 5 s |
| Titolo finestra attiva | `GetWindowTextW` | 5 s |
| Processi rilevanti | `psutil` filtrato | 60 s |
| Sessione media | Windows media controls o euristica | 30 s |
| Idle | `GetLastInputInfo` | continuo |

Il runtime v0.2 non acquisisce screenshot, keylogging, clipboard, traffico di
rete, URL, audio ambientale o microfono passivo.

## Pipeline

```text
sample raw in memoria
-> sessionizzazione
-> categorizzazione locale
-> privacy gate
-> episodio redatto
-> aggregazione
-> eventuale evidence_ref per una ipotesi o mutazione
```

Titoli grezzi non vengono persistiti. Il lineage deve referenziare episodi e
aggregati, non duplicare contenuti personali.

## Limiti inferenziali

Un segnale del watcher puo sostenere ipotesi come:

- "questo workflow ricorre";
- "questo orario sembra inadatto alle interruzioni";
- "questa capability potrebbe ridurre una frizione";
- "questa app e spesso associata a un certo contesto".

Non puo da solo sostenere conclusioni come:

- "l'utente e introverso";
- "l'utente e stressato";
- "questa e una preferenza stabile";
- "questa assenza significa disinteresse";
- "questa attivita autorizza una nuova azione".

Pattern non e diagnosi; assenza non e rifiuto; correlazione non e intenzione.
Queste regole derivano dalla wiki
[User Knowledge Ontology](../../JarvisDocs/LLM_Wiki/wiki/Jarvis_User_Knowledge_Ontology.md).

## Controlli utente

- pausa sempre accessibile;
- blocklist di app e categorie;
- visualizzazione e cancellazione selettiva;
- esclusione dei dati dall'evoluzione;
- indicatore chiaro quando il watcher e attivo;
- consenso separato per qualunque futuro sensore.

La pausa registra soltanto che il watcher era inattivo, non una supposizione sul
motivo.

## Uso nell'evoluzione

Il watcher puo attivare un problema o una opportunita, non promuovere una
soluzione. Esempi:

- ricorrenza di un workflow -> candidate capability o automazione;
- molte correzioni nello stesso contesto -> candidate di routing;
- co-occorrenze -> ipotesi su timing o non-interruzione;
- riduzione di un'attivita -> richiesta di chiarimento, non pruning automatico.

Ogni candidate conserva evidenze, controevidenze, previsione e finestra di
valutazione. Un singolo evento non modifica la personalita stabile.

## Evoluzione del watcher

Il watcher stesso puo essere mutato. Nuovi sensori o maggiore granularita
richiedono:

- scopo e beneficio dichiarati;
- nuovo consenso;
- minimizzazione e retention;
- evaluator privacy;
- canary;
- possibilita di esclusione e rollback.

Una mutazione non puo attivare osservazione aggiuntiva in background soltanto
per migliorare la propria valutazione.

### Direzione media locale

Il runtime corrente riconosce app media dedicate, ma non distingue in modo
affidabile YouTube o Netflix dentro un browser. Direzione prevista:

- usare solo metadati locali consensuali (app/domain coarse o Windows media
  session), senza scraping account, cronologia remota o contenuti privati;
- salvare un segnale come osservazione a bassa confidenza, non come preferenza;
- alla sessione successiva, K4 puo decidere se chiedere una conferma breve
  ("hai guardato/ascoltato qualcosa che vuoi ricordare?") oppure tacere;
- promozione a conoscenza utente solo dopo conferma o ricorrenza calibrata;
- blocklist, pausa, cancellazione e audit restano obbligatori.
