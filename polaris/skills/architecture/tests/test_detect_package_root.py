"""detect.py pointed AT a package still sees the cycles its absolute imports close.

2026-09-30, a product-repo audit: `detect.py app` answered 0 cycles on a backend whose
`app.pipeline` and `app.services` import each other in a 15-module loop. Module names were
taken relative to the package itself (`pipeline.runner`), every import keeps its prefix
(`app.pipeline.runner`), so no edge ever matched and the gate read green. Break: name modules
relative to the root again and the cycle disappears.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

DETECT = Path(__file__).resolve().parents[1] / "scripts" / "detect.py"


def test_a_cycle_through_absolute_imports_is_found_from_the_package_root():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "app"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "a.py").write_text("import app.b\n")
        (pkg / "b.py").write_text("from app import a\n")
        done = subprocess.run([sys.executable, str(DETECT), str(pkg), "--json"],
                              capture_output=True, text=True)
    assert '"rule": "cycle"' in done.stdout, done.stdout + done.stderr
