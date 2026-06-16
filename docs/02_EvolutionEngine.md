# 02 - Evolution Engine

> **Decisione SEED:** evoluzione aperta del software, promozione governata.
> Non e fine-tuning dei pesi: il principale spazio di ricerca e il sistema
> eseguibile che circonda il modello.

## Obiettivo

L'Evolution Engine cerca versioni di SEED piu adatte a una specifica relazione e
a specifici contesti. Non deve produrre cambiamenti per forza, massimizzare
engagement o dimostrare creativita. Deve formulare ipotesi verificabili e
produrre descendant che possano battere il parent senza compromettere controllo,
continuita e recuperabilita.

## Spazio delle mutazioni

Le categorie aiutano audit e valutazione, ma non sono una allowlist:

- UI ed espressione;
- personalita e relazione;
- policy, routing e proattivita;
- workflow e command router;
- capability, tool e integrazioni;
- memoria, retrieval e user model;
- provider, modello e strategia di inferenza;
- architettura, core e storage;
- evaluator, lineage, supervisor e governance.

Una mutazione puo aggiungere, rimuovere, fondere, riscrivere o sostituire. Le
mutazioni ad alto impatto richiedono un percorso di promozione piu forte, non un
divieto categorico.

## Origine delle mutazioni

Un candidate nasce da:

- richiesta esplicita;
- frizione o correzione ripetuta;
- workflow ricorrente;
- fallimento o rollback;
- capability inutilizzata;
- cambiamento del contesto;
- mismatch di personalita;
- opportunita espressa come previsione falsificabile.

L'evidenza puo suggerire il bisogno senza prescrivere la soluzione. Per la
stessa frizione il sistema dovrebbe generare varianti diverse, non affidarsi a
una singola intuizione del modello.

## Selezione delle capacita da imparare

L'Evolution Engine non esegue una roadmap universale di feature e non misura il
progresso dal numero di integrazioni disponibili. Decide se **vale la pena
imparare qualcosa** per quella specifica relazione.

```text
segnali ed esiti osservati
-> bisogno o opportunita ipotizzata
-> confronto con alternative piu semplici, incluso non fare nulla
-> stima di utilita, frequenza, costo, rischio e manutenzione
-> candidate specifica
-> verifica e proposta all'utente
-> apprendimento, iterazione, dormienza oppure scarto
```

Esempio non normativo: una persona che usa intensamente email e pianificazione
potrebbe ricevere una proposta per un recap o un bridge calendario; un'altra
istanza potrebbe non concepire mai quelle capability e investire invece in
strumenti completamente diversi. Il nome del servizio non e il requisito: lo e
il fitness dimostrabile per l'utente.

Una preferenza o un pattern non basta da solo ad autorizzare effetti o accessi.
La decisione di imparare e distinta dal consenso necessario per collegare
account, leggere dati, eseguire azioni o rendere persistente una capability.

### Ladder di soluzione

Prima di costruire una nuova capability, l'Evolution Engine confronta:

1. non fare nulla;
2. comporre capability gia attive;
3. usare uno skill esistente;
4. usare un MCP esistente verificabile;
5. usare API, plugin, scripting, file exchange o CLI ufficiali;
6. generare un MCP o adapter custom isolato;
7. usare UI automation supervisionata come ultima risorsa.

La scelta conserva separatamente utilita, costo, privacy, rischio, autorita
necessaria e manutenzione. Nessun singolo score puo compensare un blocker di
privacy, sicurezza o autorita.

La costruzione di una capability non implica attivazione. Una activation
authority indipendente puo attivarla automaticamente solo quando il report di
valutazione e valido e l'autorita richiesta e un sottoinsieme di quella gia
concessa. La specifica completa e in `19_Selective_Capability_Forge_Plan.md`.

## Loop evolutivo

```text
OBSERVE
  raccogli outcome, correzioni, preferenze, trace e controevidenze
FRAME
  descrivi problema, scope e ipotesi falsificabile
GENERATE
  crea piu candidate e descendant da uno o piu parent promettenti
VALIDATE
  verifica schema, build, action contract, privacy e invarianti
EVALUATE
  replay personale redatto + benchmark generici + analisi rischi
EXPOSE
  shadow, preview, confronto a coppie o canary
DECIDE
  promuovi, itera, archivia o rollback
LEARN
  registra esito reale nel lineage e aggiorna la calibrazione
```

Il loop puo essere attivato durante il giorno o in background. Non esiste un
vincolo universale "una volta per notte" ne un cap fisso di due mutazioni. Il
budget dipende da evidenza, impatto, costo, indipendenza e disruption percepita.

## Ricerca su lineage, non catena singola

SEED mantiene piu rami quando rappresentano trade-off reali:

```text
active-v12
  |-- v13a: UI piu diretta
  |-- v13b: workflow piu automatico
  `-- v13c: memoria piu selettiva
```

Non tutte le varianti devono diventare attive. L'archivio conserva parent,
ipotesi, diff, evaluator, risultati e decisione. Questo evita che l'evoluzione
sia una sequenza opaca di patch irreversibili.

## Evaluator

Ogni candidate usa un portafoglio di evaluator proporzionato all'impatto:

- test e invarianti generici;
- replay di episodi reali redatti;
- simulazioni e input avversariali;
- confronto con parent e alternative;
- metriche di costo, latenza e affidabilita;
- metriche di privacy, permessi e sicurezza;
- valutazione di personalita, mirroring e sycophancy;
- feedback esplicito o confronto a coppie dell'utente;
- osservazione dell'esito in shadow/canary.

L'evaluator non deve essere interamente controllato dal candidate. Le mutazioni
agli evaluator richiedono una valutazione esterna, come stabilito in
`11_Contratto_Mutazione.md`.

Un design reviewer basato su modello puo confrontare candidate e direttive
SEED, ma produce solo evidenza fallibile. Deve usare una famiglia diversa dal
builder quando possibile, operare read-only, citare evidence reference e
restituire `inconclusive` su output invalido o prove mancanti. Non sostituisce
controlli deterministici, evaluator indipendenti o promotion authority. Vedi
`13_ModelRoles_Voice_Plan.md`.

## Selezione multi-obiettivo

Non esiste uno score unico affidabile per ogni cambiamento. SEED conserva un
fronte di varianti quando nessuna domina le altre su:

- utilita e successo;
- errori e correzioni;
- fiducia, prevedibilita e controllo;
- compatibilita e continuita della personalita;
- privacy e sicurezza;
- latenza, costo e robustezza;
- reversibilita e qualita del recovery.

Engagement, durata della sessione e frequenza d'uso possono essere segnali
secondari, mai obiettivi dominanti.

## Stabilita e disruption

La stabilita si governa per impatto:

- cambiamenti invisibili e indipendenti possono essere promossi rapidamente se
  verificati;
- cambiamenti percettibili richiedono preview, changelog e osservazione;
- cambiamenti identitari o di workflow centrale richiedono confronto a coppie e
  canary;
- variazioni di permessi richiedono consenso;
- mutazioni di supervisor, evaluator, privacy o recovery richiedono owner gate.

Il cooldown e uno strumento possibile, non un vincolo fisso. La domanda e:
"quanta evidenza e recuperabilita servono per questo impatto?"

## Pruning e sottrazione

L'evoluzione include rimozione e semplificazione:

- capability non utili diventano dormant;
- workflow ridondanti possono essere fusi;
- inferenze personali senza supporto perdono confidenza o scadono;
- UI e automazioni possono essere ridotte;
- rami non promettenti restano archiviati senza essere attivi.

Una funzione non viene rimossa solo perche poco usata: il sistema considera
rarita del bisogno, valore quando serve e costo di mantenimento.

Allo stesso modo, una capability tecnicamente possibile non viene costruita
solo perche SEED sa costruirla. `Non imparare`, `rimandare`, `usare una
soluzione temporanea` e `rendere dormant` sono esiti validi del loop evolutivo.

## Command router deterministico

Il command router Python esistente resta una base utile, non un limite
all'evoluzione. Per comandi noti:

```text
alias esatto -> pattern -> fuzzy -> normalizzazione assistita -> conversazione
```

Il determinismo riduce costo ed errori. SEED puo comunque proporre mutazioni al
router, agli intent e agli handler quando una variante dimostra risultati
migliori. Un handler generato non ottiene automaticamente nuovi permessi.

## Predizioni falsificabili

Ogni candidate dichiara segnali attesi e finestra:

```text
ipotesi:
  il nuovo workflow riduce le correzioni nei task di pianificazione
segnali:
  correction_rate diminuisce
  task_success non diminuisce
  latency resta entro soglia
  trust survey non peggiora
finestra:
  replay + 3 giorni di canary
```

Se i segnali non si verificano, SEED archivia, itera o rollback. Non riscrive a
posteriori la motivazione per dichiarare successo.

## Cosa non puo fare un candidate direttamente

Un candidate non puo:

- sovrascrivere l'unica versione attiva;
- promuovere se stesso;
- cancellare lineage o controevidenze;
- espandere permessi senza dichiarazione e consenso;
- usare il proprio evaluator modificato come unica prova;
- eliminare il percorso di recovery;
- trasformare un'ipotesi sull'utente in fatto senza evidenza.

Questi sono limiti dell'attivazione e della governance, non limiti allo spazio
delle idee.
