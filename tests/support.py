"""Keep generated test files inside the checkout, including on restricted hosts."""

import tempfile
from pathlib import Path


def temporary_directory():
    root = Path(__file__).resolve().parents[1] / "is" / "tests"
    root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=root)
