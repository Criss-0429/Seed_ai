# J.A.R.V.I.S. v6.3 - Stack Tecnologico e Costi

> **Ultimo aggiornamento:** 1 maggio 2026
> **Stato:** Documento operativo canonico

Questo documento descrive lo stack raccomandato per un JARVIS realmente usabile in produzione, includendo costi realistici per uso personale e per uso intensivo da developer/admin.

---

## 1. Stack Locale e Infrastrutturale

### 1.1 Control Plane

| Componente | Ruolo | Costo tipico |
|---|---|---|
| **VPS Hetzner CAX11** | orchestrazione, webhook, audit, scheduler, side services | ~`EUR 4.49 / mese` |
| **Caddy** | reverse proxy HTTPS | `EUR 0` |
| **n8n** | workflow, cron, approval loop, integrazioni | `EUR 0` self-hosted |
| **OpenClaw** | orchestratore agente principale | `EUR 0` custom runtime |
| **PostgreSQL** | stato workflow, audit, registro eventi | `EUR 0` in Docker |

### 1.2 Execution Plane Locale

| Componente | Ruolo | Costo API |
|---|---|---|
| **Ollama** | modelli locali e fallback | `EUR 0` |
| **OpenAI Privacy Filter** | PII detection/redaction locale e privacy gate | `EUR 0` |
| **Whisper / faster-whisper** | STT locale | `EUR 0` |
| **Kokoro-82M** | TTS locale | `EUR 0` |
| **nomic-embed-text** | embedding locali | `EUR 0` |
| **Neural Composer** | graph memory locale | `EUR 0` |
| **M3 Memory** | memoria locale e retrieval | `EUR 0` |
| **Bitwarden CLI / SOPS** | segreti runtime | `EUR 0` self-hosted |
| **Tailscale** | rete privata tra VPS e Home Node | `EUR 0` nel free tier |

### 1.3 User Knowledge e Ambient Layer

| Componente | Ruolo | Costo tipico |
|---|---|---|
| **User Knowledge Ontology** | fatti, stati, routine, pattern, preferenze, relazioni, ipotesi e confini | `EUR 0` |
| **Salience Engine** | scoring deterministico per decidere cosa ricordare, ignorare o rendere proattivo | `EUR 0` |
| **Proactivity Queue interna** | candidati proattivi con evidenza, confidenza, timing e policy | `EUR 0` |
| **Home Assistant / MQTT** | layer opzionale per luci, stanze, musica, presenza e device locali | `EUR 0` self-hosted |
| **Matter / Thread** | standard opzionale per device smart compatibili | dipende dai device |
| **PWA via Tailscale** | accesso mobile/desktop privato senza dipendere da Electron | `EUR 0` nel free tier |
| **Tauri/Electron shell opzionale** | wrapper desktop solo se servono integrazioni native | `EUR 0` software, costo manutenzione |

Questi componenti non sono tutti necessari per il primo prototipo. Sono la direzione finale per JARVIS come personal operating ecosystem.

---

## 2. Gateway Cloud Canonico

Decisione architetturale:
**OpenRouter resta il gateway cloud principale** perche consente:
- multi-provider con un solo endpoint;
- fallback e sorting per prezzo/latenza;
- controllo puntuale di costi e provider;
- sostituzione veloce dei modelli senza cambiare la logica alta.

Il cloud non deve fare tutto. Deve fare bene solo cio che e davvero piu efficiente nel cloud.

---

## 3. Lanes Modello Raccomandate

Prezzi verificati il **28 aprile 2026**.

| Lane               | Provider               | Modello canonico                                | Prezzo ufficiale                          | Uso raccomandato                                    |
| ------------------ | ---------------------- | ----------------------------------------------- | ----------------------------------------- | --------------------------------------------------- |
| **privacy**        | locale                 | `openai/privacy-filter`                        | `EUR 0`                                   | PII filter/redaction, privacy gate locale           |
| **chat**           | OpenRouter             | `google/gemini-3.1-flash-lite-preview-20260303` | `$0.25 / 1M input`, `$1.50 / 1M output`   | chat quotidiana, coordinamento, update rapidi       |
| **research_fast**  | OpenRouter             | `openai/gpt-oss-120b`                           | `$0.039 / 1M input`, `$0.19 / 1M output`  | ragionamento, confronto fonti, ricerca sintetica    |
| **docs**           | OpenRouter             | `openai/gpt-oss-120b`                           | `$0.039 / 1M input`, `$0.19 / 1M output`  | documentazione, preventivi, offerte, report         |
| **coding**         | OpenRouter             | `qwen/qwen3-coder-next-2025-02-03`              | `$0.15 / 1M input`, `$0.80 / 1M output`   | refactor, debug, patch, test                        |
| **coding_premium** | OpenRouter             | `moonshotai/kimi-k2.5`                          | `$0.3827 / 1M input`, `$1.72 / 1M output` | coding lungo, repo grandi, task complessi           |
| **fallback**       | OpenRouter             | `meta-llama/llama-4-scout`                      | `$0.08 / 1M input`, `$0.30 / 1M output`   | backup rapido ed economico                          |
| **manual_premium** | Anthropic / OpenRouter | `Claude Sonnet 4`                               | `$3 / 1M input`, `$15 / 1M output`        | escalation esplicita, non automatica                |

### 3.1 Modelli da non usare come default globale

- `Claude Sonnet`
- `Kimi K2.5`
- qualunque modello con web search nativa sempre accesa

Questi modelli hanno senso come escalation, non come base continua del runtime.

---

## 4. Costo Tipico per Richiesta

Assunzioni:
- **chat**: `4k input + 600 output`
- **deep/docs**: `12k input + 1.5k output`
- **coding**: `40k input + 4k output`

| Lane | Costo tipico per richiesta |
|---|---|
| `chat` con Gemini 3.1 Flash Lite | `~$0.0019` |
| `research_fast` / `docs` con gpt-oss-120b | `~$0.00075` |
| `coding` con Qwen3-Coder-Next | `~$0.0092` |
| `coding_premium` con Kimi K2.5 | `~$0.0222` |
| `manual_premium` con Sonnet 4 su task deep | `~$0.0585` |
| `manual_premium` con Sonnet 4 su task coding | `~$0.18` |

Interpretazione:
- il costo vero del runtime non e nella conversazione rapida;
- il costo sale quando aumentano output, search e coding premium;
- il premium deve essere sorvegliato con guardrail, non solo con buon senso.

---

## 5. Search Layer Raccomandato

JARVIS developer-oriented non deve appoggiarsi sempre al search nativo del modello.

| Provider | Uso | Prezzo ufficiale | Nota architetturale |
|---|---|---|---|
| **Tavily** | ricerca standard | `$0.008 / credit`; basic search `1 credit`, advanced `2 credits` | default economico |
| **Exa Search** | ricerca premium e coding/docs search | `$7 / 1k search requests`; `Answer` `$5 / 1k`; `Deep Search` `$12 / 1k` | piu adatto a docs/coding grounding |
| **Exa Research** | ricerca lunga e strutturata | `$5 / 1k searches`, `$5 / 1k pages read`, `$5 / 1M reasoning tokens` su `exa-research` | da usare solo su task che lo richiedono |
| **Provider-native search** | search integrata nel modello | variabile, spesso piu cara | tenere disabilitata come default |

Decisione canonica:
- **Tavily** per la maggior parte delle query web;
- **Exa** per ricerche piu specializzate o documentali;
- search nativa del modello solo se davvero conviene in qualita o UX.

---

## 6. Profili Mensili Realistici

### 6.1 Profilo "Assistente personale ottimizzato"

- chat prevalente
- poche ricerche
- poco coding
- memoria e voce locali

**Costo cloud tipico:** `~$8-$15 / mese`

### 6.2 Profilo "Developer bilanciato"

- molto software
- documentazione frequente
- ricerca online regolare
- coding premium occasionale

**Costo cloud tipico:** `~$15-$25 / mese`

### 6.3 Profilo "Developer intenso"

- molte code session
- task lunghi
- ricerca tecnica frequente
- preventivi, documenti, confronti multipli

**Costo cloud tipico:** `~$25-$40 / mese`

### 6.4 Profilo "Premium poco governato"

- premium usato quasi sempre
- search nativa troppo frequente
- grandi contesti rimandati in loop

**Costo cloud tipico:** `>$40 / mese`, facilmente molto oltre

---

## 7. Guardrail di Budget

JARVIS deve implementare policy tecniche, non solo stime:

1. **Ack immediato su lane economico o locale**
   Il "ti aggiorno subito" non deve passare da un modello premium.

2. **Escalation esplicita**
   `coding_premium` e `manual_premium` si attivano con soglie di complessita o richiesta utente.

3. **Search budget separato**
   Search provider e LLM non devono condividere lo stesso pool mentale di costo.

4. **Context cap**
   Non reinviare sempre l'intera memoria, l'intera wiki o l'intera codebase.

5. **Premium cooldown**
   Dopo una o piu escalation costose, il router deve tornare alla corsia standard per i task successivi, salvo nuova motivazione.

6. **Monthly spend classes**
   Ogni lane deve loggare spesa stimata per permettere a OpenClaw di cambiare strategia se il budget sale troppo.

7. **Use math before AI**
   Salienza, presenza, routing, deduplica, conflitti calendario, routine, costi e policy devono usare algoritmi prima di chiamare un LLM.

8. **Ambient autonomy caps**
   Azioni ambientali reversibili come luci o musica possono avere maggiore autonomia; azioni esterne, sociali o distruttive restano soggette ad approval.

---

## 8. MODEL_MAP Canonico

Questa e la mappa consigliata per l'evoluzione dell'attuale provider OpenRouter:

```python
MODEL_MAP = {
    "chat": "google/gemini-3.1-flash-lite-preview-20260303",
    "deep": "openai/gpt-oss-120b",
    "fallback": "meta-llama/llama-4-scout",
    "coding": "qwen/qwen3-coder-next-2025-02-03",
}
```

Mappa opzionale per le escalation:

```python
OPTIONAL_MODEL_MAP = {
    "coding_premium": "moonshotai/kimi-k2.5",
    "manual_premium": "anthropic/claude-sonnet-4",
}
```

---

## 9. Interpretazione Corretta del Vecchio "EUR 7 / mese"

Il vecchio numero era utile solo come:
- profilo minimale di inferenza;
- dimostrazione che il routing intelligente abbatte i costi;
- scenario non developer-heavy.

Non deve piu essere presentato come TCO universale di produzione.

Per un admin/developer come Cristian, il budget corretto da considerare e:
- `~$15-$25 / mese` come target sano;
- `~$25-$40 / mese` come utilizzo molto intenso ma ancora governato.

---

## 10. Conclusione Operativa

Lo stack consigliato per JARVIS operativo e:
- locale per privacy, memoria, STT, TTS, embeddings;
- OpenRouter come gateway principale;
- Gemini 3.1 Flash Lite per chat e interaction shell;
- gpt-oss-120b per reasoning, docs e ricerca;
- Qwen3-Coder-Next per coding standard;
- Kimi K2.5 solo per coding premium;
- Tavily ed Exa come search layer esterno;
- Sonnet 4 solo come escalation manuale.
- User Knowledge Ontology e salience engine come layer cognitivo;
- PWA/Tailscale e ambient layer opzionale per estendere JARVIS oltre la macchina.

Questo e il miglior equilibrio oggi tra:
**potenza reale, costo accessibile, controllo operativo e fluidita conversazionale**.
