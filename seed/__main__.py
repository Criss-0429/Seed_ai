"""Entrypoint SEED.

Modalita':
  seed             → finestra webview (app vera)
  seed --repl      → REPL console (dev)
  seed --run-tool <path>  → esegue un tool in sandbox (usato internamente
                            dal sandbox executor quando l'app e' frozen)
"""

from __future__ import annotations

import logging
import runpy
import sys


def _setup_logging() -> None:
    from .core import forbidden
    logdir = forbidden.seed_data_dir() / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(logdir / "seed.log", encoding="utf-8"),
                  logging.StreamHandler()])


def main() -> int:
    argv = sys.argv[1:]
    from .core.model_bundle import enforce_offline_if_bundled
    enforce_offline_if_bundled()

    # --- modalita' sandbox: processo figlio che esegue un tool --------------
    if len(argv) >= 2 and argv[0] == "--run-tool":
        # nessun setup logging, nessun accesso a config/key:
        # il parent ha gia' passato env minimale e CWD nel workspace
        runpy.run_path(argv[1], run_name="__main__")
        return 0
    if len(argv) >= 2 and argv[0] == "--run-isolated-tool":
        from .core.process_runner import main as isolated_main
        sys.argv = [sys.argv[0], argv[1]]
        return isolated_main()

    _setup_logging()
    from .core.app import SeedApp
    app = SeedApp()
    from .supervisor import emit_health_signal_from_env
    from .core import forbidden
    emit_health_signal_from_env(forbidden.seed_data_dir())

    if "--smoke" in argv:
        app.shutdown()
        return 0

    if "--repl" in argv:
        app.repl()
        return 0

    # --- finestra webview ----------------------------------------------------
    try:
        from .ui.shell import run_window
    except ImportError as exc:
        print(f"pywebview non disponibile ({exc}); avvio REPL.")
        app.repl()
        return 0
    run_window(app, start_hidden="--background" in argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
