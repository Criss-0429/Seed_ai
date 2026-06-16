# 01 - Architettura evolutiva

> **Architettura obiettivo.** Il codice v0.2 usa ancora un core immutabile e
> mutazioni periferiche. Questa specifica apre lo spazio candidato all'intero
> software senza rinunciare a valutazione, recupero e controllo.

## Principio

SEED distingue tra:

- **cio che puo essere mutato:** qualunque componente;
- **cio che puo essere attivato:** soltanto un descendant valutato e recuperabile;
- **cio che puo auto-approvarsi:** nulla.

Il confine importante non e core/periferia, ma candidate/active.

## Vista d'insieme

```text
Interaction Surface
  presenza, conversazione, stato, spiegazioni, consenso, rollback
        |
Active Runtime
  versione promossa che interagisce e agisce per l'utente
        |
Evidence & Personal State
  episodi, fatti, ipotesi, preferenze, relazione, esiti, trace
        |
Evolution Lab
  proposta -> descendant -> replay -> eval -> shadow -> canary
        |
Lineage Archive
  parent, diff, build, evidenze, metriche, decisioni, rollback
        |
Stable Boot Supervisor
  avvio, health check, selezione versione, recovery indipendente
```

Tutti i piani sono potenzialmente oggetto di mutazione. Il supervisor, gli
evaluator e il lineage hanno un gate piu severo perche controllano l'integrita
del processo evolutivo.

## 1. Interaction Surface

Responsabilita:

- esperienza iniziale ispirata alla semplicita relazionale di *Her*;
- ack immediato, stato durante il lavoro e risultato finale;
- conversazione testuale e voce opzionale;
- superfici secondarie per profilo, lineage, permessi e privacy;
- confronto a coppie tra varianti;
- spiegazione e rollback accessibili.

La superficie puo essere completamente ridisegnata da un descendant. Una
variante UI deve comunque preservare accesso verificabile a pausa, permessi,
spiegazioni e recovery.

## 2. Active Runtime

E la versione attualmente promossa. Include:

- orchestrazione conversazionale;
- command router e workflow;
- online research lane con adapter provider-neutral, provenance e citazioni;
- persona e modalita contestuali;
- capability e tool;
- memoria e retrieval;
- privacy e permission broker;
- watcher e sensori consensuali;
- client modello e provider;
- telemetria locale.

La ricerca online e una capability remota governata, non conoscenza implicita
del modello. Exa e Tavily sono provider iniziali candidati; query e contenuti
passano da privacy gate, contratti tipizzati, limiti di costo e controlli contro
prompt injection. Ogni risposta basata sul web deve mantenere URL/provenance e
distinguere chiaramente fonti recuperate da inferenze del modello.

Qualunque elemento puo essere candidato a mutazione, compresi privacy, permessi
e core. Le modifiche ad alto impatto non vengono negate a priori: richiedono
evaluator indipendenti, owner gate e recovery provato.

### Model roles e design governor

SEED separa almeno tre ruoli modello:

- conversazione e sintesi;
- costruzione isolata di tool/descendant;
- review read-only contro direttive di design versionate.

Separare modelli non basta: devono restare separate anche le autorita. Il coder
non promuove; il reviewer non modifica, approva o promuove; test deterministici,
evaluator, promotion authority e owner gate restano decisivi. Configurazione,
selezione e piano voice sono definiti in `13_ModelRoles_Voice_Plan.md`.

## 3. Evidence & Personal State

Lo stato personale separa:

- eventi ed episodi grezzi;
- fatti espliciti;
- preferenze esplicite;
- pattern osservati;
- ipotesi e controevidenze;
- storia della relazione;
- self-narrative di SEED;
- esiti delle azioni e delle mutazioni.

Ogni elemento mantiene provenance, confidenza, ambito e validita temporale. Il
profilo utilizzato in conversazione viene rigenerato dal substrato, non
accumulato come testo incontrollato. Vedi
[Personalita compatibile](09_Personalita_Compatibile.md) e la wiki
[User Knowledge Ontology](../../JarvisDocs/LLM_Wiki/wiki/Jarvis_User_Knowledge_Ontology.md).

## 4. Evolution Lab

Ambiente separato dal runtime attivo in cui SEED:

1. formula problemi e opportunita da evidenze;
2. genera uno o piu descendant;
3. costruisce artefatti riproducibili;
4. esegue controlli statici, contrattuali e invarianti;
5. esegue replay su trace personali redatte;
6. confronta varianti su piu obiettivi;
7. conduce shadow e canary;
8. propone promozione, iterazione, archivio o rollback.

Il lab non dispone implicitamente di tutte le credenziali o i dati del runtime
attivo. Accessi e permessi dipendono dal piano di valutazione.

## 5. Lineage Archive

Il lineage e un albero o DAG append-only che rende ricostruibile l'evoluzione:

```text
versione parent
  -> mutation candidate
  -> descendant/build
  -> evaluator e risultati
  -> decisione
  -> canary
  -> promozione oppure rollback
```

Conserva anche varianti non promosse e rollback. Una mutazione fallita e
evidenza utile, non un record da cancellare.

## 6. Stable Boot Supervisor

Il supervisor e una membrana evolutiva minima esterna alla versione attiva.
Responsabilita:

- avviare una versione per identificatore;
- verificare un health check indipendente;
- applicare timeout e fallback;
- mantenere almeno una versione nota funzionante;
- offrire recovery manuale;
- proteggere l'integrita minima del lineage.

Il supervisor non definisce cosa SEED puo diventare. Esiste per evitare che una
mutazione elimini l'unico percorso con cui SEED puo tornare operativo.

Una mutazione del supervisor e ammessa, ma non puo auto-promuoversi e deve
essere validata da un percorso di recovery indipendente.

## Flusso di una richiesta

```text
input utente
-> privacy e selezione contesto
-> interpretazione deterministica dove possibile
-> ragionamento/modello dove utile
-> action contract
-> permission broker
-> esecuzione osservabile
-> risposta e stato
-> trace, outcome e candidati memoria
-> eventuale trigger evolutivo
```

Il principio della wiki
[Agent Harness Best Practices](../../JarvisDocs/LLM_Wiki/wiki/Agent_Harness_Best_Practices.md)
resta valido: determinismo prima del modello per azioni note; il modello amplia,
propone e interpreta, ma gli effetti passano da contratti osservabili.

## Flusso di una mutazione

```text
evidenza
-> ipotesi
-> candidate
-> descendant isolato
-> evaluator indipendenti
-> shadow/canary
-> promotion authority
-> active runtime
-> outcome reale
-> lineage
```

I requisiti normativi sono definiti in `11_Contratto_Mutazione.md`.

## Trust zone

```text
Zona A - personale locale
  memoria, profilo, relazione, trace, lineage, credenziali

Zona B - lab isolato
  descendant, fixture redatte, evaluator, build e test

Zona C - provider remoto
  solo payload redatti e minimi necessari

Zona D - export
  solo su azione esplicita dell'utente
```

Il fatto che una mutazione sia potente non amplia automaticamente la sua trust
zone. Ogni variazione deve apparire in `permissions_delta`.

## Invarianti di sistema

- l'utente puo sempre interrompere e recuperare;
- nessuna versione attiva e l'unica copia recuperabile;
- nessuna proposta auto-certifica il proprio successo;
- il lineage registra parent, evidenze, valutazione e decisione;
- fatti, ipotesi e segnali affettivi restano distinti;
- gli effetti reali passano da action contract e permessi;
- privacy, permessi ed evaluator sono mutabili solo con verifica indipendente;
- la personalita mantiene capacita di dissenso.
