# 13 - Model Roles, Design Governor e Voice Plan

> **Stato:** S10.1-S10.5, S11.1 backend voce e S11.2 emotion implementati e
> verificati. S11.3 pannello voce resta nella futura fase UI U3. I gate owner
> restano invariati.

## Knowledge graph

Questo piano e collegato semanticamente a documenti ufficiali JARVIS e LLM Wiki
nel grafo specifico
[`../seed-knowledge-graph/graphify-out/GRAPH_REPORT.md`](../seed-knowledge-graph/graphify-out/GRAPH_REPORT.md).
Il corpus ponte esplicita autorita e relazioni in
[`../seed-knowledge-graph/corpus/00_CORPUS_BRIDGES.md`](../seed-knowledge-graph/corpus/00_CORPUS_BRIDGES.md).

## Obiettivo

SEED non deve usare un solo modello per conversare, costruire software e
giudicare se quel software rispetta SEED. Questi lavori richiedono contesti,
prompt, budget e autorita diversi.

Ruoli previsti:

| Ruolo | Responsabilita | Modello iniziale candidato |
|---|---|---|
| `conversation` | testo, conversazione, personality runtime, sintesi finale | `gemma4:31b` |
| `tool_builder` | proposta e costruzione isolata di tool/descendant | `qwen3-coder-next` |
| `design_reviewer` | review indipendente contro direttive SEED | `gpt-oss:120b` |
| `design_reviewer_fallback` | seconda opinione o fallback reviewer | `nemotron-3-super` |

Questi nomi sono baseline da valutare, non dipendenze permanenti. Tutti sono
presenti nel catalogo Ollama Cloud verificato con la chiave SEED il
`2026-06-12`.

## Separazione delle autorita

```text
richiesta / evidenza
-> conversation model formula problema
-> tool_builder genera candidate isolata
-> controlli deterministici verificano schema, scope, segreti e invarianti
-> design_reviewer confronta artefatti con direttive SEED
-> evaluator indipendenti producono evidenze
-> promotion authority + owner gate decidono
```

Regole:

- `tool_builder` non promuove cio che costruisce;
- `design_reviewer` non modifica artefatti durante la review;
- `design_reviewer` non approva, promuove o cambia direttive;
- review LLM e evidenza fallibile, non sostituisce test, permission contract,
  privacy gate, lineage, rollback o owner gate;
- modello conversazionale non riceve automaticamente intera codebase,
  lineage o segreti;
- ogni ruolo ha credenziali, timeout, budget, context cap e fallback espliciti;
- cambio modello e decisione configurata e auditata, non mutazione silenziosa.

## Perche questi candidati iniziali

### Conversation: `gemma4:31b`

- gia verificato praticamente con SEED;
- supporta vision, tool calling e system prompt;
- adatto a conversazione multimodale e contesto lungo;
- mantiene continuita durante test S8.

Non deve costruire o giudicare da solo tool complessi. Continuita
conversazionale e competenza di coding sono obiettivi diversi.

### Tool builder: `qwen3-coder-next`

- modello agentic coding disponibile su Ollama;
- supporta tool calling e contesto lungo;
- uso risorse dichiarato medio, piu adatto a loop frequenti rispetto ai
  modelli coder massimi;
- deve lavorare solo nel lab isolato, su scope e contratti tipizzati.

Fallback/escalation da confrontare:

- `devstral-2:123b`: candidato per task repository-scale complessi;
- `qwen3-coder:480b`: escalation costosa per casi non risolti;
- nessuna escalation automatica senza budget e motivazione registrati.

### Design reviewer: `gpt-oss:120b`

- famiglia diversa dal coder, utile per ridurre errori correlati;
- reasoning e tool use adatti a review di contratti e artefatti;
- deve ricevere direttive canoniche, diff/manifest, risultati test e rischi,
  non una richiesta vaga di "controllare tutto".

Fallback `nemotron-3-super`: seconda famiglia, pensata anche per agenti
collaborativi e instruction following. Utile per disaccordi o indisponibilita
del reviewer primario.

Nota Ollama Cloud: structured outputs non sono attualmente supportati nel
cloud. Output reviewer deve quindi essere validato localmente contro schema
JSON; parsing o campi mancanti producono `inconclusive`, mai `pass`.

## Design Directive Pack

Reviewer non legge documenti casuali. Riceve un pack versionato e hashato:

1. `00_Visione_Prodotto.md`
2. `01_Architettura.md`
3. `03_PrivacyGate.md`
4. `04_Sandbox_Sicurezza.md`
5. `09_Personalita_Compatibile.md`
6. `11_Contratto_Mutazione.md`
7. feature context pack attivo in `12_ImplementationPlan.md`
8. manifest candidate, permission delta, diff, test report e rollback plan

Il pack conserva:

- `directive_pack_version`;
- hash di ogni fonte;
- feature e scope attivi;
- direttive obbligatorie;
- assunzioni e conflitti noti.

Se fonte canonica cambia, review precedente diventa stale.

## Contratto output reviewer

Output proposto:

```json
{
  "review_version": "seed.design-review.v1",
  "candidate_id": "uuid",
  "directive_pack_version": "sha256",
  "verdict": "pass|fail|inconclusive",
  "violations": [
    {
      "directive_id": "privacy.remote_payload_minimal",
      "severity": "blocking|high|medium|low",
      "evidence_ref": "diff:path:line",
      "reason": "testo breve"
    }
  ],
  "missing_evidence": [],
  "recommended_checks": [],
  "model": "gpt-oss:120b"
}
```

Un `pass` del reviewer non basta per promotion. Un `fail` blocking ferma il
candidate finche risolto o esplicitamente respinto dall'owner con audit.

## Selezione e sostituzione modelli

SEED seleziona modelli tramite benchmark riproducibile, non impressione.

### Corpus minimo

- conversazione italiana breve, lunga e ambigua;
- personality/counterpoint senza mirroring;
- tool calling valido e tool inesistente;
- costruzione tool semplice e multi-file;
- rispetto sandbox, permission delta e secret handling;
- review con violazione nota, nessuna violazione e conflitto tra direttive;
- prompt injection in file, web result e candidate;
- timeout, errore provider e risposta JSON invalida.

### Metriche per ruolo

| Ruolo | Metriche principali |
|---|---|
| conversation | utilita, tono, counterpoint, latenza, costo, tool accuracy |
| tool_builder | build pass, test pass, scope leakage, segreti, rollback |
| design_reviewer | recall violazioni blocking, falsi positivi, evidence refs, indipendenza |

Regole selezione:

- benchmark cieco dove possibile;
- stesso corpus e budget per candidati;
- nessun modello giudica da solo se stesso;
- conservare fronte multi-obiettivo, non singolo score;
- sostituzione modello passa da shadow e canary;
- regressione privacy/sicurezza blocca sostituzione.

## Routing previsto

```text
normale conversazione -> conversation
richiesta tool nuova -> conversation formula candidate contract
candidate contract completo -> tool_builder nel lab
artefatti + test -> design_reviewer
review dubbia/inconclusive -> deterministic checks + reviewer fallback
promotion -> authority separata + owner gate richiesto dal rischio
```

Modello reviewer puo essere chiamato anche su mutazioni non-code: prompt,
personality policy, routing, memoria, evaluator e supervisor. Maggiore impatto
richiede maggiore indipendenza.

## Configurazione proposta

Questa e struttura target documentale, non config implementata:

```json
{
  "models": {
    "provider": "ollama",
    "base_url": "https://ollama.com/v1",
    "api_key": "<secret-in-core_config>",
    "roles": {
      "conversation": "gemma4:31b",
      "tool_builder": "qwen3-coder-next",
      "design_reviewer": "gpt-oss:120b",
      "design_reviewer_fallback": "nemotron-3-super"
    },
    "policy": {
      "fail_closed_roles": ["design_reviewer"],
      "record_model_per_call": true,
      "allow_automatic_premium_escalation": false
    }
  }
}
```

Chiave resta solo in `%LOCALAPPDATA%\SEED\core_config\config.json`, mai in repo,
prompt, trace, report o lineage. Audit registra provider/modello/ruolo, non
segreto.

## Piano implementativo S10 - Model Role Separation And Design Governor

Implementare dopo S9:

1. introdurre config typed per ruoli e policy;
2. creare provider-neutral `ModelRouter`;
3. migrare conversation e reflection senza cambiare comportamento approvato;
4. collegare `tool_builder` solo al descendant lab;
5. costruire `DesignDirectivePack`;
6. aggiungere reviewer read-only con output schema-validato;
7. collegare review a evaluator/lineage come evidenza, non promotion authority;
8. aggiungere benchmark, cost audit, timeout e fallback;
9. shadow su candidate sintetiche;
10. owner review prima di qualunque uso su candidate reali.

Acceptance minima:

- ogni chiamata registra ruolo e modello;
- coder non puo promuovere;
- reviewer non puo scrivere o promuovere;
- reviewer rileva corpus di violazioni note;
- risposta invalida/incompleta produce `inconclusive`;
- cambio modello non altera segreti, permessi o recovery;
- fallback e indisponibilita sono visibili.

## ElevenLabs Voice

Voice e canale opzionale, non requisito per uso testuale.

Uso previsto:

- STT ElevenLabs: audio utente -> testo -> privacy gate -> normale pipeline;
- TTS ElevenLabs: sola risposta finale o update esplicitamente abilitati;
- testo redatto/minimo inviato al provider;
- audio e trascrizioni non persistiti per default;
- voce disattivabile immediatamente;
- nessuna voce clonata senza consenso separato.

### Configurazione target

```json
{
  "voice": {
    "provider": "elevenlabs",
    "api_key": "<secret-in-core_config>",
    "enabled": false,
    "stt": {
      "model": "scribe_v2",
      "language": "it"
    },
    "tts": {
      "model": "eleven_multilingual_v2",
      "voice_id": "<configured-voice-id>"
    },
    "retention": {
      "persist_audio": false,
      "persist_transcript": false
    }
  }
}
```

Una chiave ElevenLabs con scope minimo per STT/TTS va inserita solo nel file
installato `%LOCALAPPDATA%\SEED\core_config\config.json`. Non inserirla in
`config.example.json`, documenti, log o repository. Impostare quota/credit
limit lato ElevenLabs. La chiave non e stata fornita durante questa operazione,
quindi nessun valore reale e stato configurato.

### Piano implementativo S11 - Optional Voice Lane

Implementare dopo S10, salvo priorita diversa esplicita:

1. config typed e validazione chiave/voice id;
2. consenso voice separato;
3. STT adapter con timeout, dimensione massima e cancellazione buffer;
4. privacy gate sul transcript prima di cloud LLM/search;
5. TTS adapter solo su testo approvato per output;
6. fallback testuale sempre disponibile;
7. audit aggregato di uso/costo/errori, senza audio o transcript;
8. test con chiave scoped e budget limitato;
9. opt-in owner prima del test utente.

Acceptance minima:

- senza consenso nessun audio lascia dispositivo;
- chiave assente non rompe chat testuale;
- errore STT/TTS degrada a testo;
- audio/transcript non persistono per default;
- provider non riceve segreti o contesto non necessario;
- costo e chiamate sono auditabili;
- revoca voice ha effetto immediato.

## Fonti primarie

- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama Cloud limitations](https://docs.ollama.com/cloud)
- [Ollama qwen3-coder-next](https://ollama.com/library/qwen3-coder-next)
- [Ollama gpt-oss](https://ollama.com/library/gpt-oss)
- [Ollama nemotron-3-super](https://ollama.com/library/nemotron-3-super)
- [ElevenLabs API authentication](https://elevenlabs.io/docs/api-reference/authentication)
- [ElevenLabs Speech to Text](https://elevenlabs.io/docs/capabilities/speech-to-text)
- [ElevenLabs Text to Speech](https://elevenlabs.io/docs/capabilities/text-to-speech)
