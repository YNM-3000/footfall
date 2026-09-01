#!/usr/bin/env python3
"""Entrypoint shim: `uv run people_counter.py SOURCE [options]`.

The implementation lives in `src/people_counter/`. This file only exists so
the documented one-liner keeps working. Because it sits at the repo root
with the same name as the package, it would otherwise shadow it — so `src`
goes on `sys.path` first, and an imported shim hands over to the real
package rather than pretending to be it.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

if __name__ == "__main__":
    from people_counter.cli import main

    raise SystemExit(main())

# Imported, not executed: someone ran `import people_counter` with the repo
# root on sys.path and reached this shim. Swap in the real package — CPython
# re-reads sys.modules after executing a module, so submodule imports
# (`people_counter.cli`, ...) resolve against the package from here on.
del sys.modules[__name__]
sys.modules[__name__] = importlib.import_module("people_counter")
