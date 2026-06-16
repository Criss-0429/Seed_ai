# 11 - Contratto normativo di mutazione, valutazione e promozione

> **Stato:** specifica normativa dell'architettura obiettivo.
> Le parole **DEVE**, **NON DEVE**, **PUO** indicano requisiti vincolanti,
> divieti e possibilita.

## Concetti

- **Mutation candidate:** proposta di cambiamento, senza autorita sul runtime attivo.
- **Descendant:** versione eseguibile isolata derivata da una versione parent.
- **Lineage archive:** albero o DAG di versioni, mutazioni, evidenze e valutazioni.
- **Evaluator:** componente o procedura che misura una variante.
- **Promotion:** decisione che rende una variante attiva, totalmente o in canary.
- **Authority envelope:** descrizione tipizzata di account, dati, effetti,
  scope, destinazioni, schedule, limiti e durata gia autorizzati.
- **Capability activation authority:** autorita indipendente che puo attivare
  una capability verificata soltanto entro un authority envelope esistente.
- **Rollback:** ritorno verificato a una versione nota.
- **Stable boot supervisor:** meccanismo esterno minimo capace di avviare,
  controllare salute e ripristinare una versione. Non limita cio che SEED puo
  proporre; impedisce che un candidato distrugga l'unico percorso di recupero.

## Separazione delle autorita

1. Il generatore di una mutazione **NON DEVE** promuovere o auto-certificare la
   propria proposta.
2. Un evaluator modificato dal candidato **NON DEVE** essere l'unica fonte della
   valutazione di quel candidato.
3. Una mutazione del supervisor, degli evaluator, del lineage o del rollback
   **DEVE** essere verificata da una versione indipendente e richiede promozione
   esplicita dell'owner.
4. La versione attiva **NON DEVE** essere sovrascritta in-place prima che esista
   un descendant recuperabile e un rollback provato.
5. Il builder, il reviewer e il connettore di una capability **NON DEVONO**
   decidere la propria attivazione.
6. La capability activation authority **PUO** attivare automaticamente una
   capability soltanto se verifica in modo deterministico che l'autorita
   richiesta e un sottoinsieme di quella gia concessa.
7. Se il confronto di autorita e ambiguo, incompleto o introduce nuovi account,
   dati, scope, destinazioni o effetti, l'attivazione **DEVE** fallire chiusa e
   richiedere consenso.
8. Effetti irreversibili o ad alto impatto **DEVONO** richiedere conferma
   contestuale e non possono essere delegati permanentemente.

## Schema minimo

Ogni candidate **DEVE** contenere:

```json
{
  "mutation_id": "uuid",
  "parent_version": "version-id",
  "created_at": "ISO-8601",
  "reason": "problema o opportunita osservata",
  "evidence_refs": ["trace:...", "preference:...", "evaluation:..."],
  "counterevidence_refs": [],
  "hypothesis": "cambiamento e risultato atteso",
  "target_scope": ["ui", "workflow", "core"],
  "artifacts": ["diff-or-build-reference"],
  "expected_signals": [
    {"metric": "correction_rate", "direction": "decrease", "window": "3d"}
  ],
  "evaluation_plan": ["static", "replay", "shadow", "canary"],
  "risks": ["regression", "privacy", "identity_drift"],
  "permissions_delta": [],
  "rollback_plan": "version-id or procedure",
  "expiry": "ISO-8601 or null",
  "confidence": 0.0,
  "status": "proposed"
}
```

Una proposta priva di evidenza puo essere esplorata, ma **NON PUO** essere
promossa come personalizzazione comprovata.

## Trigger ammessi

I trigger sono descrittivi, non limitanti:

- richiesta esplicita;
- frizione o correzione ripetuta;
- workflow ricorrente;
- fallimento, regressione o rollback;
- capability inutilizzata o ridondante;
- cambiamento di contesto;
- mismatch di personalita;
- opportunita formulata come ipotesi falsificabile.

Il sistema **NON DEVE** mutare soltanto per mostrare attivita o produrre
divergenza.

## Ciclo obbligatorio

```text
osserva
-> formula problema e ipotesi
-> genera uno o piu descendant
-> controlli statici e contrattuali
-> replay personalizzato redatto
-> test generici e invarianti
-> shadow o dry-run
-> confronto multi-obiettivo
-> canary limitato
-> osservazione dell'esito reale
-> promozione, iterazione, rollback o archivio
```

Ogni passaggio **DEVE** lasciare un record nel lineage. I passaggi possono essere
compressi per modifiche a impatto minimo, ma il motivo della compressione deve
essere registrato.

## Classificazione per impatto

Le categorie descrivono il cambiamento senza limitarlo:

- espressione e UI;
- personalita e relazione;
- policy e routing;
- workflow;
- capability e tool;
- memoria e retrieval;
- architettura e core;
- evaluator, supervisor e governance.

L'intensita della valutazione dipende da impatto, irreversibilita, variazione di
permessi e possibilita di recupero. Non esiste un cap universale di mutazioni per
notte: dieci modifiche invisibili e indipendenti possono essere meno
disorientanti di un solo cambiamento identitario.

## Valutazione multi-obiettivo

La promozione **NON DEVE** dipendere da engagement o da un unico score aggregato.
Gli evaluator devono misurare almeno:

- successo e utilita sul compito;
- correzioni e fallimenti;
- fiducia, prevedibilita e controllo percepito;
- continuita della personalita e rischio di mirroring;
- privacy, sicurezza e variazione di permessi;
- latenza, costo e affidabilita;
- capacita di rollback e recupero.

SEED conserva un fronte di varianti promettenti quando esistono trade-off reali,
invece di nasconderli dentro una somma arbitraria. Una variante con beneficio
alto e rischio nuovo non domina automaticamente la versione attiva.

## Promozione

Una variante **PUO** essere promossa solo se:

- il build o l'artefatto e riproducibile;
- gli invarianti pertinenti passano;
- il rollback e disponibile e verificato;
- i permessi aggiuntivi sono dichiarati;
- esiste evidenza a favore rispetto al parent;
- non emergono regressioni bloccanti;
- il livello di consenso richiesto e soddisfatto.

La promozione puo essere:

- **shadow:** osserva senza controllare azioni reali;
- **canary:** attiva per una quota limitata di contesti o tempo;
- **active:** nuova versione principale;
- **experimental opt-in:** attivata esplicitamente dall'utente;
- **owner-gated:** necessaria per supervisor, evaluator, privacy, permessi e
  recupero.

Per capability e tool, una promozione puo inoltre essere:

- **authority-contained:** attivazione indipendente e automatica dopo eval,
  shadow/canary e verifica che `requested_authority` sia sottoinsieme
  dell'authority envelope gia concesso;
- **awaiting-connection:** artefatto verificato ma inattivo finche l'utente non
  collega un account o concede nuova autorita.

`Authority-contained` non autorizza azioni irreversibili o ad alto impatto, non
permette al builder di auto-promuoversi e non sostituisce recovery, audit o
rollback.

## Rollback e recovery

Ogni versione attiva **DEVE** avere:

- parent noto;
- snapshot o artefatto recuperabile;
- health check indipendente;
- timeout di avvio;
- fallback automatico se non raggiunge lo stato sano;
- rollback manuale accessibile all'utente;
- registrazione della causa e suppression temporanea della proposta fallita.

Il rollback non cancella la variante: la conserva nel lineage come evidenza.

## Anti-gaming

Gli evaluator devono essere trattati come superfici attaccabili. Sono richiesti:

- metriche non completamente controllate dal candidato;
- replay nascosti o invarianti indipendenti;
- confronto tra esito dichiarato e osservazione reale;
- rilevazione di riduzione artificiale dei compiti, dei log o delle difficolta;
- owner gate per mutazioni che cambiano come il successo viene misurato.

## Audit minimo

Per ogni versione devono essere ricostruibili:

- origine e parent;
- evidenze usate;
- diff o artefatti;
- evaluator e risultati;
- decisione di promozione;
- permessi e consenso;
- incidenti, rollback e correzioni successive.

Se il lineage non consente questa ricostruzione, la mutazione non e pronta per
la promozione.
