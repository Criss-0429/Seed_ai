# AGENTS.md - Regole operative SEED

## Fonte unica

Questo repository e' la singola fonte di verita' del progetto SEED.
Documentazione, fasi, sorgenti UI, codice, test e ricette di build devono
restare dentro questo repository.

## Prima di lavorare

Leggere, nell'ordine:

1. `PROJECT_OVERVIEW.md`
2. `ProductionPlan.md`
3. `docs/12_ImplementationPlan.md`
4. i documenti canonici pertinenti alla fase attiva

## Regole di avanzamento

- Lavorare solo sulla fase attiva.
- Non spuntare checkbox: sono gate manuali dell'owner.
- Aggiornare il Feature Context Pack prima dell'implementazione.
- Preservare le modifiche preesistenti nel worktree.
- Documentare verifiche, rischi, assunzioni e limiti residui.

## Cosa versionare

Versionare codice sorgente, test, documentazione, asset necessari, file di
configurazione di esempio, script, lockfile e ricette di build riproducibili,
inclusi `packaging/pyinstaller/*.spec`.

Non versionare:

- `build/`, `dist/`, `release/` e altri output rigenerabili;
- installer, archivi update e binari di release;
- ambienti virtuali, cache e file temporanei;
- segreti, credenziali, configurazioni personali o dati utente.

Gli installer e gli archivi update destinati ai tester vanno pubblicati come
asset di GitHub Release, mantenendo nel repository solo le istruzioni e gli
script necessari a rigenerarli.
