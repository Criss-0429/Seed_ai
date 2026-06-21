# SEED Pilot Tester Guide

SEED pilot installer is intentionally unsigned. Windows SmartScreen may show
"Windows protected your PC".

1. Verify installer name and version against release notes.
2. Verify SHA-256:
   `Get-FileHash .\SEED-<version>-Setup-Unsigned.exe -Algorithm SHA256`
3. Compare result with official `SHA256SUMS.txt`.
4. Open SmartScreen **More info** only after hash matches, then choose **Run anyway**.

Never install a certificate or add a certificate to Trusted Root for SEED.

SEED stores user data under `%LOCALAPPDATA%\SEED`, outside application install
directory. Upgrades preserve this directory. Uninstall asks whether to preserve
or remove it.

All shortcuts launch `SEEDSupervisor.exe`, which verifies health and recovery
before accepting runtime as known-good.

## One-time clean reinstall while keeping memory

Use `Reset-SEED-Keep-Memory.ps1` only when the maintainer asks you to remove a
duplicate/old SEED installation before installing the latest complete release.
The script preserves only the local SQLite memory. It removes runtime, models,
configuration, provider keys, lineage, generated tools, workspace files and
local backups. Provider keys must be entered again after reinstalling.

1. Download `Reset-SEED-Keep-Memory.ps1` from the same GitHub Release.
2. Verify its SHA-256 against `SHA256SUMS.txt`.
3. Preview without changing the PC:
   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Reset-SEED-Keep-Memory.ps1 -WhatIf`
4. Run it and type `RESET-SEED` when requested:
   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Reset-SEED-Keep-Memory.ps1`
5. Install the latest complete SEED release.

The script leaves a second verified memory copy under
`%LOCALAPPDATA%\SEED-memory-backups` and never scans or deletes project folders
under Documents.

## Optional voice (ElevenLabs BYOK)

Voice (speech-to-text and text-to-speech) is **optional**. SEED is fully usable
in text-only mode without it. No ElevenLabs key is bundled in the installer.

To enable voice, bring your own ElevenLabs API key in the app settings: the key
is validated, encrypted with DPAPI, and stored only under `%LOCALAPPDATA%\SEED`.
You can **skip** this at any time and SEED will not block on it. Revoking the key
turns voice off again. Voice also requires explicit voice consent, separate from
memory consent.
