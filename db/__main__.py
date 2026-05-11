"""
Run DB init from repository root:

    python -m db

Requires `backend/` on sys.path so `app.*` imports resolve.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from db.bootstrap import main

if __name__ == "__main__":
    main()
