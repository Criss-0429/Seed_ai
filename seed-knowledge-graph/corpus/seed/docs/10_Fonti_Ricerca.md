# 10 - Registro delle fonti e tracciabilita delle decisioni

> Questo registro distingue **evidenza scientifica**, **preprint primari** e
> **repository di riferimento**. Nessuna singola fonte dimostra che SEED
> funzionera: le fonti motivano il disegno, mentre il protocollo di 14 giorni lo
> deve valutare.

## Come leggere il registro

- **Peer-reviewed:** pubblicato in una venue scientifica con revisione.
- **Preprint primario:** lavoro originale utile ma da trattare come evidenza
  provvisoria.
- **Reference implementation/design:** mostra un pattern pratico; non valida da
  solo efficacia o sicurezza.
- **Wiki locale:** sintesi operativa subordinata alle decisioni SEED.

## Mutazione, apprendimento e valutazione

| Fonte | Stato | Evidenza utile | Decisione SEED derivata |
|---|---|---|---|
| [Darwin Godel Machine](https://arxiv.org/abs/2505.22954) e [repo](https://github.com/jennyzzt/dgm) | preprint + reference implementation | Modifica iterativa del codice, archivio di agenti discendenti e validazione empirica; il repo avverte che codice generato non fidato puo essere distruttivo. | Lineage di discendenti, valutazione empirica e isolamento prima della promozione. |
| [AlphaEvolve](https://arxiv.org/abs/2506.13131) | preprint primario | Ricerca evolutiva guidata da uno o piu valutatori. | Spazio candidato aperto, ma ogni promozione dipende da valutatori espliciti. |
| [Automated Design of Agentic Systems](https://arxiv.org/abs/2408.08435) | preprint primario | Meta-agente che scopre agenti definiti in codice in uno spazio aperto e conserva scoperte. | Le categorie di mutazione descrivono, non limitano, lo spazio. |
| [AFlow](https://arxiv.org/abs/2410.10762) e [MetaGPT repo](https://github.com/FoundationAgents/MetaGPT) | paper indicato come ICLR 2025 Oral dal progetto | Workflow agentici ottimizzati come codice usando feedback di valutazione. | Workflow, routing e contratti sono oggetti evolutivi di prima classe. |
| [Voyager](https://arxiv.org/abs/2305.16291) e [repo](https://github.com/MineDojo/Voyager) | preprint + reference implementation | Curriculum automatico, skill library eseguibile crescente, feedback e self-verification. | Accumulare skill riutilizzabili con verifica, non generare sempre da zero. |
| [Reflexion](https://papers.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html) e [repo](https://github.com/noahshinn/reflexion) | NeurIPS 2023 | Feedback verbale ed episodic memory migliorano i tentativi successivi senza cambiare i pesi. | Reflection e memoria degli esiti possono guidare correzioni del runtime. |
| [Agent Workflow Memory](https://arxiv.org/abs/2409.07429) e [repo](https://github.com/zorazrw/agent-workflow-memory) | preprint + reference implementation | Induzione e riuso di workflow da esperienze precedenti. | I workflow personali devono essere estratti, verificati e versionati. |

## Personalita, relazione e memoria

| Fonte | Stato | Evidenza utile | Decisione SEED derivata |
|---|---|---|---|
| [Conversational Style Matching Agent](https://www.microsoft.com/en-us/research/publication/an-end-to-end-conversational-style-matching-agent/) | ACM IVA 2019 | Il matching di stile aumenta la fiducia per alcuni stili, non universalmente. | Matching selettivo; compatibilita non equivale a imitazione. |
| [PersonalLLM](https://arxiv.org/abs/2409.20296) | preprint primario | Persona prompting ad alto livello produce preferenze piu omogenee degli esseri umani; feedback personale e scarso. | Non costruire la persona con etichette generiche; usare evidenze idiosincratiche. |
| [On the Effectiveness of Creating Conversational Agent Personalities Through Prompting](https://arxiv.org/abs/2310.11182) | preprint primario | Le personalita definite da prompt non emergono sempre in modo distinto e affidabile. | La personalita e uno stato/versione valutabile, non solo un system prompt. |
| [From Fixed to Flexible](https://arxiv.org/abs/2601.08194) | preprint, studio esplorativo | Preferenze sulla personalita variano per contesto; regolabilita associata ad autonomia e fiducia. | Modalita contestuali separate dall'identita stabile. |
| [Efficient Personalization of Generative User Interfaces](https://arxiv.org/abs/2604.09876) | preprint primario | Forte divergenza delle preferenze; elicitation a coppie utile rispetto al prompting diretto. | Onboarding e valutazione includono confronti a coppie concreti. |
| [Sycophancy intervention](https://arxiv.org/abs/2308.03958) e [repo](https://github.com/google/sycophancy-intervention) | preprint + reference implementation | I modelli possono seguire la posizione dell'utente anche quando errata. | Counterpoint obbligatorio e metriche anti-compiacenza. |
| [Generative Agents](https://research.google/pubs/generative-agents-interactive-simulacra-of-human-behavior/) e [repo](https://github.com/joonspk-research/generative_agents) | UIST 2023 | Osservazione, pianificazione e riflessione contribuiscono al comportamento credibile. | Separare episodi, riflessione e pianificazione della relazione. |
| [MemGPT](https://arxiv.org/abs/2310.08560) e [Letta](https://github.com/letta-ai/letta) | preprint + reference implementation | Gestione gerarchica della memoria e agenti stateful multi-sessione. | Memoria personale stratificata, non dump indiscriminato del passato. |
| [PersonaMem-v2](https://arxiv.org/abs/2512.06688) | preprint primario | La personalizzazione implicita resta difficile; memoria compatta leggibile puo aiutare. | Conservare incertezze e rendere il profilo correggibile dall'utente. |
| [PersonaFeedback](https://arxiv.org/abs/2506.12915) | preprint primario | La personalizzazione implicita resta difficile e il solo retrieval non garantisce buone risposte personali. | Valutare l'esito della personalizzazione, non assumere che piu memoria equivalga a maggiore compatibilita. |
| [MIRIX](https://arxiv.org/abs/2507.07957) | preprint + reference architecture | Memoria modulare per assistenti personali persistenti. | Usare tipi di memoria distinti; non adottare il monitoraggio visuale come default perche amplia lo scope privacy. |

## Autonomia, controllo e interazione

| Fonte | Stato | Evidenza utile | Decisione SEED derivata |
|---|---|---|---|
| [Principles of Mixed-Initiative User Interfaces](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/chi99horvitz.pdf) | CHI 1999 | Gestire incertezza, attenzione, utilita attesa, costo degli errori, invocazione e terminazione dirette. | Proattivita contestuale, soglie di intervento, controllo e rollback visibili. |
| [OpenHarness](https://github.com/HKUDS/OpenHarness) | reference implementation | Harness come combinazione governata di strumenti, conoscenza, osservazione, azione e permessi. | Evolvere l'harness come sistema, mantenendo governance e dry-run. |
| [Muffin public docs](https://github.com/GiustoPiedimonte/muffin-public-docs), [memoria](https://github.com/GiustoPiedimonte/muffin-public-docs/blob/main/03-memoria.md), [identita](https://github.com/GiustoPiedimonte/muffin-public-docs/blob/main/04-identita.md) | design reference | Separazione tra identita stabile, profilo vivo dell'utente e self-narrative; counterpoint. | Modello a cinque componenti in `09_Personalita_Compatibile.md`. |

## Collegamenti alla LLM Wiki locale

Le seguenti pagine sono contesto operativo, non autorita superiore ai documenti
SEED:

| Wiki | Uso in SEED |
|---|---|
| [Runtime Harness Adaptation](../../JarvisDocs/LLM_Wiki/wiki/Runtime_Harness_Adaptation.md) | Adattare contratti, skill, action realization e traiettorie. |
| [Cognitive User Model & Execution Harness](../../JarvisDocs/LLM_Wiki/wiki/Jarvis_Cognitive_User_Model_Execution_Harness.md) | Loop osserva-pesa-capisce-dubita-corregge-agisce-osserva effetto. |
| [User Knowledge Ontology](../../JarvisDocs/LLM_Wiki/wiki/Jarvis_User_Knowledge_Ontology.md) | Separazione tra fatti, pattern, ipotesi e segnali affettivi. |
| [Memory Architecture](../../JarvisDocs/LLM_Wiki/wiki/Jarvis_Memory_Architecture.md) | Memoria con provenance, selezione e writeback governato. |
| [Agent Harness Best Practices](../../JarvisDocs/LLM_Wiki/wiki/Agent_Harness_Best_Practices.md) | Determinismo prima del modello, action contract, verifica e audit. |
| [OpenHarness](../../JarvisDocs/LLM_Wiki/wiki/OpenHarness.md) | Harness adattabile e governato. |
| [Personal OS Thesis Direction](../../JarvisDocs/LLM_Wiki/wiki/Personal_OS_Thesis_Direction.md) | Trasparenza, reversibilita e controllo come qualita centrali. |
| [Personal Assistant Repo Scouting](../../JarvisDocs/LLM_Wiki/wiki/Personal_Assistant_Repo_Scouting.md) | Orientamento tra implementazioni esistenti. |

## Limiti di trasferibilita

- Benchmark di coding agent non equivalgono a uso personale quotidiano.
- Risultati in ambienti simulati non dimostrano sicurezza sul desktop reale.
- Studi brevi sulla personalita non dimostrano compatibilita longitudinale.
- Repository pubblici possono contenere decisioni non validate o superfici di
  rischio non adatte a SEED.
- Preprint recenti possono cambiare dopo revisione.

Per questo SEED tratta ogni fonte come input progettuale e ogni decisione come
ipotesi da verificare nel protocollo descritto in `06_Esperimento.md`.

## Provider modello e voce

| Fonte | Stato | Decisione SEED derivata |
|---|---|---|
| [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling) e [structured outputs](https://docs.ollama.com/capabilities/structured-outputs) | documentazione provider primaria | Modelli per ruolo devono essere benchmarkati anche su tool call e output validabile. |
| [Ollama Cloud](https://docs.ollama.com/cloud) | documentazione provider primaria | Structured outputs non disponibili nel cloud: output reviewer validato localmente; errore produce `inconclusive`. |
| [qwen3-coder-next](https://ollama.com/library/qwen3-coder-next), [gpt-oss](https://ollama.com/library/gpt-oss), [nemotron-3-super](https://ollama.com/library/nemotron-3-super) | model card/provider registry | Baseline candidate separate per builder, reviewer e fallback; selezione finale dipende da benchmark SEED. |
| [ElevenLabs authentication](https://elevenlabs.io/docs/api-reference/authentication), [STT](https://elevenlabs.io/docs/capabilities/speech-to-text), [TTS](https://elevenlabs.io/docs/capabilities/text-to-speech) | documentazione provider primaria | Voice opzionale con chiave scoped in core config, consenso separato, retention minima e fallback testuale. |
