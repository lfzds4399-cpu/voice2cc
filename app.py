"""voice2ai.py — entry-point shim.

The actual code lives in src/voice2ai/. This shim makes `python voice2ai.py` and
the legacy `start.bat` keep working without users learning a new command.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make src/ importable when running from the project root
_HERE = Path(__file__).resolve().parent
_SRC = _HERE / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from voice2ai.main import run  # noqa: E402


if __name__ == "__main__":
    sys.exit(run())
