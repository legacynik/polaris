"""polaris#40 round 1 — the session doors' installer selfcheck runs where nothing is installed."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

from host_repo import PKG


class TheSelfcheckRunsWhereNothingIsInstalled(unittest.TestCase):
    """C4 — the hook names `$CLAUDE_PLUGIN_ROOT`, and a checkout is not an installation."""

    def test_install_settings_selfcheck_passes_with_no_installed_copy_on_the_machine(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDE_PLUGIN_ROOT", "POLARIS_VAULT")}
        done = subprocess.run([sys.executable,
                               str(PKG / "skills" / "start" / "scripts" / "install_settings.py"),
                               "--selfcheck"], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
