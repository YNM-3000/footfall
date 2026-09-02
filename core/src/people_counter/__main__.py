"""Enables `python -m people_counter ...`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
