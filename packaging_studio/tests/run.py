"""Run the Packaging Studio test suite.

Pure-Python tests (parser, classifier) run with any Python interpreter::

    python packaging_studio/tests/run.py

They also run inside Blender's Python. The core and utils subpackages have no
Blender dependency, so no ``bpy`` is required for these tests.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(
        str(Path(__file__).resolve().parent), pattern="test_*.py"
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
