# Contributing to SEED

Thanks for your interest. SEED is an early pilot project, so coordination
matters more than speed.

## Before you start

- **Open an issue first** for anything substantial (new feature, refactor,
  dependency, behavioural change). Small fixes (typos, obvious bugs) can go
  straight to a PR.
- Read [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md) and the relevant documents
  under [`docs/`](docs/) to understand the architecture and the active phase.
- SEED is **local-first and privacy-first**. Changes must not weaken these
  guarantees: no silent uploads, no plaintext secrets, no bypassing the privacy
  gate or the consent flow.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pip install git+https://github.com/openai/privacy-filter
copy config\config.example.json config\config.json
python run_dev.py
```

## Quality gate

Before opening a PR, run:

```powershell
ruff check .
ruff format --check .
python -m pytest
python scripts\core_acceptance.py
```

Or the full gate (lint, types, audit, tests, acceptance, build report):

```powershell
python scripts\quality_gate.py --full
```

All checks must pass. New behaviour needs tests; tests run offline (network,
providers and real models are mocked).

## Pull requests

- Keep PRs focused; one logical change per PR.
- Describe **what** changed, **why**, and how you verified it.
- Match the style of the surrounding code; do not reformat unrelated files.
- Never commit regenerable output (`build/`, `dist/`, `release/`), installers,
  update archives, virtualenvs, caches, secrets or user data. The release
  artifacts are published as GitHub Release assets, not committed.

## Security

Report vulnerabilities privately to the maintainer instead of filing a public
issue. Do not include real API keys, credentials or personal data in issues,
PRs or test fixtures.

## License

By contributing, you agree that your contributions are licensed under the
project's [GNU AGPL-3.0](LICENSE) license.
