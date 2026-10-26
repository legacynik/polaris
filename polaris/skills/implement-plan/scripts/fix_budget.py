#!/usr/bin/env python3
"""fix_budget.py — the fix loop's circuit breaker (gstack /qa self-regulation, adapted).

The score is read from git since the task base (HEAD at claim, noted on the bead), so a resumed
orchestrator gets the same number: +15 per revert commit, +20 per file touched outside the
task's declared scope (committed, staged, unstaged or untracked). Above 20 the loop stops and
a human decides.

    fix_budget.py --repo R --base SHA --scope GLOB [--scope GLOB ...]
    fix_budget.py --selfcheck

Exit: 0 keep going · 1 STOP, report to the human · 2 usage error (fail closed).
"""
import argparse
import fnmatch
import subprocess
import sys
import tempfile
from pathlib import Path

# ponytail: gstack's weights and threshold as is; tune once real loops have been measured.
REVERT, UNRELATED, STOP_ABOVE = 15, 20, 20


def git(repo, *args):
    # quotepath off: a non-ASCII path comes back as itself, not as "caf\303\251.py"
    r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args],
                       capture_output=True, text=True)
    if r.returncode:
        raise ValueError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r.stdout.splitlines()


def measure(repo, base, scope):
    """(score, reverts, unrelated files). ValueError when git cannot read the base."""
    try:
        git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    except ValueError:
        raise ValueError(f"unknown base {base!r} in {repo}")
    # ponytail: a revert is a commit titled "Revert …" (git revert's default); hand-made
    # reverts under another title are not seen.
    reverts = [s for s in git(repo, "log", "--format=%s", f"{base}..HEAD") if s.startswith("Revert ")]
    # --no-renames: a file moved into the scope still shows where it came from
    touched = set(git(repo, "diff", "--no-renames", "--name-only", base))
    touched |= set(git(repo, "ls-files", "--others", "--exclude-standard"))
    # fnmatch: `*` crosses `/`, so `src/*` covers every file under src/
    unrelated = sorted(f for f in touched if not any(fnmatch.fnmatch(f, g) for g in scope))
    return REVERT * len(reverts) + UNRELATED * len(unrelated), reverts, unrelated


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", required=True, help="the task base SHA (HEAD when the task was claimed)")
    ap.add_argument("--scope", action="append", required=True,
                    help="a path glob the task declared (repeat)")
    a = ap.parse_args(argv)
    try:
        score, reverts, unrelated = measure(a.repo, a.base, a.scope)
    except ValueError as e:
        print(f"fix_budget: {e}", file=sys.stderr)
        return 2
    line = f"score {score} (stop above {STOP_ABOVE}): {len(reverts)} reverts, " \
           f"{len(unrelated)} files outside the scope{': ' + ', '.join(unrelated) if unrelated else ''}"
    if score > STOP_ABOVE:
        print(f"STOP — {line}. The fix loop is not converging: report to the human, change nothing.")
        return 1
    print(f"ok — {line}")
    return 0


def selfcheck():
    with tempfile.TemporaryDirectory() as d:
        for args in (["init", "-q"], ["config", "user.email", "s@x"], ["config", "user.name", "s"]):
            git(d, *args)
        (Path(d) / "a.py").write_text("0\n")
        git(d, "add", "a.py")
        git(d, "commit", "-q", "-m", "base")
        base = git(d, "rev-parse", "HEAD")[0]
        assert main(["--repo", d, "--base", base, "--scope", "*.py"]) == 0
        for i in (1, 2):
            (Path(d) / "a.py").write_text(f"{i}\n")
            git(d, "commit", "-qam", f"fix {i}")
            git(d, "revert", "--no-edit", "HEAD")
        assert main(["--repo", d, "--base", base, "--scope", "*.py"]) == 1, "two reverts stop"
        assert main(["--repo", d, "--base", "0" * 40, "--scope", "*.py"]) == 2, "bad base fails closed"
    print("fix_budget selfcheck: ok")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if sys.argv[1:] == ["--selfcheck"] else main())
