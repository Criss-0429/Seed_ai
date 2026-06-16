# Personal OS Thesis Direction

**Stato:** ipotesi progettuale da discutere con il relatore  
**Ultimo aggiornamento:** 2026-06-10  
**Relazione con JARVIS:** JARVIS e' laboratorio tecnico e caso di studio; non
coincide con l'intera tesi.

## Direzione Chiara

La tesi puo' indagare il passaggio storico da interfacce che chiedono all'uomo
di adattarsi al linguaggio della macchina a sistemi operativi che adattano
linguaggio, rappresentazione e interazione alla persona.

Domanda centrale:

> Come cambia il rapporto uomo-macchina quando il sistema operativo smette di
> essere un'interfaccia standard uguale per tutti e diventa uno strato
> interpretativo personale, capace di riconfigurare l'esperienza in tempo reale
> usando dati longitudinali, senza sottrarre controllo all'utente?

Ipotesi:

> L'evoluzione dell'interfaccia sposta progressivamente il lavoro di traduzione
> dall'uomo alla macchina. Il possibile OS futuro non offre soltanto funzioni:
> mantiene un modello correggibile della persona e presenta gli stessi dati
> attraverso forme diverse, accessibili e contestuali. Il valore dipende dalla
> trasparenza e reversibilita' dell'adattamento, non dalla sua invisibilita'.

## Arco Storico Proposto

| Passaggio | Rapporto uomo-dato-macchina | Domanda progettuale |
| --- | --- | --- |
| Oralita', rito, manoscritto | Informazione legata a luogo, corpo, memoria e supporto unico | Chi puo' accedere e reinterpretare il dato? |
| Stampa ed editoria | Riproduzione e standardizzazione diffondono il dato | Cosa guadagniamo e perdiamo standardizzando la forma? |
| Numeri, archivi, interrogazioni | L'uomo deve formulare domande nel linguaggio del sistema | Quanto sapere tecnico serve per accedere all'informazione? |
| GUI, iOS, Android | Metafore visuali, touch e interaction design mediano la complessita' | Chi decide il modello di interazione valido per tutti? |
| Linguaggio naturale e OS adattivo | Il sistema interpreta intenzione, contesto e storia personale | Come evitare che interpretazione diventi manipolazione? |

Foligno, Quintana e Museo della Stampa e dell'Editoria possono diventare un
caso locale concreto per aprire l'arco storico: il dato pubblico passa da
evento, memoria e supporto materiale a riproduzione editoriale. Questa pista
richiede ricerca su fonti primarie prima di diventare argomento centrale.

## Quattro Assi Di Ricerca

### Uomo-macchina

Da comando esplicito a negoziazione continua. La macchina non esegue soltanto:
seleziona cosa mostrare, propone forme e costruisce un modello dell'utente.

### Uomo-linguaggi

Ogni interfaccia e' un linguaggio. CLI, query, icone, gesture e conversazione
distribuiscono diversamente potere e competenza tra persona e sistema.

### Informazione-numeri-interrogazioni

I dati non diventano conoscenza da soli. Schema, query e interfaccia decidono
quali domande sono facili, quali difficili e quali invisibili.

### Reale-digitale-teletrasporto

Usare "teletrasporto" come metafora operativa: la stessa entita' informativa
attraversa supporti e dispositivi cambiando forma, senza perdere identita' e
provenance. Non spostamento magico della materia, ma continuita' semantica tra
rappresentazioni.

## Il Rischio Del Linguaggio

Il linguaggio naturale rende il sistema accessibile, ma nasconde facilmente:

- schema e vincoli reali;
- ambiguita' interpretative;
- fonti e confidence;
- decisioni prese dal sistema;
- differenza tra desiderio dell'utente e inferenza della macchina.

Un OS conversazionale non deve sembrare onnisciente. Deve mostrare quando sta
interpretando, chiedere conferma quando serve e permettere di ispezionare o
correggere il modello personale.

## Principi Del Personal OS Accessibile

1. **Stesso dato, molte rappresentazioni.** Il contenuto resta stabile; forma,
   densita', modalita' e linguaggio possono adattarsi.
2. **Accessibilita' come adattamento, non modalita' speciale.** Il sistema
   risponde a capacita', contesto e preferenze senza creare un'esperienza di
   serie B.
3. **Inferenza non e' fatto.** Ogni adattamento appreso resta correggibile.
4. **Spiegabilita' operativa.** L'utente puo' chiedere: "Perche' lo vedo cosi'?"
5. **Reversibilita'.** Ogni trasformazione puo' essere annullata o congelata.
6. **Dati posseduti dall'utente.** Gli artifact importanti restano leggibili e
   modificabili fuori dal sistema intelligente.
7. **Personalizzazione senza paternalismo.** Il sistema propone e assiste; non
   decide quale esperienza l'utente dovrebbe desiderare.

## Prototipi Possibili

### Prototipo A - Interfacce Nel Tempo

Una stessa collezione di dati viene resa attraverso cinque paradigmi:
manoscritto/pergamena, pagina stampata, interrogazione testuale, smartphone
contemporaneo e vista adattiva.

Il prompt dimostrativo "visualizza il mio telefono come se fosse una pergamena
dell'800" diventa un test serio: quali funzioni sopravvivono, quali metafore
falliscono, quali azioni diventano piu' accessibili o meno comprensibili?

Output:

- installazione o web prototype comparativo;
- task identici eseguiti nelle diverse rappresentazioni;
- mappa delle trasformazioni che preservano o alterano il significato.

### Prototipo B - Adaptive Personal OS Shell

Una shell simulata cambia densita', gerarchia, input e modalita' in base a
contesto e preferenze apprese. Ogni cambiamento mostra una ragione, puo' essere
corretto e puo' essere annullato.

Esempi:

- passa da visuale a vocale quando le mani sono occupate;
- riduce densita' durante sovraccarico;
- espande dettagli per un utente esperto;
- mantiene una modalita' bloccata quando l'utente rifiuta l'adattamento.

Questo e' il prototipo principale consigliato: rende verificabile la tesi senza
costruire un vero sistema operativo.

### Prototipo C - Personal Data Mirror

Un modello personale longitudinale mostra dati, evidenze, confidence,
contraddizioni e adattamenti prodotti. Note, liste e progetti restano file
locali modificabili.

Obiettivo: verificare se un OS puo' personalizzarsi mantenendo leggibile il
rapporto tra dato originale, interpretazione e interfaccia risultante.

JARVIS e Muffin sono riferimenti utili per memoria, counterpoint, provenance,
knowledge artifact e controllo umano.

### Prototipo D - Teletrasporto Semantico

Esperimento speculativo secondario: un oggetto informativo passa tra stampa,
telefono, voce e spazio fisico mantenendo identita', storia e possibilita'
d'azione. Utile come installazione finale; troppo ampio come prototipo
principale.

## Perimetro Consigliato

Struttura tesi consigliata:

1. ricostruzione storico-critica del lavoro di traduzione tra uomo, supporto,
   linguaggio e macchina;
2. definizione del personal OS adattivo e dei suoi rischi;
3. Prototipo A come sonda storica;
4. Prototipo B come esperimento principale;
5. Prototipo C come verifica di trasparenza e controllo;
6. valutazione comparativa con utenti.

Non serve costruire un OS completo. Serve dimostrare una posizione:

> Un sistema diventa realmente personale non quando nasconde tutta la
> complessita', ma quando sa trasformarla per l'utente lasciandogli comprensione,
> scelta e proprieta'.

## Valutazione

Metriche e domande osservabili:

- comprensione del motivo di un adattamento;
- capacita' di correggerlo o annullarlo;
- tempo e successo sui task;
- carico cognitivo percepito;
- fiducia prima e dopo una spiegazione;
- differenze tra interfaccia statica e adattiva;
- percezione di controllo, accessibilita' e invasivita'.

## Domande Da Portare Al Relatore

- L'asse storico deve partire dalla storia locale di Foligno o da una storia
  generale delle interfacce?
- Il contributo principale e' interaction design, speculative design o critica
  dei sistemi adattivi?
- Quale popolazione rende verificabile il concetto di accessibilita'?
- Quanta parte di JARVIS puo' essere mostrata come caso tecnico senza spostare
  la tesi sul software engineering?
- "Teletrasporto semantico" chiarisce il progetto o distrae dalla domanda
  centrale?

## Relazioni

- [[GiustoDev_Muffin_Architecture]]
- [[Jarvis_Final_Feature_Vision]]
- [[Jarvis_User_Knowledge_Ontology]]
- [[Data_Privacy_Controls]]
- [[OpenHuman]]
