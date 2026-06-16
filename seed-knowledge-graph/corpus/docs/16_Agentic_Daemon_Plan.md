# 16 - Agentic Background Daemon Plan (Hermes + OpenClaw pattern)

> **Stato:** D0 Runtime Option Benchmark attivo su go esplicito di Cristian
> (2026-06-13). D1-D6 e D-OBS restano forecast, separati e owner-gated.

## Obiettivo

Dare a SEED un **daemon agentico in background** (solo a PC acceso) e funzioni
agentiche reali (shell/file/app/web/home, skills procedurali, delega a
sub-agenti), **dietro la sandbox e la governance esistenti** di SEED. Ispirato al
sistema ibrido previsto per JARVIS: Hermes (tool registry, skills, MCP, backend
di esecuzione, delega) + OpenClaw (gateway 24/7, heartbeat/cron, sovereign data)
+ altri pattern.

## Regola architetturale (non negoziabile, da wiki)

`Hermes_Agent`, `OpenClaw`, `Agentic_Runtime_Options_2026_05`:

- **SEED Core resta il governatore**: conversazione, trust, privacy gate, audit,
  cost/model policy (ModelRouter S10), capability registry, permission broker,
  sandbox, lineage. NON viene sostituito.
- **Hermes/OpenClaw = pattern e worker, non runtime intero.** Niente "big bang
  replacement", niente runtime esterno sul percorso generico delle richieste.
- **Worker dietro capability registry**: delega capability-specifica, mai un
  canale generico verso un orchestratore esterno.
- **Prima attivazione READ-only** (es. `worker.runtime_status`), poi singole
  capability WRITE_SAFE allowlistate.
- Comandi deterministici/locali NON passano dal worker.

## Cosa prendere da ciascuno

| Fonte | Pattern da importare | Cosa NON prendere |
|---|---|---|
| Hermes | tool registry tipizzato, **skills = ricette `.md` riviste** (procedural memory), MCP filtering, **backend di esecuzione isolato (Docker)**, `delegate_task` a sub-agenti isolati, provider routing/fallback | runtime intero, memoria propria, gateway che sposta il centro di gravita' fuori da SEED |
| OpenClaw | daemon worker privato, **heartbeat/cron** reviewable, session/identity isolation, sovereign data locale | orchestratore 24/7 always-on, self-hacking (skill auto-installate senza review), shell illimitata |
| OpenHarness/Verdent | dry-run, permission hooks, worktree/workspace isolation, manager/executor, review queue | tool/shell ampi senza sandbox |

## Daemon: "solo a PC acceso"

Il daemon NON e' un servizio OS persistente. Vincoli:

- vive nel processo SEED supervisionato (estende `SEEDSupervisor` S6 +
  `Scheduler`): parte all'avvio di SEED, muore alla chiusura/logout;
- nessun auto-start a livello OS, nessun task pianificato di sistema;
- a PC spento: nulla gira. A PC acceso ma SEED chiuso: nulla gira;
- heartbeat/cron solo entro la sessione SEED attiva, con cooldown e suppression.

## Sicurezza ed esecuzione (sopra il sandbox esistente)

SEED ha gia': audit statico AST + allowlist import + deny call/os/path
(`sandbox.py`), subprocess isolato (env minimale senza key, CWD workspace,
timeout, kill albero, `CREATE_NO_WINDOW`), permission broker, `forbidden` path
guard, lineage append-only, owner gate (vedi S10.5 `design_reviewer_real_enabled`).

Estensioni richieste per l'agentico reale:

- **Action contract** per ogni capability worker (input/output schema, risk_class,
  allowed_scopes, side_effect_type, requires_approval, supports_dry_run,
  supports_rollback, observability_signal) — da harness cognitivo doc wiki;
- **Tier di isolamento**: subprocess+AST (gia') per tool locali; **container
  (Docker/Hermes backend)** o subprocess fortemente ristretto (path/network
  allowlist) per shell/file/web reali;
- **Expected observation + rollback** per ogni azione (active inference): l'agente
  dichiara cosa osservare dopo; fallback a istruzione manuale; nessun fake
  `actions_taken`;
- **Trust gate**: azioni `DESTRUCTIVE`/`CRITICAL` -> approval owner esplicito
  (riusa il pattern owner-gate di S10.5); blocco se observability bassa;
- **Proattivita' governata** (formula harness): default silenzio; parla solo se
  expected_value > interruption_cost + privacy_cost + trust_cost; suppression e
  cooldown; mai azione sensibile autonoma;
- **Skills riviste**: ogni skill `.md`/codice passa da `Skill_Security_Audit` +
  capability forge (S3/S4/S5) + reviewer (S10.3) come evidenza; niente
  self-install autonomo;
- **Niente segreti ai worker**: come il sandbox attuale, env senza key; le key
  restano in core_config;
- **Audit + lineage** per ogni azione: aggregato, senza contenuto personale.

## Fasi (forecast, gated)

| Fase | Scope | Gate |
|---|---|---|
| D0 | **Runtime Option Benchmark**: OpenClaw vs Hermes vs OpenHarness su fixture (no repo reale); scelta backend di esecuzione e isolamento | owner |
| D1 | **Daemon host PC-on**: loop background supervisionato (estende Supervisor+Scheduler) con heartbeat + proactivity queue persistente; ZERO azioni agentiche di scrittura | owner |
| D2 | **Worker adapter READ-only**: capability `worker.runtime_status` e simili dietro registry/permission/audit; prima attivazione read-only | owner |
| D-OBS | **Read-only observation lane**: osservare app in uso, tab del browser ed esecuzioni sul PC (SOLO lettura) per raccogliere conoscenza sull'utente, alimentando CUK/memoria come candidate redatte | owner |
| D3 | **Sandbox hardening**: backend container/ristretto, action contract, dry-run, expected observation, rollback; trust gate per destructive | owner |
| D4 | **Capability WRITE_SAFE**: file/app/home-assistant read-safe allowlistate con observation+rollback; nessuna azione critica senza approval | owner |
| D5 | **Skills procedurali + delega**: skills riviste (forge+reviewer), sub-agenti isolati (worktree/container), task graph IR | owner |
| D6 | **Gateway cross-surface (opz.)**: Telegram/altro dietro privacy gate + consenso (vedi VPS Telegram) | owner |

## Decisione proposta D0 (2026-06-13)

Il benchmark architetturale sintetico propone un'integrazione ibrida governata:

- **OpenHarness** come backend di isolamento/esecuzione, per dry-run, permission
  hooks e workspace isolation;
- **Hermes** come fonte dei pattern registry tipizzato, skill riviste e delega
  isolata;
- **OpenClaw** come fonte dei pattern heartbeat, daemon e session isolation;
- **nessun runtime esterno** come sostituto o orchestratore generale di SEED.

Evidenza: `seed/core/runtime_bench.py`, test `tests/test_runtime_bench.py`,
report generabile con `:runtimebench`. Il report e deterministico, hashato e
privacy-safe; non installa o esegue i runtime confrontati. D1 resta bloccata
fino al gate owner D0.

## D-OBS — Read-only observation lane (raccolta info utente)

Obiettivo: capire l'utente osservando il PC in **sola lettura** (mai azione),
estendendo il `watcher` esistente. Alimenta il modello cognitivo (CUK K1-K4) e la
memoria (M2) come **candidate redatte**, non fatti.

Cosa osserva (read-only, opt-in, per-classe):

- app in primo piano e in uso, durata/sessioni (gia' parziale nel watcher);
- **tab/app del browser** (titolo/URL redatto) tramite estensione/accessibility,
  mai contenuto di pagina senza richiesta;
- esecuzioni/processi sul PC (nome processo, finestra), mai lettura file non
  autorizzata.

Vincoli non negoziabili:

- **READ-only assoluto**: nessuna azione, nessun click, nessuna scrittura;
- **consenso per-classe** dalla superficie UI "Permessi e Privacy — cosa posso
  osservare" (Prototype SEED_UI): l'utente abilita/disabilita ogni classe;
- **privacy gate** su ogni segnale prima di qualunque uso o sintesi; URL/titoli
  redatti; niente upload;
- **candidate-only**: l'osservazione diventa al massimo un'**ipotesi** a bassa
  confidenza (es. routine, interesse) — mai un fatto, mai diagnosi; promozione
  governata, correzione dell'utente prevale (regole CUK doc 15);
- **sensibile escluso**: salute/finanza/relazioni intime fuori per default;
- **salienza prima del modello**: euristica deterministica decide cosa merita di
  diventare candidate; il resto resta "remember silently" o scartato;
- **audit aggregato**: ore per categoria, conteggi; mai contenuto personale grezzo
  nel report;
- **revoca immediata** e cancellazione: stop osservazione + purge dei derivati.

Si appoggia a: `watcher` (gia' presente), privacy gate, KnowledgeStore/
KnowledgeExtractor (M2), salience (K3), permission broker. Wireframe D
(overlay-first context-aware) usa questo permesso per riferirsi a cio' che l'utente
sta guardando, **solo se l'osservazione e' attiva**.

## Acceptance minima (per fase)

- daemon gira solo a PC acceso e con SEED attivo; si ferma alla chiusura;
- nessun servizio OS persistente creato;
- prima capability worker e' READ-only;
- ogni azione ha contract, sandbox, observation, audit; destructive -> approval;
- nessun segreto raggiunge il worker;
- proattivita' rispetta silence/suppression/cooldown e costo interruzione;
- skill installata solo dopo audit+review, mai self-install autonomo;
- rollback verificato per le azioni reversibili.

## Non-goals

- orchestratore esterno always-on a PC spento o senza SEED;
- runtime esterno sul percorso generico delle richieste;
- shell/file/web illimitati senza sandbox e approval;
- self-modifica autonoma di skill/permessi senza owner gate;
- segreti o memoria personale inviati ai worker o a provider non necessari;
- sostituzione di Core, trust engine, capability registry o lineage.

## Metriche

action success rate, rollback success rate, unsafe-action-blocked, approval
latency, proactivity false-positive/suppression rate, privacy-block count,
daemon uptime entro sessione, costo per worker.

## Relazione con le altre feature

- riusa: Supervisor (S6), Scheduler, sandbox/permission/capabilities, lineage
  (S1-S5), ModelRouter + DesignReviewer + owner gate (S10), memoria/CUK
  (M/K) per salience e proattivita';
- precede l'attivazione reale del Capability Forge su repo veri;
- S11.3 (pannello UI voce) resta posticipata per scelta di Cristian.

## Fonti

`Hermes_Agent.md`, `OpenClaw.md`, `OpenClaw_Setup_Patterns.md`,
`Agentic_Runtime_Options_2026_05.md`, `Jarvis_Agentic_Architecture.md`,
`Jarvis_Cognitive_User_Model_Execution_Harness.md`, `Skill_Security_Audit.md`,
`BAND_Multi_Agent_Governance.md`. Subordinate ai documenti SEED.
