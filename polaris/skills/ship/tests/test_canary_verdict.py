"""Post-deploy verification window: advance, hold, or propose a rollback, from metrics.

The metrics files are what the repository exposes before and after a production deploy
(health, error rate, p95 latency). Missing data is UNKNOWN and never advances the rollout.
The CLI is driven with real files; nothing is mocked.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "canary_check.py"
BASE = {"health_ok": True, "error_rate": 0.010, "p95_ms": 400}


def verdict(baseline, now):
    d = Path(tempfile.mkdtemp())
    (d / "b.json").write_text(json.dumps(baseline))
    (d / "n.json").write_text(json.dumps(now))
    return subprocess.run([sys.executable, str(SCRIPT), "verdict", "--baseline", str(d / "b.json"),
                           "--now", str(d / "n.json")], capture_output=True, text=True, timeout=30)


class VerificationWindow(unittest.TestCase):
    def test_metrics_close_to_baseline_advance(self):
        done = verdict(BASE, {"health_ok": True, "error_rate": 0.011, "p95_ms": 420})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(done.stdout.startswith("ADVANCE"), done.stdout)

    def test_error_rate_above_twice_the_baseline_proposes_a_rollback(self):
        done = verdict(BASE, {"health_ok": True, "error_rate": 0.025, "p95_ms": 400})
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertTrue(done.stdout.startswith("ROLLBACK proposed"), done.stdout)
        self.assertIn("error_rate", done.stdout)

    def test_p95_more_than_half_again_slower_proposes_a_rollback(self):
        done = verdict(BASE, {"health_ok": True, "error_rate": 0.010, "p95_ms": 610})
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("p95_ms", done.stdout)

    def test_health_turning_bad_proposes_a_rollback(self):
        done = verdict(BASE, {"health_ok": False, "error_rate": 0.010, "p95_ms": 400})
        self.assertEqual(done.returncode, 1, done.stdout)

    def test_a_moderate_regression_holds(self):
        done = verdict(BASE, {"health_ok": True, "error_rate": 0.015, "p95_ms": 400})
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertTrue(done.stdout.startswith("HOLD"), done.stdout)

    def test_a_missing_metric_is_unknown_and_never_advances(self):
        done = verdict(BASE, {"health_ok": True, "error_rate": 0.010})
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertIn("UNKNOWN p95_ms", done.stdout)

    def test_errors_appearing_on_a_zero_error_baseline_propose_a_rollback(self):
        done = verdict(dict(BASE, error_rate=0.0), {"health_ok": True, "error_rate": 0.02, "p95_ms": 400})
        self.assertEqual(done.returncode, 1, done.stdout)

    def test_an_unreadable_metrics_file_is_exit_2(self):
        d = Path(tempfile.mkdtemp())
        (d / "b.json").write_text("{nope")
        (d / "n.json").write_text("{}")
        done = subprocess.run([sys.executable, str(SCRIPT), "verdict", "--baseline", str(d / "b.json"),
                               "--now", str(d / "n.json")], capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 2, done.stdout)


if __name__ == "__main__":
    unittest.main()
