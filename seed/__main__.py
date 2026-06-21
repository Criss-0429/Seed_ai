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


def _cap_native_threads() -> None:
    """Limita i thread nativi PRIMA di importare numpy/torch.

    BLAS/OMP/MKL allocano arene di memoria per-thread: su CPU con molti core la
    RAM (e quindi il pagefile su SSD) cresce in modo imprevedibile. Cap a 4
    rende il footprint piccolo e stabile. Rispetta eventuali override utente."""
    import os

    cap = str(max(1, min(4, (os.cpu_count() or 4))))
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ.setdefault(var, cap)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def main() -> int:
    argv = sys.argv[1:]
    _cap_native_threads()
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

    # Single-instance: se SEED gira gia', mostra quella finestra ed esci PRIMA
    # di caricare app/modelli/DB (evita processi accavallati e lock sul DB).
    gui_mode = not any(
        flag in argv for flag in ("--smoke", "--repl", "--run-tool", "--run-isolated-tool"))
    instance = None
    if gui_mode:
        from .ui.single_instance import SingleInstance
        instance = SingleInstance()
        if instance.already_running:
            instance.signal_show()
            logging.getLogger("seed").info(
                "SEED gia' attivo: mostro l'istanza esistente e termino.")
            return 0

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
    run_window(app, start_hidden="--background" in argv, instance=instance)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
