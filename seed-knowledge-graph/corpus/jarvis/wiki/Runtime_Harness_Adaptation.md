# Runtime Harness Adaptation

**Ultimo Aggiornamento:** 2026-06-04
**Rilevanza per JARVIS:** Alta - rafforza l'idea che un agente affidabile migliori adattando harness, contratti, feedback e regolazione della traiettoria, non solo cambiando modello.

Runtime Harness Adaptation e' il pattern descritto nel paper arXiv `2605.22166`, "Adapting the Interface, Not the Model: Runtime Harness Adaptation for Deterministic LLM Agents". Il paper propone Life-Harness: un harness runtime lifecycle-aware che resta fisso in valutazione e migliora agenti LLM frozen convertendo failure ricorrenti in interventi riusabili sull'interfaccia modello-ambiente.

## 1. Core Value / Funzione Principale

Il valore per JARVIS e' diretto: molte failure agentiche non richiedono fine-tuning, ma contratti migliori tra modello, ambiente, tool, osservazioni e feedback. Il paper riporta miglioramenti su 116/126 combinazioni modello-ambiente in sette ambienti deterministici, con harness trasferibili fra modelli.

## 2. Specifiche Tecniche

- Ambito: agenti in domini deterministici e rule-governed.
- Oggetto adattato: runtime harness, non pesi modello.
- Interventi: environment contracts, procedural skills, action realization, trajectory regulation.
- Risultato chiave dichiarato: miglioramento medio relativo dell'88.5% nelle impostazioni valutate.
- Stato fonte: work in progress, v2 del 2026-05-27.

## 3. Integrazione con JARVIS

JARVIS ha gia' molte parti compatibili: `CapabilityRegistry`, invocation gate, response contract, task graph, approval loop, status stream, low-cost deterministic capability pack. Questo paper suggerisce di trattare quei moduli come harness adattabile e misurabile:

- salvare recurring failure come fixture/harness interventions;
- aggiungere procedural skills solo dopo audit e staging;
- migliorare action realization con schema e guardrail, non con prompt libero;
- usare trajectory regulation per retry, cancel, fallback, status e recovery.

Non e' una ragione per fare fine-tuning o sostituire il Core.

## Relazioni

- [[Agent_Harness_Best_Practices]] - workflow harness e quality gates.
- [[OpenHarness]] - riferimento pratico per harness agentico governato.
- [[High_Reliability_Decision_Protocol]] - gate list e blast radius per action classes.
- [[Capability_Forge_External_Tools]] - concetto operativo da allineare se viene creata pagina dedicata.

**Fonte:** https://arxiv.org/abs/2605.22166
