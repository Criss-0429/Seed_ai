# 06 - Protocollo dell'esperimento

> **Obiettivo:** verificare in 14 giorni se una base comune puo evolvere in
> sistemi individualmente utili, compatibili ma non speculari, mantenendo
> continuita, controllo e recuperabilita.

## Domande di ricerca

1. **RQ1 - Divergenza utile:** i descendant attivi divergono tra utenti e
   migliorano rispetto ai rispettivi parent?
2. **RQ2 - Compatibilita relazionale:** SEED diventa piu compatibile senza
   diventare una copia o un interlocutore compiacente?
3. **RQ3 - Accettazione del cambiamento:** gli utenti comprendono, tollerano e
   controllano un sistema che muta?
4. **RQ4 - Qualita della governance:** lineage, evaluator, canary e rollback
   impediscono regressioni e rendono le decisioni ricostruibili?

## Disegno

- **Partecipanti:** 6-8 persone con profili d'uso differenti.
- **Durata:** giorno 0 onboarding, 14 giorni di uso, giorno 15 debrief/export.
- **Base comune:** stesso build iniziale e stessi principi; key e consensi per utente.
- **Confronto interno:** ogni candidate viene confrontato con il proprio parent.
- **Baseline:** mantenere una versione non evolutiva o periodi shadow per
  distinguere utilita dell'evoluzione da novelty e uso del solo assistente.
- **Dati:** locali; export esplicito e leggibile dall'utente al termine.

## Giorno 0 - Risveglio e onboarding

1. installazione, health check e download necessari con stato visibile;
2. consenso informato su osservazione, provider, mutazioni, permessi, export e
   interruzione;
3. esperienza minimale di risveglio;
4. conversazione libera: l'utente parla di se, delle proprie giornate e di cosa
   desidera dalla relazione;
5. confronti a coppie su tono, proattivita, livello di sfida e forma delle risposte;
6. restituzione delle prime ipotesi, tutte correggibili;
7. prova guidata di spiegazione, pausa, permessi e rollback;
8. misura iniziale di aspettative, fiducia e preferenze.

Non vengono assegnate diagnosi o etichette di personalita. Le inferenze iniziali
restano ipotesi con provenance e confidenza.

## Fasi dei 14 giorni

| Periodo | Scopo | Osservazioni principali |
|---|---|---|
| Giorni 1-3 | Calibrazione | correzioni, preferenze esplicite, frizioni, comprensione dell'onboarding |
| Giorni 4-7 | Prime evoluzioni | qualita dei candidate, preview, piccoli canary, utilita iniziale |
| Giorni 8-11 | Evoluzione profonda | workflow, capability, personalita contestuale, possibili descendant piu ampi |
| Giorni 12-14 | Validazione e stabilita | regressioni, continuita, recovery, confronto con parent e baseline |

Le mutazioni non vengono artificialmente fermate nell'ultima fase. Si misura se
il sistema sa evitare cambiamenti inutili e mantenere stabilita quando opportuno.

## Raccolta locale

| Strumento | Cosa raccoglie | Quando |
|---|---|---|
| Trace operative | richiesta, decisione, azione, esito, correzione | continuo |
| Stato personale | fatti, ipotesi, preferenze, correzioni e provenance | su evento |
| Lineage | candidate, descendant, parent, evaluator, decisioni e rollback | ogni mutazione |
| Metriche runtime | successo, errori, latenza, costo, permessi | continuo |
| Feedback breve | utilita, prevedibilita, compatibilita, controllo | giornaliero, non obbligatorio |
| Confronti a coppie | preferenza tra parent/varianti o stili | quando informativo |
| Diario ricercatore | incidenti e interventi esterni | quando serve |

Cristian non accede automaticamente ai dati durante il test. Gli interventi
necessari vengono registrati per non confonderli con evoluzione autonoma.

## Metriche

### Evoluzione e lineage

- numero di candidate, descendant, canary, promozioni e rollback;
- profondita e ramificazione del lineage;
- percentuale di mutazioni con evidenza e previsione verificata;
- regressioni intercettate prima e dopo la promozione;
- tempo e affidabilita del recovery;
- distanza e composizione delle versioni finali tra utenti.

### Utilita

- successo sui task e riduzione delle correzioni;
- uso spontaneo, trattato come segnale secondario;
- preferenza rispetto al parent o alla baseline;
- valore delle capability e dei workflow emersi;
- costo, latenza e affidabilita;
- utilita percepita e SUS finale.

### Personalita compatibile

- compatibilita percepita;
- distintivita e capacita di dissenso;
- prevedibilita e continuita;
- adattamento appropriato al contesto;
- correzioni delle inferenze personali;
- mirroring e sycophancy rilevati nei replay o riportati dall'utente;
- preferenze a coppie tra varianti.

### Fiducia, controllo e privacy

- comprensione del perche di una mutazione;
- uso di spiegazioni, pause, revoche e rollback;
- permessi negati o revocati;
- eventi privacy registrati come conteggi, non contenuto;
- fiducia prima/dopo e senso di controllo;
- incidenti e dati non ricostruibili dal lineage.

## Giorno 15 - Debrief ed export

- l'utente ispeziona ed esporta il report prima di condividerlo;
- intervista semi-strutturata di 30-45 minuti;
- confronto tra esperienza iniziale, parent importanti e versione finale;
- analisi di una mutazione apprezzata, una rifiutata e una non percepita;
- domande su compatibilita, identita propria di SEED, dissenso e mirroring;
- prova finale di rollback/recovery;
- SUS e valutazione della disponibilita a continuare l'uso.

## Rischi e contromisure

| Rischio | Contromisura |
|---|---|
| Novelty effect | 14 giorni, trend temporale, parent comparison e baseline |
| Poca interazione | nessuna forzatura; trattare il non-uso come risultato e indagarlo nel debrief |
| Mutazioni senza evidenza | contratto obbligatorio, evaluator e lineage |
| Evoluzione aggressiva | impatto, preview, canary, controllo e recovery |
| Evoluzione troppo timida | misurare candidate scartati e ragioni; non abbassare artificialmente i gate |
| Mirroring o compiacenza | counterpoint, replay anti-sycophancy e metriche di distintivita |
| Profilazione eccessiva | ipotesi/fatti separati, confidenza, scadenza e correzione |
| Gaming degli evaluator | metriche indipendenti, invarianti nascosti e owner gate |
| Bug che compromette il test | pilot, supervisor, health check e versione nota funzionante |
| Costi API | budget per utente e metriche costo/beneficio, senza limitare a priori le categorie |

## Criteri di interpretazione

La sola divergenza non dimostra successo. Una mutazione e positiva soltanto se
produce beneficio osservabile senza un peggioramento non accettato negli altri
obiettivi. Una versione finale piu simile linguisticamente all'utente non e
necessariamente piu compatibile.

Le fonti e i limiti di trasferibilita sono in `10_Fonti_Ricerca.md`; i requisiti
di audit e promozione sono in `11_Contratto_Mutazione.md`.
