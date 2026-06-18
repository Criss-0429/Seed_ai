<div align="center">

# SEED

**A local-first AI companion for Windows that grows with you.**

![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-1f1f1f)
![status](https://img.shields.io/badge/status-pilot-orange)
![license](https://img.shields.io/badge/license-AGPL--3.0-blue)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)

[English](README.md) · [Italiano](README-ita.md)

</div>

---

## Project status

SEED is an **early, evolving open-source project** in private pilot. The
foundations are solid — local privacy gate, boot supervisor, reversible
mutations — while higher-level capabilities are still moving. Expect rough
edges and treat it as a technical base, not a finished product.

## What SEED is

SEED is a desktop runtime for Windows: a conversational companion that starts
minimal and adapts to how you work over time. It runs locally, asks before it
acts, and changes only in reversible, auditable steps.

- **Local-first** — memory, history and configuration live under
  `%LOCALAPPDATA%\SEED`. Your content is not uploaded automatically.
- **Consent-driven** — watcher, voice, online search and permissions are off by
  default; you turn them on, and pause/revoke/rollback are always available.
- **Reversible** — every proposed change goes through validation (shadow,
  canary, evidence). Final promotion is always an explicit owner decision, never
  automatic.
- **Bring your own keys (BYOK)** — you connect your own LLM provider; one
  encrypted key per user, with a spending cap.

## Features

- Conversational assistant with a stable, distinct personality (not a clone of
  the user) and explainable answers.
- BYOK LLM providers: **Ollama Cloud** (recommended, free tier), **OpenRouter**,
  **Vercel AI Gateway**. Keys are encrypted with Windows DPAPI.
- **Optional voice** (speech-to-text and text-to-speech) via ElevenLabs BYOK —
  fully optional and skippable; SEED is complete in text-only mode.
- Local privacy gate that redacts queries before they reach any provider.
  Selectable Layer-1 backend (`privacy.backend`): `opf` (OpenAI Privacy Filter,
  ~2.7GB, highest accuracy, unloaded when idle), `gliner` (~300MB multilingual,
  always-on, good for low-RAM machines), or `regex` only. A deterministic regex
  layer always runs underneath.
- Boot supervisor with health checks, known-good snapshots and crash recovery.
- Proposal-only evolution engine: mutations are evaluated in isolation and
  remain owner-gated.

## Download

The Windows installer is published via **GitHub Releases**:

➡️ **[Download the latest release](https://github.com/Criss-0429/Seed_ai/releases/latest)**

The installer is **unsigned**, so Windows SmartScreen will warn you ("Windows
protected your PC"). This is expected — verify the SHA-256 against
`SHA256SUMS.txt` in the release, then choose **More info → Run anyway**. SEED
never installs a certificate into your Trusted Root. See
[`installer/TESTER_GUIDE.md`](installer/TESTER_GUIDE.md) for the full procedure.

## Quick start (development)

Requires Python 3.11+ on Windows.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install git+https://github.com/openai/privacy-filter
copy config\config.example.json config\config.json
python run_dev.py            # GUI
python run_dev.py --repl     # REPL
```

On first run SEED asks for consent, then for an LLM provider key (BYOK). The
chat unlocks once at least one provider key is validated.

## Build from source

Build a Windows tester release (PyInstaller `onedir` + Inno Setup). ML
checkpoints must be present locally; they are not committed to Git.

```powershell
python scripts\build_release.py --version 0.3.0-pilot --schema-version 1

& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" `
  /DAppVersion=0.3.0-pilot `
  /DReleaseRoot="$PWD\release\0.3.0-pilot" `
  installer\SEED.iss

python scripts\build_release.py --version 0.3.0-pilot --finalize-installer
```

Run the quality gate (lint, types, tests, acceptance) before building:

```powershell
python scripts\quality_gate.py --full
```

## Tech stack

- **Runtime:** Python 3.11+, packaged with PyInstaller (`onedir`).
- **UI:** `pywebview` desktop shell rendering a vanilla-JS surface (no
  React/CDN), fully offline.
- **ML (local):** Torch CPU, Transformers, Sentence-Transformers; emotion
  recognition (wav2vec2), embeddings, privacy filter.
- **Providers (BYOK):** OpenAI-compatible LLM APIs; ElevenLabs for optional voice.
- **Installer:** Inno Setup (unsigned), distributed via GitHub Releases.

## Repository layout

```
seed/            Application package (core runtime, UI, builtin capabilities)
config/          Example configuration (config.example.json)
packaging/       PyInstaller specs (reproducible build recipes)
installer/       Inno Setup script + tester guide
scripts/         Build, release and quality-gate scripts
site/            Static distribution website (GitHub Pages)
tests/           Test suite
docs/            Architecture and product documentation
assets/          Brand assets (icon, mark)
benchmarks/      Local benchmarks
```

## Privacy & security

- User data stays under `%LOCALAPPDATA%\SEED`; uninstall asks whether to keep or
  delete it.
- Provider keys are encrypted with DPAPI and never written in plaintext.
- No automatic upload of memory, traces or lineage.
- Online search is a separate, off-by-default module with privacy-gated queries.

Found a security issue? Please report it privately to the maintainer rather than
opening a public issue.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). This is a
pilot project, so open an issue to discuss substantial changes first.

## License

[GNU AGPL-3.0](LICENSE). If you run a modified version of SEED as a network
service, you must make the source of your version available to its users.
