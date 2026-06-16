# J.A.R.V.I.S. v6.3 - Panoramica Master del Sistema

> **Ultimo aggiornamento:** 1 maggio 2026
> **Stato:** Documento canonico - Architettura di produzione Master v6.3
> **Versione:** 6.3 (Personal Operating Ecosystem)

---

## 1. Sintesi

**J.A.R.V.I.S.** e un ecosistema operativo personale ibrido che unisce memoria locale, privacy by design, orchestrazione multi-modello, conoscenza dell'utente, automazioni ambientali autorizzate e una UX conversazionale continua.

La direzione canonica v6.3 e:

**JARVIS non e solo un assistente da lavoro: e un personal operating ecosystem.**

Deve poter collegare computer, casa, telefono, voce, routine, progetti, relazioni, strumenti e agenti in un sistema unico, governato e osservabile quando serve.

Per i task iniziati dall'utente resta valida una regola semplice:

**JARVIS non lavora mai in silenzio.**

Quando riceve una richiesta:
1. risponde subito con una conferma naturale;
2. mostra avanzamento mentre orchestra ricerca, memoria o coding;
3. usa il modello specializzato solo per il lavoro vero;
4. restituisce un output finale chiaro, con tono umano e coerente.

Questo non significa che JARVIS debba parlare sempre. Nei processi interni di conoscenza, pattern recognition e proattivita', il silenzio e' una feature. JARVIS parla solo quando salienza, evidenza e timing lo giustificano.

Questo sposta JARVIS da un semplice schema "tri-brain/quad-brain" verso un runtime piu realistico:
- **conversation-first** sul piano UX;
- **multi-lane routing** sul piano inferenziale;
- **capability evolution live** sul piano operativo;
- **user-knowledge driven** sul piano cognitivo;
- **ambient-aware** sul piano ecosistemico.

---

## 2. Principi Fondamentali

1. **Conversation First**
   JARVIS deve dare un primo feedback entro poche centinaia di millisecondi. Anche durante task lunghi, l'utente deve vedere o sentire aggiornamenti intermedi.

2. **Hybrid Orchestration**
   Il lavoro e diviso tra Control Plane remoto, Execution Plane locale e gateway cloud pay-as-you-go. I task semplici o sensibili restano locali; quelli complessi scalano al cloud.

3. **Privacy By Design**
   Dati sensibili, memoria, voice I/O e contesto personale restano il piu possibile sul nodo locale. Il cloud riceve solo payload necessari e redatti.

4. **Cost-Aware Specialization**
   Nessun modello premium viene usato come default globale. Ogni corsia del router ha un costo massimo e una responsabilita precisa.

5. **Memory As Source Of Truth**
   La memoria di lavoro e a cascata: wiki, M3 Memory, knowledge graph, retrieval tecnico e diario agentico devono convergere in un unico ecosistema coerente.

6. **Live Capability Evolution**
   JARVIS deve poter aggiungere skill, workflow, connettori e operatori con aggiornamenti modulari e caricamento progressivo, senza richiedere ogni volta spegnimento completo del sistema.

7. **User Knowledge as Open Ontology**
   JARVIS deve modellare l'utente con una ontologia aperta: fatti, stati, routine, pattern, preferenze, relazioni, eccezioni, ipotesi e confini. Palestra, universita, famiglia, partner o luci accese sono esempi, non feature hardcoded.

8. **Proactivity Must Be Earned**
   La proattivita non e una proposta banale a fine task. Deve nascere da evidenza, salienza, policy e conoscenza del contesto. Se non c'e una ragione forte, JARVIS tace.

9. **Ambient Intelligence With Boundaries**
   L'ambiente fisico autorizzato fa parte dell'ecosistema: luci, musica, presenza, telefono, routine e scene. Ogni integrazione ambientale deve avere confini, audit, reversibilita quando possibile e consenso.

---

## 3. Planes e Trust Zones

| Plane / Zona | Componenti principali | Ruolo |
|---|---|---|
| **Interaction Plane** | Frontend React/Electron, Telegram, TTS, status stream | Primo contatto conversazionale, feedback immediato, UX naturale |
| **Control Plane** | n8n, OpenClaw, PostgreSQL, scheduler, audit trail | Orchestrazione, workflow, deleghe, policy, cron |
| **Execution Plane** | Ollama, Whisper, Kokoro, M3 Memory, LLM Wiki, Neural Composer, filesystem locale | Privacy, memoria, voce, retrieval, strumenti locali |
| **External API Plane** | OpenRouter, search API, provider premium opzionali | Ragionamento, coding, ricerca e fallback cloud |
| **User Knowledge Plane** | ontologia utente, pattern memory, routine, relazioni, osservazioni mature | Conoscere l'utente in modo evidence-based e correggibile |
| **Ambient Plane** | Home Assistant/MQTT/Matter opzionali, telefono, presenza, musica, luci | Collegare JARVIS all'ambiente fisico autorizzato |

Le trust zones restano tre:
- **Locale/alta fiducia**: memoria, file, segreti, PII, voice.
- **Remoto controllato**: orchestrazione, audit, workflow, code staging.
- **Internet/bassa fiducia**: modelli cloud, search provider, SaaS esterni.

---

## 4. Runtime Lanes Canoniche

Il router non deve piu essere descritto come una sola piramide di modelli. In produzione, JARVIS usa corsie specializzate:

| Lane | Modello / Stack canonico | Ruolo |
|---|---|---|
| **interaction_shell** | locale leggero oppure `Gemini 3.1 Flash Lite` | Conferma immediata, status update, continuita conversazionale |
| **privacy** | `openai/privacy-filter` locale | Rilevamento e mascheramento PII, gating locale, classificazione sensibile |
| **chat** | `google/gemini-3.1-flash-lite-preview-20260303` via OpenRouter | Conversazione quotidiana, coordinamento, task semplici |
| **research_fast** | `gpt-oss-120b` + search esterna | Analisi, confronto fonti, risposte aggiornate, reasoning economico |
| **docs** | `gpt-oss-120b` come default; finitura opzionale con modello editoriale piu forte | Documentazione, preventivi, offerte, sintesi strutturate |
| **coding** | `qwen/qwen3-coder-next-2025-02-03` via OpenRouter | Refactor, patch, debug, test e lavoro tecnico standard |
| **coding_premium** | `moonshotai/kimi-k2.5` via OpenRouter | Task lunghi, codebase grandi, sessioni difficili |
| **fallback** | `meta-llama/llama-4-scout` via OpenRouter | Backup veloce e poco costoso |
| **manual_premium** | `Claude Sonnet 4` o harness premium equivalente | Escalation esplicita, non automatica |

**Decisione architetturale chiave:**
il premium non deve essere il percorso standard. Deve essere un'eccezione, attivata solo quando il lane standard non basta.

---

## 5. Search Policy Canonica

JARVIS deve saper fare ricerca online, ma non deve usare sempre il search nativo del modello.

Scelta raccomandata:
- **Tavily** come ricerca standard economica e veloce;
- **Exa** come ricerca premium per analisi piu profonde o developer research su docs e codice;
- ricerca nativa del provider LLM solo quando serve un output unico tightly-coupled con il modello.

Questa scelta abbassa il costo e migliora il controllo:
- ricerca e raccolta fonti separate;
- compressione del contesto prima del modello;
- reasoning applicato solo sul materiale gia filtrato.

---

## 6. Memoria e Retrieval

La memoria operativa di JARVIS continua a poggiare su quattro elementi:

1. **LLM Wiki (Obsidian)**
   Source of Truth editoriale e semantica.

2. **M3 Memory**
   Memoria locale a retrieval rapido per cronologia, note, frammenti e contesto conversazionale.

3. **Neural Composer / Graph Memory**
   Grafo locale per relazioni tra concetti, entita e procedure.

4. **Knowledge Extraction Layer**
   Processo che aggiorna wiki, grafo, note operative e registro capacita dopo task rilevanti.

5. **User Knowledge Ontology**
   Layer cognitivo che distingue fatti, stati, routine, pattern, preferenze, relazioni, eccezioni, ipotesi e confini. Non e una dashboard: e un processo interno con viste solo per audit, consenso e correzione.

Decisione nuova:
**la memoria deve registrare anche le nuove capacita apprese da JARVIS e la conoscenza utente rilevante**, non solo contenuti e cronologia.

Le inferenze personali delicate non diventano automaticamente verita. Devono maturare, accumulare evidenza o chiedere conferma.

---

## 7. Ecosistema Agenti e Harness

Il runtime pubblico non coincide con tutti gli harness di sviluppo.

- **OpenClaw** resta il cervello operativo 24/7.
- **n8n** resta il backbone di eventi, trigger, integrazioni e approvazioni.
- **Hermes**, **OpenCode**, **Jules**, **Codex**, **Claude Code** e harness simili non devono stare sempre nel loop pubblico: entrano come strumenti specializzati di capability forge, code engineering o esecuzione remota.

La divisione canonica e:
- **runtime harness**: OpenClaw + n8n + MCP + tool locali;
- **capability forge**: harness che costruiscono o aggiornano skill, plugin, workflow, parser, connector;
- **premium code harness**: usati solo quando la complessita tecnica lo giustifica.

Documento di riferimento dedicato:
`Docs/JARVIS_v6_AGENT_ECOSYSTEM.md`

### Skill Intake e Capability Forge Safety

Le nuove skill, plugin, hook, MCP config e collezioni agentiche non entrano direttamente nel runtime pubblico.

Decisione canonica:
- i cataloghi esterni sono **fonti di scouting**, non dipendenze da installare in blocco;
- ogni skill passa da security audit, sandbox test e registrazione capability;
- Repomix o strumenti equivalenti possono creare snapshot selettivi del codebase per review e onboarding agentico;
- il forge segue un quality gate: research -> plan -> execute -> review -> verify -> record;
- Flowise e LangChain restano riferimenti/laboratori, non sostituti di n8n + OpenClaw + MCP.

### Influenza di Microsoft JARVIS (HuggingGPT)

Tra i riferimenti esterni, `microsoft/JARVIS` e utile soprattutto per tre motivi:
- formalizza un flusso **planner -> selector -> executor -> response**;
- mostra il valore di un **task graph esplicito** con dipendenze e argomenti;
- rende visibili i risultati intermedi con endpoint separati per piano e risultati.

Decisione di integrazione:
- il nostro JARVIS **non** adottera un model swarm generico stile Hugging Face Hub come runtime standard;
- adottera invece l'idea di **Task Graph IR** come formato interno per richieste complesse;
- usera questa struttura per progress narration, audit, capability forge e debug admin.

---

## 8. Profili di Costo Realistici

Il vecchio numero "circa 7 euro/mese" va interpretato come **profilo minimale di inferenza**, non come profilo reale da developer/admin intensivo.

Profili canonici:

| Profilo | Costo cloud realistico | Descrizione |
|---|---|---|
| **Assistente personale ottimizzato** | ~`$8-$15 / mese` | Chat, memoria, ricerca leggera, voce locale |
| **Developer bilanciato** | ~`$15-$25 / mese` | Coding frequente, docs, preventivi, ricerca web |
| **Developer intenso** | ~`$25-$40 / mese` | Molti task tecnici, ricerca ripetuta, escalation mirate |
| **Premium poco governato** | `>$40 / mese` | Troppo premium automatico, troppa ricerca nativa, contesto enorme |

Questi valori non includono:
- VPS/cloud di supporto;
- elettricita del nodo locale;
- eventuali tool premium esterni;
- costo di tempo umano.

---

## 9. Comportamento Canonico della Conversazione

Ogni task importante deve seguire questo schema:

1. **Ack immediato**
   "Certo, controllo subito."

2. **Aggiornamento visibile**
   "Sto confrontando due fonti ufficiali."

3. **Esecuzione specialistica**
   Search, retrieval, coding, orchestrazione o tool use.

4. **Risposta finale**
   Sintesi utile, naturale, con livello di dettaglio adeguato.

In altre parole:
**JARVIS non deve essere silenzioso, ma nemmeno verboso.**

---

## 10. Documenti Canonici Correlati

- `VISION.md`
- `MISSION.md`
- `DESIGN_PRINCIPLES.md`
- `Docs/JARVIS_v6_STACK.md`
- `Docs/JARVIS_v6_WORKFLOW.md`
- `Docs/JARVIS_v6_IMPLEMENTATION.md`
- `Docs/JARVIS_v6_AGENT_ECOSYSTEM.md`
- `Docs/MindMap/SubAgenti.canvas`
- `Docs/MindMap/Architettura_Generale.canvas`

---

Questa panoramica sostituisce la lettura rigida del vecchio tri-brain/quad-brain con una architettura piu realistica: **conversation-first, multi-lane, cost-aware, live-upgradable, user-knowledge driven e ambient-aware**.
