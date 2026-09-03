#!/usr/bin/env python3
"""Replay a *-skillopt.tasks.json suite against two versions of its skill.

  replay_tasks.py <skill> <baseline-ref>      e.g. replay_tasks.py update 498ed70~1

The point is not "does the new version pass" — it is verify-red: a case that passes
on BOTH versions proves nothing about the change, and a suite full of those reports
green while testing nothing. Every run therefore prints, per case, whether it
DISCRIMINATES, is a regression guard, or is dead weight.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

# The vendored skillopt_sleep backend lives in the private OS repository, which is not this
# package. Declare it per machine — a literal home directory in a public package looks for a
# folder that exists on exactly one laptop, and ships that laptop's owner with it.
VENDOR = Path(os.environ.get("POLARIS_VENDOR_DIR", Path.home() / ".polaris" / "vendor"))
if not VENDOR.is_dir():
    sys.exit(f"replay_tasks: no vendored skillopt_sleep at {VENDOR} — "
             "set POLARIS_VENDOR_DIR to the checkout that carries it")
sys.path.insert(0, str(VENDOR))

from skillopt_sleep.backend import ClaudeCliBackend  # noqa: E402
from skillopt_sleep.replay import replay_one  # noqa: E402
from skillopt_sleep.types import TaskRecord  # noqa: E402

PLUGIN = Path.home() / "dev/polaris-plugin"
SKILL = sys.argv[1] if len(sys.argv) > 1 else "update"
BASELINE = sys.argv[2] if len(sys.argv) > 2 else "HEAD~1"
TASKS = PLUGIN / f"polaris/evals/{SKILL}-skillopt.tasks.json"


def skill_text(ref: str | None) -> str:
    rel = f"polaris/skills/{SKILL}/SKILL.md"
    if ref is None:
        return (PLUGIN / rel).read_text()
    return subprocess.run(["git", "-C", str(PLUGIN), "show", f"{ref}:{rel}"],
                          capture_output=True, text=True, check=True).stdout


def to_record(d: dict) -> TaskRecord:
    return TaskRecord(
        id=d["id"], project=d.get("project", ""), intent=d["intent"],
        context_excerpt=d.get("context_excerpt", ""), outcome=d.get("outcome", "success"),
        reference_kind=d.get("reference_kind", "rule"), judge=d.get("judge"),
        tags=d.get("tags", []), source_sessions=d.get("source_sessions", []),
        split=d.get("split", "train"), origin=d.get("origin", "real"),
    )


def main() -> int:
    tasks = [to_record(t) for t in json.loads(TASKS.read_text())["tasks"]]
    old, new = skill_text(BASELINE), skill_text(None)
    print(f"{SKILL}: baseline {BASELINE} ({len(old)} char) vs HEAD ({len(new)} char) · {len(tasks)} casi\n")
    backend = ClaudeCliBackend()
    rows = []
    for t in tasks:
        r_old = replay_one(backend, t, old, "")
        r_new = replay_one(backend, t, new, "")
        o, n = r_old.hard >= 1.0, r_new.hard >= 1.0
        verdict = ("DISCRIMINA" if (n and not o) else
                   "non-discriminante" if (n and o) else
                   "REGRESSIONE" if (o and not n) else "rosso su entrambe")
        rows.append((t.id, o, n, verdict, r_new.fail_reason[:70]))
        print(f"{t.id:38} old={'✓' if o else '✗'} new={'✓' if n else '✗'}  {verdict}")
        if not n and r_new.fail_reason:
            print(f"{'':38} → {r_new.fail_reason[:100]}")
    print()
    disc = sum(1 for r in rows if r[3] == "DISCRIMINA")
    print(f"discriminanti {disc}/{len(rows)} · new verdi {sum(1 for r in rows if r[2])}/{len(rows)}")
    Path(__file__).with_name(f"{SKILL}-replay-results.json").write_text(json.dumps(
        [{"id": r[0], "old": r[1], "new": r[2], "verdict": r[3]} for r in rows], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
