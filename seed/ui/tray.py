"""Icona di sistema (tray) per la modalita' background — ispirata a Wispr Flow.

SEED si riduce a una piccola icona in background; da li' si apre la finestra
piena o la "cattura rapida" (overlay command-bar), che resta anche evocabile
ovunque con la shortcut globale Ctrl+Spazio (vedi shell._start_overlay_hotkey).

Dipendenza OPZIONALE: `pystray` + `Pillow`. Se assenti, niente tray ma la
shortcut globale resta attiva: la feature degrada, non si rompe.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable

log = logging.getLogger("seed.ui.tray")

_ICON = Path(__file__).resolve().parents[1] / "assets" / "seed.ico"


def start_tray(
    *,
    on_open: Callable[[], None],
    on_quick: Callable[[], None],
    on_quit: Callable[[], None],
) -> object | None:
    """Avvia l'icona tray in un thread daemon. Ritorna l'icona o None.

    - click sinistro / "Apri SEED": finestra piena
    - "Cattura rapida": overlay command-bar (parla o scrivi al volo)
    - "Esci": termina SEED
    """
    try:
        import pystray
        from PIL import Image
    except Exception as exc:  # dep assente: degrada, shortcut globale resta
        log.info("tray non disponibile (%s): Ctrl+Spazio resta attivo", exc)
        return None

    try:
        image = Image.open(_ICON) if _ICON.is_file() else Image.new("RGB", (64, 64))
    except Exception as exc:
        log.warning("icona tray non caricata (%s)", exc)
        image = Image.new("RGB", (64, 64))

    def _wrap(fn: Callable[[], None]) -> Callable[..., None]:
        def _handler(icon=None, item=None) -> None:
            try:
                fn()
            except Exception as exc:
                log.warning("azione tray fallita: %s", exc)
        return _handler

    def _quit(icon=None, item=None) -> None:
        try:
            on_quit()
        except Exception as exc:
            log.warning("uscita da tray fallita: %s", exc)
        finally:
            try:
                icon = icon or tray
                icon.stop()
            except Exception:
                pass

    menu = pystray.Menu(
        pystray.MenuItem("Apri SEED", _wrap(on_open), default=True),
        pystray.MenuItem("Cattura rapida  (Ctrl+Spazio)", _wrap(on_quick)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Esci", _quit),
    )
    tray = pystray.Icon("SEED", image, "SEED", menu)
    threading.Thread(target=tray.run, name="seed-tray", daemon=True).start()
    log.info("tray attiva: SEED vive in background")
    return tray
