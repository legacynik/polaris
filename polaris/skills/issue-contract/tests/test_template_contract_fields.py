"""A repo template that asks for the contract's own fields is filled by the contract's own flags.

Field report 2026-10-09 (a product repo's `task.yml`): the template declares required fields with
ids `not-a-duplicate`, `adversarial-verification`, `domain`, `priority`, `afk`. Every one of them was
passed (`--dedup`, `--adv-test`, `--domain`, `--priority`, `--afk`) and the builder still exited 2,
asking for each again as `--field`. Five issues were created only with that double entry.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_issue.py"

# The shape of the real template, field ids and labels verbatim; the domain list is a placeholder.
TASK = """name: Task
description: Contract-complete task (issue-contract standard)
labels: ["task"]
body:
  - type: textarea
    id: executive
    attributes:
      label: Executive (italiano semplice)
    validations: {required: true}
  - type: textarea
    id: not-a-duplicate
    attributes:
      label: Not a duplicate because
    validations: {required: true}
  - type: textarea
    id: context
    attributes:
      label: Context
    validations: {required: false}
  - type: textarea
    id: acceptance-criteria
    attributes:
      label: Acceptance criteria
    validations: {required: true}
  - type: textarea
    id: adversarial-verification
    attributes:
      label: Adversarial verification (run before merge/deploy)
    validations: {required: true}
  - type: textarea
    id: out-of-scope
    attributes:
      label: Out of scope
    validations: {required: false}
  - type: dropdown
    id: domain
    attributes:
      label: Domain
      options:
        - billing
        - platform
    validations: {required: true}
  - type: dropdown
    id: priority
    attributes:
      label: Priority
      options: [p0, p1, p2, p3]
    validations: {required: true}
  - type: dropdown
    id: afk
    attributes:
      label: AFK eligibility (may an unattended agent claim this?)
      options: [yes, no]
    validations: {required: true}
"""
DEDUP = "Searched: gh issue list --search invoice rounding. Found: none."
ADV = ["`pytest tests/test_rounding.py` (new) red before the fix, green after",
       "`curl /invoices/7` returns 200 with 2 decimals, not 500"]


def run_builder() -> subprocess.CompletedProcess:
    repo = Path(tempfile.mkdtemp()) / "acme-api"
    (repo / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    (repo / ".github" / "ISSUE_TEMPLATE" / "task.yml").write_text(TASK)
    args = ["--repo-path", str(repo), "--repo-slug", "acme/acme-api", "--type", "task",
            "--title", "Invoice totals round to two decimals",
            "--ac", "`GET /invoices/7` returns `total` with 2 decimals, exit 0",
            "--exec", "Oggi i totali delle fatture escono con troppi decimali.",
            "--dedup", DEDUP, "--domain", "billing", "--priority", "p1", "--afk", "no",
            "--category", "bug", "--impact", "2", "--cost", "S"]
    for test in ADV:
        args += ["--adv-test", test]
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def section(body: str, label: str) -> str:
    """The text under `### <label>` up to the next heading."""
    after = body.split(f"### {label}\n", 1)[1]
    return after.split("\n#", 1)[0].strip()


def test_the_contract_flags_fill_the_template_fields_that_ask_for_them():
    done = run_builder()
    assert done.returncode == 0, done.stdout + done.stderr
    body = done.stdout
    assert {label: section(body, label) for label in (
        "Not a duplicate because", "Adversarial verification (run before merge/deploy)",
        "Domain", "Priority", "AFK eligibility (may an unattended agent claim this?)")} == {
        "Not a duplicate because": DEDUP,
        "Adversarial verification (run before merge/deploy)": "\n".join(f"- [ ] {t}" for t in ADV),
        "Domain": "billing", "Priority": "p1",
        "AFK eligibility (may an unattended agent claim this?)": "no"}
