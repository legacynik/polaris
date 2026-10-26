"""A `--field` cannot replace the validated dedup or adversarial evidence on a template that asks for it.

Breaker, 2026-10-09: once those template fields were filled from `--dedup` and `--adv-test`, a
`--field not-a-duplicate="trust me"` replaced the Searched/Found text and the builder dropped its own
block, so the validated evidence vanished from the issue with exit 0. The acceptance-criteria field
already refuses an override for this reason; the two contract fields now do the same.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from test_template_contract_fields import ADV, DEDUP, SCRIPT, TASK


def builder(*extra: str) -> subprocess.CompletedProcess:
    repo = Path(tempfile.mkdtemp()) / "acme-api"
    (repo / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    (repo / ".github" / "ISSUE_TEMPLATE" / "task.yml").write_text(TASK)
    args = ["--repo-path", str(repo), "--repo-slug", "acme/acme-api", "--type", "task",
            "--title", "Invoice totals round to two decimals",
            "--ac", "`GET /invoices/7` returns `total` with 2 decimals, exit 0",
            "--exec", "Oggi i totali delle fatture escono con troppi decimali.",
            "--dedup", DEDUP, "--domain", "billing", "--priority", "p1", "--afk", "no",
            "--category", "bug", "--impact", "2", "--cost", "S", *extra]
    for test in ADV:
        args += ["--adv-test", test]
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_an_override_of_the_validated_evidence_is_refused():
    for field in ("not-a-duplicate=trust me", "adversarial-verification=TBD"):
        done = builder("--field", field)
        assert (done.returncode, field.split("=")[0] in done.stdout) == (2, True), done.stdout
