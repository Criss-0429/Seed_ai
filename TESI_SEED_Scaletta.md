# Tesi di Laurea — Progetto SEED
## Scaletta (triennale, ~40-60 pagine)

> **Titolo provvisorio:** *SEED — Un sistema che cresce con l'utente: personalizzazione adattiva e realtime della user experience tramite agenti AI*
>
> **Tesi centrale:** un software non deve essere uguale per tutti. Partendo da un "foglio bianco" identico, il sistema osserva ciò che è saliente per l'utente e si evolve — generando tool, interfacce e adattamenti — fino a diventare un prodotto unico per ogni persona.

---

## 1. Introduzione (4-5 pp)

- Il problema: il software oggi è one-size-fits-all; la personalizzazione è un menu di opzioni predefinite, non una crescita organica.
- **Genesi del progetto** (1 paragrafo, max 1 pagina): il prototipo "JARVIS" come prima esplorazione — memoria persistente, loop di pensiero e auto-critica. Cosa ha insegnato e perché ha portato al pivot verso SEED.
- La conversazione chiave: il rapporto storico tra umani e dati → la visione di un sistema personale invece di un OS uguale per tutti.
- Domanda di ricerca: *può un sistema partire identico per tutti e divergere in prodotti diversi, guidato solo dall'osservazione dell'uso reale?*
- Obiettivi e scope: un harness applicativo (non un OS), testato su 2-3 utenti per 2 settimane.
- Struttura della tesi.

## 2. Contesto e stato dell'arte (8-10 pp)

- **2.1 Umani e dati nella storia** (breve, è la cornice filosofica): dalla scrittura ai database al personal computing — il dato è sempre stato organizzato *per* l'utente da qualcun altro.
- **2.2 Personalizzazione e adaptive UI**: temi/skin, recommender system, adaptive interfaces in letteratura HCI; perché restano configurazione, non evoluzione.
- **2.3 Agenti LLM e codice auto-generato**: tool use, self-correction loop, code generation con review; il pattern propose → verify → approve.
- **2.4 Accessibilità**: limiti dell'approccio attuale (pannelli opzioni nascosti); l'idea di adattamento a livello di rendering (es. cromia per daltonici).
- **2.5 La prospettiva del game design**: sistemi emergenti, progressione, feedback loop — perché chi progetta giochi è attrezzato a progettare sistemi che evolvono con chi li usa. *(Questo collega la tesi al tuo corso di studi: non nasconderlo, valorizzalo.)*

## 3. SEED — Visione e principi di design (6-8 pp)

- **3.1 Il foglio bianco**: tutti partono dalla stessa base; nessuna feature preinstallata "per categoria di utente".
- **3.2 Salienza, non configurazione**: il sistema propone solo ciò che ha *visto* servire. L'avvocato che vive di mail ottiene tool per le mail; il pizzaiolo che le ignora non vede mai quel pannello — non disattivato: mai concepito.
- **3.3 L'utente resta sovrano**: ogni evoluzione è proposta → l'utente accetta, rifiuta o corregge. Trasparenza del "perché ti propongo questo".
- **3.4 UX realtime e re-rendering**: contenuti ripresentati nello stile dell'utente (es. siti DnD su pergamena); accessibilità come caso d'uso primario, non opzione.
- **3.5 Divergenza come obiettivo**: il successo si misura in quanto due istanze diventano *diverse*.

## 4. Architettura del sistema (8-10 pp)

- **4.1 Overview** (diagramma generale).
- **4.2 Osservazione e salienza**: cosa viene tracciato, come si decide che un pattern "conta".
- **4.3 Memoria**: cosa il sistema ricorda dell'utente e come la usa (eredità del lavoro su JARVIS).
- **4.4 Loop di generazione**: pensa → genera codice/tool → si auto-revisiona (dubbio) → approva o scarta → propone all'utente.
- **4.5 Re-rendering dell'interfaccia**: pipeline di trasformazione (es. HTML → reimpaginazione tematica/accessibile).
- **4.6 Sicurezza e contenimento**: sandbox del codice auto-generato, limiti, cosa il sistema non può fare da solo.

## 5. Implementazione del prototipo (5-7 pp)

- Stack tecnologico e scelte (e perché — onestà sui trade-off da non-programmatore di sistemi).
- I componenti realizzati vs quelli simulati/semplificati.
- Esempi concreti: un tool generato dal sistema, un re-rendering, un ciclo proposta-rifiuto-correzione.
- Screenshot e walkthrough.

## 6. Sperimentazione (5-6 pp)

- **6.1 Metodologia**: 2-3 utenti con profili volutamente diversi, 2 settimane, stessa base di partenza.
- **6.2 Metriche**: tool generati e accettati/rifiutati per utente; divergenza UI (colori, layout, pannelli); tempo prima della prima proposta utile; episodi di correzione da parte dell'utente.
- **6.3 Raccolta dati**: log di sistema + diario/intervista agli utenti (cosa hanno percepito, fiducia nelle proposte).

## 7. Risultati e discussione (5-7 pp)

- Confronto visivo e funzionale delle istanze finali: *stessa base, prodotti diversi* (questo è il momento "figo e interagibile" — confronto side-by-side).
- Cosa il sistema ha capito bene, cosa ha proposto a sproposito.
- Il ruolo del rifiuto/correzione dell'utente nell'evoluzione.
- Discussione: la divergenza osservata risponde alla domanda di ricerca?

## 8. Limiti, etica e sviluppi futuri (3-4 pp)

- Limiti: campione minuscolo, durata breve, costi computazionali, robustezza del codice auto-generato.
- **Etica e privacy**: un sistema che osserva tutto è anche un rischio — trasparenza, dati locali, consenso. (Capitolo breve ma indispensabile: il relatore e la commissione lo cercheranno.)
- Futuro: dall'app harness verso il sistema personale completo — la visione "non più Mac o Windows, ma il *tuo* sistema".

## 9. Conclusioni (2 pp)

- Sintesi del percorso e dei risultati.
- Riflessione personale: dal "faccio il mio Jarvis perché è figo" alla progettazione di sistemi che crescono con le persone.

---

## Appendici e bibliografia

- A. Log di esempio delle evoluzioni generate
- B. Questionario/traccia interviste utenti
- C. Dettagli tecnici (prompt, schemi memoria)
- Bibliografia (HCI adaptive interfaces, LLM agents, accessibilità, storia del personal computing)

---

## Note operative

- **Bilanciamento pagine**: cap. 2-4 sono il cuore (~26 pp); se serve tagliare, si taglia dal 2, mai dal 6-7 (i dati del test sono ciò che rende la tesi tua).
- **Per la discussione**: prepara il confronto side-by-side delle 2-3 istanze come demo/video — è l'argomento più forte che hai.
- **Rischio da gestire subito**: il test di 2 settimane va pianificato a ritroso dalla data di consegna. Prototipo congelato → test → analisi → scrittura cap. 6-7.
