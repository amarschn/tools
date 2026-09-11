"""Put the materials project root on sys.path for its own tests.

The builder, release and schema_lab packages import each other by their own
top-level names. This keeps that working now that the project is a
subdirectory of the tools repository, without rewriting every import.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
