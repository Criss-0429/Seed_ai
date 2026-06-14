"""Package-aware PyInstaller entrypoint for the external SEED supervisor."""

from seed.supervisor_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
