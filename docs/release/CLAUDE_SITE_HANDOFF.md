# Claude Handoff - SEED Site And Release Download

## Current State

- Repository: `Criss-0429/Seed`
- Working branch prepared by Codex: `codex/site-release-handoff`
- GitHub rulesets have already been configured manually by Cristian.
- Local ruleset templates are stored in `.github/rulesets/`.
- Release/download artifacts must be published as GitHub Release assets, never committed.
- `build/`, `dist/`, `release/`, venvs and caches are ignored.

## Branch Model

- `main`: stable/public release source.
- `develop`: integration branch.
- `codex/*` or `feature/*`: implementation branches.
- `release/vX.Y.Z`: temporary stabilization branch before merging into `main`.
- Published versions are immutable tags: `vX.Y.Z`.

## GitHub Release Contract

The site must not link to branches or raw files. It must link to GitHub Releases.

Preferred stable download URL:

```text
https://github.com/Criss-0429/Seed/releases/latest/download/SEED-Bootstrap-Setup-Unsigned.exe
```

Robust API option:

```text
https://api.github.com/repos/Criss-0429/Seed/releases/latest
```

Required release assets for the bootstrap strategy:

```text
SEED-Bootstrap-Setup-Unsigned.exe
SEED-runtime-<version>.zip
SEED-models-privacy-filter-<version>.zip
SEED-models-embedding-<version>.zip
SEED-models-emotion-<version>.zip
release-manifest.json
SHA256SUMS.txt
TESTER_GUIDE.md
```

GitHub Release assets must stay below 2 GiB each. Do not publish a single
monolithic installer if it exceeds that limit.

## Site Scope For Claude

Create a static site under `site/` with:

- clear product intro;
- Windows download CTA;
- latest release lookup;
- graceful fallback if GitHub API fails;
- SmartScreen explanation for unsigned installer;
- SHA-256 verification instructions;
- privacy/local-data summary;
- tester/pilot status;
- requirements and release notes link.

The download button must select only `SEED-Bootstrap-Setup-Unsigned.exe`.
Do not select GitHub-generated source archives.

## Workflow Scope For Claude

Create GitHub Actions workflows:

- `.github/workflows/ci.yml`
- `.github/workflows/pages.yml`
- `.github/workflows/release.yml`

Do not assume GitHub-hosted runners can build the full SEED release if required
ML checkpoints are only available locally. Document whether the release build
needs a self-hosted Windows runner or a manual upload step.

## Do Not Commit

- `build/`
- `dist/`
- `release/`
- installer binaries
- update ZIPs
- local venvs
- caches
- API keys or provider config
- user data under `%LOCALAPPDATA%`

## Verification Expected From Claude

- site link check;
- GitHub API fallback test;
- missing asset test;
- workflow YAML syntax check;
- no heavy artifacts tracked by Git;
- `git diff --check`;
- focused tests if workflow/release scripts are touched.
