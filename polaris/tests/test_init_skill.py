"""The `init` door's scripts prove themselves without a vault."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_installed_copy_proves_itself_without_a_vault() -> None:
    """The skills CLI installs `init/` next to `architecture/`: that layout must run."""
    done = subprocess.run(
        [sys.executable, "-I", str(ROOT / "skills" / "init" / "scripts" / "polaris_init.py"),
         "--selfcheck"], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "no-pointer=ok" in done.stdout
