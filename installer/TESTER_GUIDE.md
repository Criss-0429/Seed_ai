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

## Optional voice (ElevenLabs BYOK)

Voice (speech-to-text and text-to-speech) is **optional**. SEED is fully usable
in text-only mode without it. No ElevenLabs key is bundled in the installer.

To enable voice, bring your own ElevenLabs API key in the app settings: the key
is validated, encrypted with DPAPI, and stored only under `%LOCALAPPDATA%\SEED`.
You can **skip** this at any time and SEED will not block on it. Revoking the key
turns voice off again. Voice also requires explicit voice consent, separate from
memory consent.
