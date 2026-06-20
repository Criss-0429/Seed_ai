<div align="center">

# SEED

**Un'intelligenza locale per Windows che cresce con te.**

![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-1f1f1f)
![status](https://img.shields.io/badge/status-pilot-orange)
![license](https://img.shields.io/badge/license-AGPL--3.0-blue)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)

[English](README.md) · [Italiano](README-ita.md)

</div>

---

## Stato del progetto

SEED è un progetto open-source **giovane e in evoluzione**, in pilot privato. Le
fondamenta sono solide — privacy gate locale, boot supervisor, mutazioni
reversibili — mentre le funzionalità di alto livello sono ancora in movimento.
Aspettati spigoli: è una base tecnica, non un prodotto finito.

## Cos'è SEED

SEED è un runtime desktop per Windows: un compagno conversazionale che parte
minimale e si adatta nel tempo al tuo modo di lavorare. Gira in locale, chiede
prima di agire e cambia solo in passi reversibili e verificabili.

- **Locale** — memoria, cronologia e configurazione vivono in
  `%LOCALAPPDATA%\SEED`. I tuoi contenuti non vengono caricati automaticamente.
- **Consensuale** — watcher, voce, ricerca online e permessi sono spenti di
  default; li attivi tu, e pausa/revoca/rollback sono sempre disponibili.
- **Reversibile** — ogni cambiamento proposto passa per validazione (shadow,
  canary, evidenze). La promozione finale è sempre una decisione esplicita
  dell'owner, mai automatica.
- **Chiavi tue (BYOK)** — colleghi il tuo provider LLM; una chiave cifrata per
  utente, con tetto di spesa.

## Funzionalità

- Assistente conversazionale con identità stabile e distinta dall'utente (non
  una copia) e risposte spiegabili.
- Provider LLM BYOK: **Ollama Cloud** (consigliato, piano gratuito),
  **OpenRouter**, **Vercel AI Gateway**. Chiavi cifrate con Windows DPAPI.
- **Voce opzionale** (STT e TTS) via ElevenLabs BYOK — del tutto facoltativa e
  skippabile; SEED è completo in modalità testuale.
- Privacy gate locale che redige le query prima che raggiungano qualsiasi
  provider. Backend Layer-1 selezionabile (`privacy.backend`): `opf` (OpenAI
  Privacy Filter, ~2.7GB, max accuratezza, scaricato quando idle), `gliner`
  (~300MB multilingue, sempre-attivo, ideale per PC con poca RAM) o solo
  `regex`. Sotto gira sempre un layer regex deterministico.
- Boot supervisor con health check, snapshot known-good e crash recovery.
- Motore evolutivo proposal-only: le mutazioni sono valutate in isolamento e
  restano owner-gated.

## Download

L'installer Windows è pubblicato tramite **GitHub Releases**:

➡️ **[Scarica l'ultima release](https://github.com/Criss-0429/Seed_ai/releases/latest)**

L'installer è **non firmato**, quindi Windows SmartScreen mostrerà un avviso
(«PC protetto da Windows»). È previsto — verifica lo SHA-256 con `SHA256SUMS.txt`
nella release, poi scegli **Ulteriori informazioni → Esegui comunque**. SEED non
installa mai certificati nei Trusted Root. Procedura completa in
[`installer/TESTER_GUIDE.md`](installer/TESTER_GUIDE.md).

## Avvio rapido (sviluppo)

Richiede Python 3.11+ su Windows.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install git+https://github.com/openai/privacy-filter
copy config\config.example.json config\config.json
python run_dev.py            # GUI
python run_dev.py --repl     # REPL
```

Al primo avvio SEED chiede il consenso, poi una chiave provider LLM (BYOK). La
chat si sblocca quando almeno una chiave provider è validata.

## Build da sorgente

Build di una release tester Windows (PyInstaller `onedir` + Inno Setup). I
checkpoint ML devono essere presenti in locale; non sono versionati in Git.

```powershell
python scripts\build_release.py --version 0.3.0-pilot --schema-version 1

& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" `
  /DAppVersion=0.3.0-pilot `
  /DReleaseRoot="$PWD\release\0.3.0-pilot" `
  installer\SEED.iss

python scripts\build_release.py --version 0.3.0-pilot --finalize-installer
```

Esegui il quality gate (lint, tipi, test, acceptance) prima della build:

```powershell
python scripts\quality_gate.py --full
```

## Stack tecnico

- **Runtime:** Python 3.11+, pacchettizzato con PyInstaller (`onedir`).
- **UI:** shell desktop `pywebview` che rende una superficie in JS vanilla
  (niente React/CDN), completamente offline.
- **ML (locale):** Torch CPU, Transformers, Sentence-Transformers; riconoscimento
  emozioni (wav2vec2), embedding, privacy filter.
- **Provider (BYOK):** API LLM OpenAI-compatible; ElevenLabs per la voce opzionale.
- **Installer:** Inno Setup (non firmato), distribuito via GitHub Releases.

## Struttura della repository

```
seed/            Pacchetto applicativo (runtime core, UI, capability builtin)
config/          Configurazione di esempio (config.example.json)
packaging/       Spec PyInstaller (ricette di build riproducibili)
installer/       Script Inno Setup + guida tester
scripts/         Script di build, release e quality gate
site/            Sito statico di distribuzione (GitHub Pages)
tests/           Suite di test
docs/            Documentazione di architettura e prodotto
assets/          Asset di brand (icona, mark)
benchmarks/      Benchmark locali
```

## Privacy e sicurezza

- I dati utente restano in `%LOCALAPPDATA%\SEED`; la disinstallazione chiede se
  conservarli o eliminarli.
- Le chiavi provider sono cifrate con DPAPI e mai scritte in chiaro.
- Nessun upload automatico di memoria, tracce o lineage.
- La ricerca online è un modulo separato, spento di default, con query filtrate
  dal privacy gate.

Hai trovato un problema di sicurezza? Segnalalo privatamente al maintainer
invece di aprire una issue pubblica.

## Come contribuire

I contributi sono benvenuti — vedi [CONTRIBUTING.md](CONTRIBUTING.md). È un
progetto pilota: apri una issue per discutere modifiche sostanziali prima di
implementarle.

## Licenza

[GNU AGPL-3.0](LICENSE). Se esegui una versione modificata di SEED come servizio
di rete, devi rendere disponibile il sorgente della tua versione ai suoi utenti.
