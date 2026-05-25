"""
MediaMitigator — Application entry point.

Run with:  python src/main.py

Author: Nathan
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path when run directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.app import run

if __name__ == "__main__":
    sys.exit(run())
