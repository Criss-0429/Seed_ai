# Jarvis User Knowledge Ontology

**Ultimo Aggiornamento:** 2026-05-25  
**Rilevanza per JARVIS:** Alta - definisce come JARVIS deve conoscere l'utente senza hardcodare esempi specifici.

Questa pagina formalizza il punto piu' importante della nuova visione: palestra, pasti, universita', casa, partner, amici o luci accese non sono feature singole. Sono esempi di una ontologia aperta della conoscenza dell'utente.

## 1. Principio

La feature non e' "ricordare la palestra".

La feature e':

- riconoscere fatti personali;
- collegarli a contesti, luoghi, persone, routine e progetti;
- distinguere stato, routine, preferenza, pattern, relazione, ipotesi e confine;
- usare la conoscenza solo quando e' rilevante;
- chiedere conferma quando l'inferenza e' sensibile.

## 2. Domini aperti

| Dominio | Esempi |
|---|---|
| Identita' e situazione di vita | studente, lavoratore, fuorisede, pendolare, freelance |
| Luoghi e mobilita' | casa, universita', lavoro, palestra, tragitti |
| Relazioni | famiglia, amici, partner, colleghi, docenti |
| Studio e lavoro | lezioni, esami, scadenze, repo, clienti |
| Routine | palestra, pasti, sonno, studio, sessioni creative |
| Energia e recupero | focus, stanchezza, recupero post-allenamento |
| Segnali affettivi vocali | possibile fretta, irritazione, calma, incertezza, stanchezza rilevati localmente |
| Preferenze | musica, tono, dettaglio, canali, tool |
| Vincoli e confini | privacy, autonomia, dati salute, invii esterni |
| Valori e obiettivi | salute, studio, autonomia, Jarvis, creativita' |

## 3. Tipi di conoscenza

| Tipo | Significato | Esempio |
|---|---|---|
| Fatto | informazione specifica verificata | "Il lunedi' mattina ha lezione" |
| Stato | condizione temporanea | "Oggi e' fuori casa" |
| Routine | ricorrenza abbastanza stabile | "Di solito va in palestra il mercoledi' sera" |
| Pattern | ricorrenza interpretata da piu' evidenze | "Quando lavora fino a tardi tende a saltare la cena" |
| Preferenza | scelta stabile o ricorrente | "Durante coding preferisce update brevi" |
| Relazione | legame con persona/gruppo | "X e' un familiare stretto" |
| Eccezione | modifica temporanea della routine | "Questa settimana non c'e' lezione" |
| Ipotesi | inferenza non confermata | "Forse sta procrastinando la palestra" |
| Segnale affettivo | stato/ipotesi temporanea da voce o comportamento, con confidence e scadenza | "In questo turno sembra di fretta, confidence media" |
| Confine | regola personale/privacy | "Non usare dati salute senza conferma" |

## 4. Regola di sicurezza cognitiva

Un'ipotesi non deve diventare fatto.

Una routine non deve diventare obbligo.

Una relazione non deve diventare leva di proattivita' senza sensibilita'.

Un pattern personale deve essere:

- evidence-based;
- confidente ma correggibile;
- non invadente;
- spiegabile;
- disattivabile.

Regola specifica per segnali affettivi:

- un label emotion non e' un fatto psicologico;
- non usare segnali vocali per diagnosi, giudizi stabili o autorizzazioni implicite;
- persistere solo segnali opt-in, redatti, con confidence, fonte, modello e retention;
- preferire uso per-turn: tono, brevita, richiesta di conferma, non memoria canonica;
- se Cristian corregge il segnale, la correzione prevale sull'inferenza.

## 5. Relazioni

- [[Jarvis_Final_Feature_Vision]]
- [[GiustoDev_Muffin_Architecture]]
- [[Jarvis_Memory_Architecture]]
- [[Data_Privacy_Controls]]
- [[Emotion2Vec]]

**Fonte raw:** `raw/GiustoDev_architecture/jarvis-final-feature-vision.md`; `raw/scouting_2026_05_25_harness_emotion_sources.md`
