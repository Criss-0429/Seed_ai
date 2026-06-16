# 19 - Selective Capability Forge Plan

> **Stato:** programma futuro documentato, non implementato.
> **Sequencing:** parte dopo P6 oppure solo con override esplicito dell'owner.
> **Obiettivo:** permettere a ogni istanza SEED di capire quali strumenti
> conviene imparare per il proprio utente, costruirli e attivarli entro
> autorita gia concesse, senza trasformarsi in un catalogo universale di
> integrazioni.

## Decisione di prodotto

SEED non deve limitarsi a eseguire tool preinstallati o a costruire tool solo
quando l'utente formula una richiesta tecnica. Deve poter osservare workflow
consensuali, riconoscere frizioni e bisogni ricorrenti, confrontare soluzioni
possibili e decidere se imparare una nuova capability.

L'obiettivo non e massimizzare il numero di tool. `Non imparare`, comporre
capability esistenti, usare una soluzione temporanea, attendere piu evidenza o
rendere dormant una capability sono risultati validi.

Due istanze che partono dalla stessa base devono poter evolvere strumenti
completamente diversi. Servizi come email, calendari, Canva, Photoshop o
Illustrator sono esempi non normativi: non devono esistere branch hardcoded per
questi prodotti.

## Correzione normativa: attivazione e autorita

La regola precedente `mai self-install automatico` viene resa piu precisa:

> **SEED non puo mai auto-espandere la propria autorita.**

Questo significa:

- il componente che genera una capability non puo approvarla, promuoverla o
  attivarla;
- una `CapabilityActivationAuthority` indipendente puo attivare automaticamente
  una capability verificata solo quando l'autorita richiesta e un sottoinsieme
  di quella gia concessa;
- nuovi account, scope, categorie di dati, destinazioni, frequenze o tipi di
  effetto richiedono consenso esplicito;
- azioni irreversibili o ad alto impatto richiedono sempre conferma
  contestuale, anche quando la connessione e gia autorizzata;
- il diniego o la revoca non possono essere aggirati generando un nuovo tool.

L'attivazione automatica entro un'autorita esistente non e auto-promozione: e
una decisione separata, deterministica, auditabile e revocabile della promotion
authority.

## Invarianti non negoziabili

1. Il builder non promuove mai cio che costruisce.
2. Il reviewer produce evidenza, non autorita.
3. Password, token e segreti sono `discard-only`: non entrano in memoria,
   prompt, lineage, audit, evidenze o input dei tool.
4. Dati personali, sensibili e finanziari possono essere analizzati soltanto
   localmente; payload remoti sono redatti, aggregati e minimi.
5. Una capability generata non riceve direttamente credenziali.
6. Ogni effetto passa da action contract, authority envelope e audit.
7. Una variazione di autorita blocca l'attivazione fino al consenso umano.
8. Effetti irreversibili o ad alto impatto richiedono sempre conferma.
9. Ogni capability attiva ha health check, expected observation e recovery
   proporzionati al rischio.
10. Drift di codice, dipendenze, schema tool o autorita causa quarantena.
11. L'utente puo pausare, revocare, restringere, dimenticare e fare rollback.
12. UI automation e ultima risorsa e non diventa base per effetti irreversibili
    autonomi.

## Separazione delle quattro autorita

### 1. Observation consent

Autorizza SEED a comprendere localmente determinate sorgenti e workflow. Deve
essere:

- espresso in linguaggio naturale;
- opt-in;
- visibile mentre attivo;
- revocabile per singola sorgente;
- separato dal permesso di eseguire azioni.

### 2. Connection authority

Autorizza il collegamento con un account, un MCP, un'applicazione locale o un
servizio. L'utente vede cosa SEED potra leggere, fare e non fare. Il login
avviene tramite il flusso ufficiale del servizio quando disponibile.

### 3. Execution authority envelope

Descrive precisamente l'autorita gia concessa:

- account o connessione;
- categorie di dati leggibili;
- effetti consentiti;
- scope e destinazioni;
- schedule e frequenza;
- limiti quantitativi;
- durata e scadenza;
- condizioni di revoca.

### 4. Irreversible/high-impact confirmation

Non puo essere concessa permanentemente. Richiede conferma contestuale per:

- inviare o pubblicare;
- acquistare, pagare o trasferire;
- cancellare senza recovery affidabile;
- cambiare account, sicurezza o permessi;
- assumere impegni legali o finanziari;
- effettuare scritture esterne non recuperabili.

## Pipeline canonica

```text
osservazione consentita
-> evidenza locale derivata
-> ipotesi di bisogno
-> confronto con non fare nulla e alternative esistenti
-> ricerca e verifica dei connettori
-> piano tipizzato della capability
-> costruzione isolata
-> valutazione indipendente
-> shadow
-> awaiting_connection oppure canary
-> attivazione entro authority envelope
-> autopilot governato
-> monitoraggio, correzione, quarantena, dormienza o rimozione
```

Il bisogno deve essere formulato prima della soluzione. Una frizione osservata
non autorizza SEED a decidere in anticipo che serva un MCP, un'app specifica o
una nuova capability.

## Contratti pubblici

### WorkflowEvidence

```text
WorkflowEvidence {
  evidence_id
  source_kind
  activity_kind
  recurrence
  duration
  friction_signals
  outcome_signals
  sensitivity
  provenance_refs
  local_feature_refs
  raw_retention
  created_at
  expires_at
}
```

Contiene evidenze derivate e riferimenti locali, non password, token o copie
indiscriminate di contenuti personali. Il dato grezzo resta effimero salvo
consenso esplicito e motivato.

### NeedHypothesis

```text
NeedHypothesis {
  hypothesis_id
  user_goal
  observed_problem
  evidence_refs
  counterevidence_refs
  affected_contexts
  expected_value
  uncertainty
  expiry
}
```

Descrive il bisogno senza prescrivere una soluzione. Deve poter decadere,
essere corretto o essere soppresso dopo feedback negativo.

### FitnessDecision

```text
FitnessDecision {
  decision_id
  need_hypothesis_ref
  alternatives
  evidence_strength
  expected_utility
  privacy_cost
  trust_cost
  maintenance_cost
  operational_risk
  hard_blockers
  selected_alternative
  verdict
  reasons
}
```

Il verdetto non dipende da un singolo score aggregato. Le dimensioni restano
separate e i blocker di privacy, autorita e sicurezza non possono essere
compensati da maggiore utilita.

### CapabilityPlan

```text
CapabilityPlan {
  capability_id
  need_hypothesis_ref
  selected_connector_ref
  input_schema
  output_schema
  action_contracts
  requested_authority
  expected_observations
  dry_run_plan
  rollback_plan
  evaluation_plan
  maintenance_plan
}
```

### ConnectorDescriptor

```text
ConnectorDescriptor {
  connector_id
  kind
  source
  publisher
  version
  digest
  dependency_lock_ref
  tool_schema_hash
  transport
  destinations
  credential_mode
  verification_state
  drift_policy
}
```

`kind` include almeno `existing_capability`, `skill`, `mcp_local`,
`mcp_remote`, `official_api`, `plugin`, `file_exchange`, `cli`,
`custom_adapter` e `ui_automation`.

### ConnectionRequirement

```text
ConnectionRequirement {
  connection_id
  human_reason
  service_name
  data_access
  allowed_effects
  explicit_limits
  denied_effects
  retention
  revocation_path
}
```

La UI mostra questo contratto in linguaggio comprensibile, non come richiesta
tecnica di token o scope OAuth.

### AuthorityEnvelope

```text
AuthorityEnvelope {
  authority_id
  connection_id
  data_classes
  effects
  scopes
  destinations
  schedules
  quantitative_limits
  valid_from
  expires_at
  revocation_ref
}
```

L'attivazione automatica richiede una verifica deterministica:

```text
requested_authority is strict_subset_or_equal(granted_authority)
```

Il confronto deve fallire chiuso se un campo e sconosciuto, ambiguo o non
rappresentabile.

### CapabilityManifestV2

```text
CapabilityManifestV2 {
  capability_id
  version
  description
  provenance
  evidence_refs
  connector_ref
  input_schema
  output_schema
  action_contracts
  requested_authority
  risk_classes
  data_classes
  retention
  dependency_lock_ref
  build_digest
  tests
  fixtures
  health_check
  expected_observations
  dry_run_plan
  rollback_plan
  drift_policy
  maintenance_policy
}
```

### CapabilityEvaluationReport

```text
CapabilityEvaluationReport {
  capability_id
  manifest_digest
  evaluator_version
  deterministic_checks
  adversarial_checks
  privacy_checks
  authority_checks
  runtime_checks
  dry_run_result
  rollback_result
  expected_observation_result
  comparison_result
  blockers
  verdict
}
```

### CapabilityLifecycleState

```text
observed
-> framed
-> researching
-> planned
-> building
-> evaluating
-> shadow
-> awaiting_connection | canary
-> active
-> dormant | quarantined | rejected | archived
```

Ogni transizione lascia evidenza nel lineage. Nessuna transizione salta i gate
di autorita o rende implicita una nuova connessione.

## Evidence Engine locale

SEED puo comprendere workflow in modo ampio soltanto dopo consenso esplicito.
Le sorgenti possono includere applicazioni attive, processi, browser bridge,
documenti scelti, eventi e outcome delle capability.

La pipeline obbligatoria e:

```text
raw locale effimero
-> rilevazione e scarto segreti
-> classificazione sensibilita
-> estrazione di feature locali
-> WorkflowEvidence
-> aggregazione e scadenza
```

Regole:

- nessun keylogging;
- nessuna intercettazione password;
- nessuna cattura silenziosa di credenziali o sessioni;
- sorgenti sensibili elaborate localmente o non elaborate;
- se manca un percorso locale sicuro, il sistema fallisce chiuso;
- i provider remoti vedono soltanto evidenze redatte e minime;
- pausa, blocklist, cancellazione e revoca sono sempre disponibili.

## Need e Fitness Engine

Il motore decide prima se valga la pena intervenire e solo dopo quale soluzione
usare.

Default per opportunita inferite:

- almeno 3 occorrenze distribuite su 2 sessioni;
- almeno 5 occorrenze su 3 sessioni per ambiti sensibili;
- richiesta esplicita puo superare la soglia di ricorrenza, ma non i gate di
  privacy, autorita o sicurezza;
- controevidenza forte blocca o rimanda;
- una soluzione esistente adeguata impedisce la costruzione di un duplicato;
- feedback negativo sopprime proposte simili per un periodo dichiarato.

Le soglie sono configurabili e auditabili. Non trasformano automaticamente
pattern in fatti o preferenze stabili.

## Strategia di selezione dei connettori

SEED valuta nell'ordine:

1. non fare nulla;
2. comporre capability attive;
3. usare uno skill esistente;
4. usare un MCP esistente verificabile;
5. usare API, plugin, scripting, file exchange o CLI ufficiali;
6. generare un MCP o adapter custom isolato;
7. usare UI automation supervisionata come ultima risorsa.

La scelta considera utilita, affidabilita, costo, privacy, autorita necessaria,
manutenzione e rischio di drift. La soluzione tecnicamente piu potente non e
automaticamente la migliore.

## MCP discovery e vetting

Un registry MCP e una fonte di discovery, non una trust authority. Prima
dell'uso sono obbligatori:

- verifica di publisher e provenienza quando disponibile;
- pin di package, versione, digest e dependency lock;
- scansione statica, dipendenze, licenze, PII e segreti;
- snapshot di tool schema e descrizioni;
- allowlist delle destinazioni di rete;
- test con input sintetici e avversariali;
- rilevazione di token passthrough, SSRF, prompt injection e scope eccessivi;
- quarantena su drift di schema, descrizioni, digest, dipendenze o autorita.

MCP locali vengono eseguiti in processo o container ristretto. MCP remoti
passano dal Connection Broker. Nessun MCP riceve automaticamente memoria
personale, filesystem, shell, provider key o autorita del Core.

Riferimenti tecnici primari:

- [MCP Authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)
- [MCP Registry](https://modelcontextprotocol.io/registry/about)

## Connection Broker e Credential Vault

Il Connection Broker trasforma requisiti tecnici in richieste comprensibili.
Esempio:

```text
Ogni mattina SEED potra leggere oggetto, mittente e testo delle nuove email.
Non potra inviare o cancellare messaggi. Il riepilogo restera locale.
Puoi revocare l'accesso in qualsiasi momento.
```

Il broker:

- apre il login ufficiale del servizio;
- usa OAuth 2.1 con PKCE, `state`, audience/resource binding quando applicabile;
- conserva token e credenziali nel vault locale cifrato;
- espone ai tool solo handle tipizzati e operazioni autorizzate;
- gestisce scadenza, refresh e revoca;
- non permette token passthrough;
- mantiene la capability in `awaiting_connection` quando non esiste un flusso
  affidabile e comprensibile per collegare il servizio.

Il vault non e accessibile al builder, al reviewer, ai descendant o agli MCP
generati.

## Capability Builder V2

Il builder riceve un `CapabilityPlan`, non accesso libero al sistema.

Produce:

- logica tool con input/output tipizzati;
- adapter o MCP custom solo quando necessario;
- manifest V2;
- dipendenze fissate e riproducibili;
- fixture sintetiche;
- test e health check;
- dry-run, expected observation e rollback quando richiesti.

Il codice generato chiama connector handle tipizzati. Non importa SDK arbitrari
nel runtime principale, non installa dipendenze nell'ambiente applicativo e non
riceve credenziali.

## Evaluator indipendente

Prima di shadow sono obbligatori:

- validazione schema e action contract;
- audit statico e dependency scan;
- build riproducibile;
- test funzionali con fixture sintetiche;
- test avversariali e prompt injection;
- test di esfiltrazione segreti, filesystem e rete;
- verifica dell'authority envelope richiesto;
- verifica dry-run, rollback ed expected observation;
- confronto con parent, no-op e alternative esistenti;
- runtime isolato con limiti di risorse e timeout.

Il reviewer LLM puo contribuire, ma output invalido, mancanza di prove o
incertezza producono `inconclusive`, mai approvazione implicita.

## Activation Authority e autopilot

La `CapabilityActivationAuthority` e separata da builder, connector, reviewer
ed evaluator. Una capability puo essere auto-attivata solo quando:

- il report indipendente e valido;
- il build digest corrisponde al manifest valutato;
- il connettore e verificato e non presenta drift;
- l'autorita richiesta e sottoinsieme di quella gia concessa;
- non esistono nuovi account, scope, dati, destinazioni o tipi di effetto;
- non sono presenti effetti irreversibili o ad alto impatto;
- shadow e canary sono verdi;
- health check, osservazione e recovery sono validi;
- non esistono blocker aperti.

Se serve nuova autorita, lo stato diventa `awaiting_connection`. Dopo il
collegamento umano, SEED puo operare in autopilot soltanto entro l'envelope
concesso.

## Esperienza utente

La superficie primaria resta conversazionale. Le superfici secondarie mostrano:

- `SEED ha imparato X perche...`;
- bisogno ed evidenze usate;
- cosa la capability puo leggere e fare;
- cosa non puo fare;
- connessioni, schedule, destinazioni e limiti;
- ultimo esito, health e rollback;
- stato `awaiting_connection`, `active`, `dormant` o `quarantined`.

Controlli obbligatori:

- pausa;
- revoca connessione;
- restringi autorita;
- conferma azione ad alto impatto;
- ispeziona attivita;
- rollback;
- dimentica evidenze;
- sopprimi apprendimenti simili;
- mostra dettagli tecnici opzionali.

L'utente non deve conoscere token, scope OAuth, manifest o MCP per prendere una
decisione informata.

## Monitoraggio, drift e pruning

Ogni capability attiva confronta esito reale ed expected observation. Il
sistema registra:

- successo e fallimenti;
- correzioni e rollback;
- affidabilita e latenza;
- variazioni di schema, digest e dipendenze;
- variazioni di autorita o destinazioni;
- costo operativo e manutenzione;
- utilita osservata per l'utente.

Comportamenti inattesi, drift o variazioni di autorita causano quarantena
automatica. Affidabilita degradata puo causare rollback o dormienza. Il pruning
rimuove solo artefatti generati non piu utili; lineage, decisioni e incidenti
restano auditabili.

## Fasi di implementazione

| Fase | Scope | Advancement gate |
|---|---|---|
| **P7.0 - Contratti e policy** | Feature Context Pack, contratti V2, lifecycle, configurazione default-OFF, migrazione conservativa V1 | nessun cambiamento runtime; test contratti e migrazione verdi |
| **P7.1 - Local Evidence Engine** | consenso, sorgenti, raw effimero, secret discard, WorkflowEvidence, revoca e cancellazione | segreti scartati; dati sensibili mai remoti; revoca verificata |
| **P7.2 - Need & Fitness Engine** | ipotesi di bisogno, alternative, no-op e decisione multi-obiettivo | utenti sintetici divergono senza branch hardcoded |
| **P7.3 - Connector Discovery & Vetting** | inventario capability, MCP/API/plugin discovery, pinning, scan e drift | connettori malevoli o mutati bloccati/quarantinati |
| **P7.4 - Capability Builder V2** | generazione tool/adapter/MCP isolati con manifest e dipendenze bloccate | nessun segreto; nessuna modifica ambiente principale |
| **P7.5 - Independent Evaluator** | test deterministici, runtime, avversariali, privacy, autorita e rollback | nessuna shadow senza report valido |
| **P7.6 - Connection Broker** | vault, OAuth/MCP auth, connection UX e revoca | token mai esposti; revoca/scadenza funzionanti |
| **P7.7 - Activation Authority & Autopilot** | subset authority, shadow, canary, attivazione governata e conferme irreversibili | nuova autorita attende consenso; high-impact sempre bloccato |
| **P7.8 - User Experience** | timeline, richieste connessione, controlli, spiegazioni e audit | tester non tecnico comprende capacita e limiti |
| **P7.9 - Maintenance & Pilot** | health, drift, quarantena, dormienza, pruning, metriche e pilot | recovery verificato; nessuna regressione P0-P6 |

Ogni fase viene implementata e approvata singolarmente. La presenza di questo
documento non autorizza l'avvio di P7.

## Piano test

### Contratti e policy

- validazione completa dei contratti V2;
- confronto authority envelope deterministico e fail-closed;
- migrazione V1 conservativa: tool esistenti non diventano auto-attivi;
- builder incapace di chiamare promotion o vault.

### Evidence, privacy e fitness

- password, token e segreti scartati prima di memoria, prompt e audit;
- dati sensibili mai inviati a provider remoti;
- revoca sorgente interrompe raccolta e uso futuro;
- tre utenti sintetici producono capability differenti o nessuna capability;
- nessun branch hardcoded per servizi o casi di esempio;
- feedback negativo sopprime proposte simili.

### Connector e MCP

- MCP malevolo, SSRF, token passthrough e scope eccessivo bloccati;
- drift di schema, descrizione, digest o dipendenza causa quarantena;
- MCP custom costruito ed eseguito con dati sintetici in isolamento;
- connector host non espone credenziali al tool generato.

### Connessione e attivazione

- OAuth simulato con PKCE, `state`, audience, scadenza e revoca;
- attivazione automatica consentita entro authority envelope esistente;
- nuova autorita produce `awaiting_connection`;
- azione irreversibile richiede sempre conferma contestuale;
- azione reversibile in autopilot verifica risultato e rollback.

### Recovery e regressioni

- crash durante build, eval, canary e attivazione;
- rollback e stable boot dopo capability difettosa;
- quarantena su comportamento inatteso;
- suite P0-P6, core acceptance, lint, compile e build completi.

## Acceptance finale

- due utenti sintetici con la stessa base evolvono capability differenti;
- un terzo utente non riceve capability quando manca fitness;
- SEED spiega perche ha imparato o deciso di non imparare;
- nessun tool aumenta autonomamente autorita o accede al vault;
- nessun segreto entra in memoria, prompt, lineage o audit;
- capability verificata entro autorita esistente puo essere auto-attivata;
- nuova connessione viene richiesta in linguaggio naturale;
- azioni irreversibili non possono essere eseguite automaticamente;
- drift MCP o dipendenze causa quarantena;
- revoca, restrizione, dormienza e rollback sono verificati;
- fallimenti di build, connessione o capability non compromettono SEED.

## Rollout

Tutte le nuove lane partono default-OFF:

```text
fixture sintetiche
-> osservazione locale read-only
-> MCP esistente read-only
-> MCP custom read-only
-> azioni reversibili entro authority envelope
-> osservazione ampia consensuale
-> pilot controllato
```

Prima del pilot esterno:

- test automatici e adversarial verdi;
- nessun blocker privacy o recovery;
- un pilot interno su un utente;
- successivo pilot limitato a 2-3 utenti;
- metriche e audit revisionati dall'owner.

## Metriche

- opportunita utili rispetto alle opportunita proposte;
- frequenza del verdetto `non imparare`;
- false-positive surprise rate;
- tempo fra bisogno verificato e valore reale;
- correzioni, soppressioni e revoche;
- escalation di autorita richieste;
- blocchi privacy e secret discard;
- rollback e quarantene;
- costo di manutenzione;
- divergenza delle capability tra utenti.

## Non-goals iniziali

- costruire un marketplace universale di tool;
- installare automaticamente MCP non verificati;
- insegnare all'utente concetti tecnici per collegare un servizio;
- intercettare password, sessioni o credenziali;
- garantire integrazione con software privo di accesso legale e affidabile;
- rendere UI automation equivalente a un'API stabile;
- autorizzare permanentemente azioni irreversibili;
- permettere al builder di promuovere o modificare i propri gate.

## Rischi e assunzioni

- Non esiste un sistema letteralmente privo di errori; l'architettura deve
  fallire chiusa e preservare recovery.
- Un servizio esterno puo cambiare API, schema o policy: il drift e parte del
  contratto operativo.
- L'osservazione ampia richiede consenso iniziale esplicito e controlli per
  sorgente; non e implicita nell'uso di SEED.
- La capacita di costruire non implica che esista un percorso affidabile per
  collegare ogni servizio.
- P7 resta futura finche P6 non viene approvata o l'owner non concede un
  override di sequenza.
