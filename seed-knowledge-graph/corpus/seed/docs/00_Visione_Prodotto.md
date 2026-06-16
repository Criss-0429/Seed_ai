# 00 - Visione prodotto e autorita documentale

> **Stato:** decisione di prodotto SEED.
> **Ambito:** questa documentazione descrive l'architettura obiettivo dell'esperimento.
> Il runtime v0.2 esistente e una base tecnica, non la specifica finale.

## Tesi del prodotto

SEED e un'applicazione personale che parte da una base comune, costruisce una
relazione riconoscibile con il singolo utente e puo evolvere qualunque parte di
se stessa quando esiste un motivo verificabile per farlo.

Lo spazio delle mutazioni candidate e intenzionalmente aperto: interfaccia,
tono, policy, workflow, capability, memoria, routing, architettura e componenti
del runtime possono essere oggetto di una proposta. L'apertura dello spazio di
ricerca non autorizza pero una proposta a sostituire direttamente la versione
attiva.

La regola centrale e:

> **Nessun limite su cio che SEED puo proporre; valutazione rigorosa su cio che
> SEED puo attivare.**

SEED non deve diventare una copia dell'utente. Deve diventare un interlocutore
compatibile: capace di adattare forma, ritmo e modalita di collaborazione,
mantenendo identita, giudizio e capacita di contraddire.

## Esperienza iniziale

L'esperienza di primo avvio prende ispirazione dalla qualita relazionale e dalla
semplicita visiva di *Her*, senza copiarne interfaccia o personaggio:

1. una presenza centrale minimale e calda segnala che il sistema si sta avviando;
2. SEED spiega in linguaggio semplice cosa osservera, cosa puo modificare e come
   interrompere, correggere o annullare;
3. avvia una conversazione naturale: chiede all'utente di parlare di se, delle
   proprie giornate e di cosa si aspetta da un assistente;
4. usa brevi confronti concreti per distinguere preferenze simili, per esempio
   risposta diretta oppure ragionata, suggerimento spontaneo oppure su richiesta;
5. restituisce cio che pensa di aver capito, marcando ogni inferenza come
   correggibile;
6. entra nella normale esperienza conversazionale.

Il primo avvio non e un test di personalita e non produce diagnosi. Genera
ipotesi iniziali a bassa confidenza che l'uso reale puo confermare, correggere o
eliminare.

## Principi non negoziabili

1. **Relazione, non imitazione.** La compatibilita non coincide con il matching
   continuo dello stile dell'utente.
2. **Ipotesi diverse dai fatti.** Un segnale implicito non diventa una verita
   personale senza evidenze e possibilita di correzione.
3. **Mutazione diversa da attivazione.** Il componente che genera una mutazione
   non puo auto-certificarla ne promuoverla da solo.
4. **Evidenza prima della promozione.** Ogni cambiamento attivo deve avere una
   ragione, una previsione osservabile, una valutazione e un rollback.
5. **Continuita percepibile.** Dopo una mutazione l'utente deve riconoscere SEED,
   comprenderne il cambiamento e poter tornare indietro.
6. **Controllo locale.** Memoria, profilo, lineage e telemetria restano sul PC
   dell'utente; ogni esportazione e esplicita.
7. **Permessi proporzionati agli effetti.** Il consenso segue il rischio e la
   variazione di permessi, non il semplice fatto che una funzione sia nuova.
8. **Utilita multi-obiettivo.** SEED non ottimizza engagement, compiacenza o
   tempo trascorso come obiettivo dominante.
9. **Trasparenza interrogabile.** L'utente puo chiedere perche SEED crede
   qualcosa, perche e cambiato e quale evidenza ha usato.
10. **Nessuna memoria o mutazione irreversibile per costruzione.**

## Superficie primaria e superfici secondarie

La superficie primaria resta conversazionale e minimale:

- presenza centrale;
- stato di risveglio, ascolto, pensiero, azione e ritorno;
- testo e voce opzionale;
- ack immediato, aggiornamenti durante il lavoro e risultato finale.

Le informazioni operative non devono affollare la relazione principale. Sono
accessibili in superfici secondarie:

- cosa SEED pensa di sapere dell'utente;
- modifiche proposte, in prova, attive e annullate;
- lineage delle versioni;
- permessi e privacy;
- motivazioni, evidenze e risultati delle valutazioni;
- esportazione e cancellazione.

## Runtime attuale e architettura obiettivo

Il runtime v0.2 implementa gia elementi utili: command router deterministico,
privacy gate, permission broker, sandbox capability, memoria locale, watcher,
reflection, snapshot e rollback. Implementa pero una politica piu restrittiva
rispetto a questa visione: core immutabile, mutazioni limitate agli strati
periferici e selezione con cap fisso.

Questi vincoli restano **descrizione dello stato corrente**, non decisioni
definitive di prodotto. La migrazione richiesta e documentata in:

- `01_Architettura.md`;
- `02_EvolutionEngine.md`;
- `09_Personalita_Compatibile.md`;
- `11_Contratto_Mutazione.md`.

## Gerarchia delle fonti

In caso di conflitto tra documenti SEED:

1. `00_Visione_Prodotto.md` definisce intento e principi;
2. `11_Contratto_Mutazione.md` definisce i requisiti normativi di promozione;
3. `01_Architettura.md`, `02_EvolutionEngine.md` e
   `09_Personalita_Compatibile.md` definiscono il disegno tecnico;
4. `03`-`08` descrivono sottosistemi, protocollo e stato corrente;
5. `10_Fonti_Ricerca.md` motiva le decisioni ma non le sostituisce;
6. la LLM Wiki fornisce contesto subordinato;
7. il codice v0.2 descrive cio che esiste, non cio che deve restare.

## Criterio di successo

Al termine dei 14 giorni, SEED non e riuscito soltanto se e "diverso" dalla
base. Deve risultare:

- piu utile per quel partecipante;
- riconoscibile e coerente;
- compatibile senza essere speculare;
- capace di spiegare e annullare le proprie evoluzioni;
- empiricamente migliore della propria versione precedente su segnali dichiarati;
- ancora sotto il controllo dell'utente.
