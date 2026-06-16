# 03 - Privacy Gate

> Tutto cio che lascia il PC dell'utente passa dal privacy gate. Il gate e
> mutabile nello spazio candidato, ma nessuna sua mutazione puo auto-promuoversi
> o indebolire il trattamento attivo senza valutazione indipendente e owner gate.

## Obiettivo

Il privacy gate minimizza il contenuto inviato a provider, evaluator o export.
Non e una garanzia assoluta di anonimizzazione. Ogni flusso deve dichiarare:

- destinazione;
- scopo;
- categorie di dati;
- trasformazioni applicate;
- retention;
- permessi;
- possibilita di revoca.

## Pipeline corrente

1. OpenAI Privacy Filter locale per token classification PII:
   [repo](https://github.com/openai/privacy-filter) e
   [model card](https://huggingface.co/openai/privacy-filter);
2. rinforzo deterministico per email, telefono, IBAN, codice fiscale, path,
   hostname e pattern di segreti;
3. pseudonimizzazione stabile con mapping locale cifrato tramite DPAPI;
4. minimizzazione del contesto;
5. re-idratazione solo verso l'utente.

Il filtro e recall-oriented, ma resta fallibile, soprattutto su lingue e casi
non coperti. I test e i limiti devono restare visibili.

## Trust zone

| Zona | Contenuto | Regola |
|---|---|---|
| Personale locale | memoria, user model, relazione, trace, pii map, credenziali | non esce automaticamente |
| Evolution lab | descendant e fixture minime/redatte | accesso proporzionato al piano di eval |
| Provider remoto | prompt e contesto redatti | minimo necessario, provider dichiarato |
| Export | report e artefatti scelti | azione esplicita e anteprima dell'utente |

## Dati evolutivi

Candidate, evaluator e lineage possono esporre piu dati di una normale chat se
non governati. Sono quindi obbligatori:

- `evidence_refs` invece di copie indiscriminate dei contenuti;
- fixture di replay redatte;
- separazione tra metriche aggregate e testo personale;
- nessuna credenziale dentro build, diff, prompt o log;
- scansione di diff e artefatti per PII e segreti;
- `permissions_delta` per ogni candidate;
- export del lineage solo dopo anteprima.

Una mutazione non puo usare la privacy come semplice metrica da compensare con
maggiore utilita. Una regressione bloccante di privacy impedisce la promozione.

### Segreti discard-only e capability generate

Password, token, cookie di sessione, recovery code e segreti equivalenti sono
`discard-only`: se rilevati durante osservazione, costruzione o valutazione
vengono scartati immediatamente e non diventano memoria, evidence reference,
prompt, lineage, audit o input di tool.

Le capability generate non ricevono credenziali. Un Connection Broker separato
conserva i segreti nel vault locale cifrato ed espone soltanto operazioni
tipizzate e autorizzate. Dati personali, sensibili e finanziari possono essere
analizzati localmente; se non esiste un percorso locale sicuro, il flusso
fallisce chiuso invece di inviare il dato grezzo a un provider remoto.

## Personalita e privacy

Il modello di personalita e dato personale. Deve distinguere fatti, preferenze,
ipotesi, pattern e segnali affettivi. L'utente puo:

- vedere cosa SEED pensa di sapere;
- conoscere provenance e confidenza;
- correggere o cancellare;
- impedire l'uso di categorie;
- far scadere ipotesi;
- escludere dati da replay ed evoluzione.

I segnali vocali o affettivi non vengono promossi automaticamente a tratti
stabili. Vedi `09_Personalita_Compatibile.md`.

## Cosa puo uscire

| Flusso | Default | Condizione |
|---|---|---|
| Chat verso API | redatto e pseudonimizzato | provider configurato e consenso |
| Proposta/eval LLM remoto | redatto, aggregato e minimo | piano di valutazione dichiarato |
| File, screenshot, audio | no | opt-in specifico e permessi |
| Telemetria e lineage | locale | export manuale al giorno 15 |
| pii map, credenziali, memoria raw | mai automaticamente | nessuna eccezione implicita |

## Mutazioni del privacy gate

Sono ammesse come candidate, ma richiedono:

- evaluator indipendente dalla variante;
- corpus di regressione e casi avversariali;
- confronto con il gate attivo;
- nessun uso di PII reale non consensuale nei test;
- owner gate;
- canary limitato;
- rollback provato.

Il fatto che il gate attuale sia migliorabile non giustifica una sostituzione
diretta. Questa regola protegge il processo senza dichiarare immutabile il
componente.

## Export sperimentale

Al giorno 15 l'utente vede e approva il report prima della condivisione. Il
report preferisce aggregati: utilizzo, promozioni, rollback, distanze tra
versioni, risultati evaluator e survey. Testi, titoli finestra e memoria
personale non sono inclusi per default.
