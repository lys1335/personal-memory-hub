"""Pytest configuration and base fixtures.

Per 10_8 (Testing Implementation Design):
- Deterministic-by-default (D1.7 itself is deterministic)
- Mock at boundaries (database fixture uses real in-memory SQLite)
- Test structure mirrors architecture layers (unit/, integration/, evaluation/)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the Python path for imports in all test files
_src = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(_src))
