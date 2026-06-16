# 04 - Isolamento, sicurezza e recovery

> La potenza dello spazio di mutazione rende isolamento e recovery piu
> importanti, non meno. Le restrizioni definiscono cosa puo essere attivato con
> una certa evidenza e autorita; non definiscono cio che puo essere proposto.

## Modello di minaccia

SEED deve assumere che un candidate possa:

- contenere bug o codice dannoso;
- chiedere permessi non necessari;
- leggere dati personali oltre lo scope;
- manipolare evaluator o metriche;
- degradare privacy, recovery o prevedibilita;
- fallire all'avvio;
- produrre effetti corretti in test ma dannosi nel contesto reale.

Il modello generatore non viene trattato come autorita fidata.

## Livelli di isolamento

| Oggetto | Isolamento minimo |
|---|---|
| Capability corrente | subprocess, env minimo, I/O contrattuale, timeout |
| Descendant UI/workflow | profilo dati separato, fixture redatte, nessun effetto reale in replay |
| Descendant completo | directory/build separato, credenziali assenti, health check |
| Canary | contesti, tempo, permessi ed effetti limitati |
| Mutazione supervisor/evaluator | verifica da versione indipendente e owner gate |

La sandbox Python corrente e utile ma non equivale a isolamento forte del
desktop Windows. Il rischio residuo deve essere dichiarato e compensato con
permessi, canary, versioni separate e recovery.

## Permission broker

Ogni action contract dichiara effetti e classe di rischio:

| Classe | Esempi | Regola di attivazione |
|---|---|---|
| `safe` | risposta, nota locale | osservabile e revocabile |
| `read_safe` | workspace SEED | scope dichiarato |
| `read_sensitive` | file personali | selezione o consenso esplicito |
| `execute` | aprire app/processo | allowlist e motivazione |
| `network` | provider, web, integrazione | destinazione e retention visibili |
| `write` | modifica file | preview/scope e consenso |
| `destructive` | rimozione, sistema, credenziali | mai implicito; owner gate e recovery |

Il target non dichiara `destructive` impossibile per sempre. Dichiara che non
puo essere attivato da un candidate senza un percorso esplicito, verificato e
approvato. Dinieghi e revoche diventano evidenza, non motivi per ripetere la
richiesta.

## Controlli su codice e artefatti

Prima di qualunque esecuzione:

- parsing e audit statico;
- scansione segreti e PII;
- dipendenze e provenienza dichiarate;
- build riproducibile;
- action contract e `permissions_delta`;
- controlli su path e destinazioni;
- test con input sintetici e avversariali;
- limite risorse e timeout;
- identificazione del parent e rollback.

L'audit AST corrente resta un evaluator, non una garanzia. Mutazioni fuori dal
template capability richiedono evaluator adatti al nuovo scope.

## Path e credenziali

La base v0.2 protegge path di sistema, profili altrui, credenziali e
`core_config`. Nel target queste policy possono essere candidate a mutazione,
ma una variante che le cambia:

- non riceve automaticamente i dati protetti;
- deve dichiarare la variazione;
- viene testata da evaluator indipendenti;
- richiede owner gate;
- non sostituisce la policy attiva durante la valutazione.

Default operativo: deny per scritture fuori dal workspace e assenza di segreti
nell'ambiente dei descendant.

## Anti-gaming

Un candidate non puo dimostrare il proprio successo:

- cancellando errori o trace;
- riducendo artificialmente i task valutati;
- modificando la definizione delle metriche senza dichiararlo;
- nascondendo variazioni di permessi;
- disabilitando health check, rollback o privacy;
- usando soltanto evaluator che esso stesso ha modificato.

I replay nascosti, gli invarianti indipendenti e l'osservazione reale in canary
servono a rilevare questi comportamenti.

## Stable boot e recovery

Prima della promozione di un descendant completo devono esistere:

- versione nota funzionante;
- avvio per version id;
- health check indipendente;
- timeout;
- fallback automatico;
- rollback manuale;
- log del supervisor;
- prova di recovery eseguita.

Una mutazione che migliora i benchmark ma rende incerto il recovery non e pronta
per essere attiva.

## Registro rischi

| Rischio | Mitigazione | Residuo |
|---|---|---|
| PII o segreto in artefatto | scansione, fixture redatte, env minimo | presente |
| Codice dannoso entro i permessi | isolamento, action contract, canary | presente |
| Prompt injection | separazione dati/istruzioni, capability minime, replay | medio |
| Gaming evaluator | evaluator indipendenti e invarianti nascosti | presente |
| Perdita dell'avvio | supervisor, known-good e fallback | basso se verificato |
| Disorientamento | preview, changelog, confronto e rollback | dipende dall'utente |

I requisiti completi di promozione sono in `11_Contratto_Mutazione.md`.
