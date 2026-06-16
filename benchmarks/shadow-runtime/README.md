# Shadow Runtime Benchmark

Benchmark eseguibile e sintetico richiesto dall'owner il 2026-06-14 per
confrontare il runtime custom SEED con possibili harness esterni senza usare
dati personali, credenziali, provider o repository reali.

## Baseline custom SEED

Report: `custom-seed-shadow-report.json`.

- 14 fixture sintetiche eseguite;
- 14 pass;
- il restricted process blocca le operazioni socket quando
  `network_allowed=False`, incluso il modulo low-level `_socket`, oltre al
  precedente static audit;
- letture e scritture fuori workspace bloccate;
- segreto sintetico dell'ambiente non ereditato;
- spawn subprocess bloccato nel restricted process;
- timeout hard e output non JSON bloccati;
- scrittura entro workspace permessa;
- static audit blocca subprocess, rete non dichiarata ed `exec`.

Il guard socket Python e difesa aggiuntiva, non isolamento OS contro codice
ostile. Per quello resta richiesto il backend container con rete disabilitata.

## OpenHarness 0.1.9 - shadow test isolato

Report: `openharness-shadow-report.json`.

- installazione temporanea con cache inclusa: 237,24 MB, sotto il tetto 500 MB;
- solo dry-run e chiamate dirette al permission checker con fixture sintetiche;
- zero provider, chiavi reali, model call o tool execution;
- 10 fixture pass, 2 fail;
- il checker blocca mutazioni in plan mode, richiede conferma in default mode e
  protegge path sensibili anche in full auto;
- difetto high: gli override CLI `--permission-mode plan` e
  `--permission-mode full_auto` risultano inefficaci e lasciano il runtime in
  `default`;
- limite medium: la sandbox OS e disabilitata per default, quindi il permission
  checker non equivale a isolamento process-level.

Conclusione: OpenHarness offre un permission checker piu ricco del pattern
custom attuale, ma la versione testata non e adottabile come boundary di
sicurezza senza correggere/verificare l'override CLI e attivare una sandbox
reale.

## Hermes Agent 0.16.0 - shadow test isolato

Report: `hermes-shadow-report.json`.

- clone shallow + core/dev environment temporaneo; picco 529,61 MB con cache,
  ridotto immediatamente a 328,81 MB eliminando la sola cache;
- zero provider, key, model call o tool live;
- approval/core guards senza optional Tirith: 455 pass, 9 fail;
- skill guard/AST audit: 87 pass, 2 fail ambientali, 2 skip;
- registry, skill dispatch e delega: 306 pass, 5 fail, 2 skip;
- difetto high confermato: i path assoluti Windows `C:\...` bypassano il
  detector approval per redirect, tee e in-place edit verso shell rc, SSH
  `authorized_keys` e config Hermes;
- registry, tool search, skill AST audit e delega scoped restano pattern utili.

Conclusione: Hermes e bocciato come runtime o boundary di sicurezza SEED su
Windows. Resta una buona reference da cui reimplementare pattern selezionati
dietro governance e sandbox SEED.

## OpenClaw 2026.6.2 - shadow test source-only

Report: `openclaw-shadow-report.json`.

- clone sparse + runner Vitest minimo: 213,48 MB;
- runtime completo e gateway non avviati: Node locale `22.17.0`, requisito
  OpenClaw `>=22.19.0`;
- normalizzazione, sessioni, ownership, allowlist e heartbeat token:
  `131/131` pass;
- heartbeat policy, cooldown, active hours, wake, visibility e message access:
  `144/144` pass;
- exec policy analysis source-only: 131 pass; 4 fixture POSIX non portabili su
  Windows; sandbox/policy complete non valutabili senza `@openclaw/fs-safe`;
- audit statico: sandbox assente equivale a `mode=off`; exec host normale ha
  security default `full`, mentre il sandbox host usa `deny`.

Conclusione: OpenClaw e la reference migliore per heartbeat e session lifecycle,
ma non deve essere incorporato come runtime SEED ne usato come boundary di
sicurezza con i default attuali.

## Altri harness - readiness

| Harness | Stato locale | Precondizioni / peso osservato |
|---|---|---|
| OpenClaw | testato source-only in ambiente temporaneo | 213,48 MB; ottima reference heartbeat/sessioni, non safety boundary default |
| Hermes Agent | testato in ambiente temporaneo | 328,81 MB senza cache; bocciato come runtime/boundary Windows, utile come reference |
| OpenHarness | testato in ambiente temporaneo | installazione e cache 237,24 MB; cleanup richiesto a fine benchmark |
| Docker isolation | CLI presente, daemon spento | richiede avvio Docker e download immagini |

## Gate per test esterni

Prima di scaricare o installare:

1. approvazione owner esplicita;
2. installazione solo sotto directory temporanea dedicata;
3. nessuna key o dato reale;
4. rete negata durante le fixture;
5. tetto spazio misurato;
6. rimozione completa degli ambienti e verifica spazio a fine benchmark.
