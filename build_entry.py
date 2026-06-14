"""PyInstaller entrypoint.

Import SEED as a package so relative imports inside ``seed.__main__`` retain
their known parent package in the frozen executable.
"""

from seed.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
