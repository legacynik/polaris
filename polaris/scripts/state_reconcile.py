#!/usr/bin/env python3
"""state_reconcile — the deterministic core of /polaris-status's state-decay check.

The gap it closes: /update never closes a thread and /end only closes on merge-evidence, so if you
only /update, a DONE thread stays stuck in state/current.md forever (at best a 14d `stale?` flag).
This runs on-demand (from /polaris-status, NOT the per-session hot paths) and, per thread in `## Open`,
resolves it against GROUND TRUTH (is its branch merged?) — the vault's own rule "recall != stato
attuale, lo stato si risolve su codice/GitHub". It PROPOSES fixes (close superseded, flag stale); it
never writes — /polaris-status is observe-only, the founder confirms.

Bounded (one git check per thread), graceful (unresolvable → 'unverified', never blocks), propose-only.

Usage: state_reconcile.py [state/current.md] [--repo-dir .]   (prints the proposal)
       state_reconcile.py --selfcheck
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

# is_merged(branch) -> True (merged into origin/main), False (not), None (unverified). Injected for tests.
MergeChecker = Callable[[str], "bool | None"]
_THREAD = re.compile(r"^-\s+`([^`]+)`(?:\s+\(([^)]+)\))?.*?(?:since\s+([\d-]+))?\s*$")


def parse_threads(text: str) -> list[dict]:
    """Threads from the `## Open` section: {branch, repo, since, line}. First backtick token = branch."""
    out, in_open = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            in_open = line.strip().lower().startswith("## open")
            continue
        m = _THREAD.match(line) if in_open else None
        if m:
            out.append({"branch": m.group(1), "repo": m.group(2) or "", "since": m.group(3) or "", "line": line})
    return out


def classify(threads: list[dict], is_merged: MergeChecker) -> dict[str, list[dict]]:
    """Split threads into superseded (branch merged), unverified, and active."""
    buckets: dict[str, list[dict]] = {"superseded": [], "unverified": [], "active": []}
    for t in threads:
        if t["branch"] in ("main", "master", ""):  # trunk threads aren't feature branches; leave to human
            buckets["active"].append(t)
            continue
        m = is_merged(t["branch"])
        buckets["superseded" if m is True else "unverified" if m is None else "active"].append(t)
    return buckets


def git_merged(branch: str, repo_dir: str) -> bool | None:
    """True if `branch`'s tip is an ancestor of origin/main (i.e. merged). None if unresolvable."""
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", branch, "origin/main"],
                           cwd=repo_dir, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return True if r.returncode == 0 else False if r.returncode == 1 else None


def report(buckets: dict[str, list[dict]]) -> str:
    """The propose-only alignment: what to close, what couldn't be verified. Never writes."""
    lines = []
    if buckets["superseded"]:
        lines.append("PROPOSE CLOSE (branch merged into origin/main — superseded, verified):")
        lines += [f"  - `{t['branch']}` {t['repo']} — /end can close this against merge evidence." for t in buckets["superseded"]]
    if buckets["unverified"]:
        lines.append("UNVERIFIED (branch not resolvable here — check in its repo):")
        lines += [f"  - `{t['branch']}` {t['repo']}" for t in buckets["unverified"]]
    lines.append(f"ACTIVE (live, keep — resurface these on top): {len(buckets['active'])} thread(s).")
    if not buckets["superseded"] and not buckets["unverified"]:
        lines.insert(0, "state aligned — no superseded threads detected against ground truth.")
    return "\n".join(lines)


def reconcile(state_path: Path, repo_dir: str) -> str:
    threads = parse_threads(state_path.read_text())
    return report(classify(threads, lambda b: git_merged(b, repo_dir)))


def apply_cleanup(state_path: Path, superseded: list[dict]) -> int:
    """Surgically remove ONLY the confirmed-superseded thread lines; every other byte is preserved.
    Never touches active/unverified/other-panel threads. Returns count removed. Caller gates on confirm."""
    drop = {t["line"] for t in superseded}
    kept = [ln for ln in state_path.read_text().splitlines() if ln not in drop]
    state_path.write_text("\n".join(kept) + "\n")
    return len(drop)


def _selfcheck() -> None:
    txt = ("# Current\n## Open\n"
           "- `feat/done-123` (_polaris) — shipped · since 2026-07-01\n"
           "- `feat/live-456` (noemi) — in progress · since 2026-07-18\n"
           "- `main` (_polaris) — trunk work · since 2026-07-19\n"
           "## Next\n- `feat/live-456`: next step\n")
    threads = parse_threads(txt)
    assert [t["branch"] for t in threads] == ["feat/done-123", "feat/live-456", "main"], threads
    fake = {"feat/done-123": True, "feat/live-456": False}.get  # merged / not / (main handled separately)
    b = classify(threads, fake)
    assert [t["branch"] for t in b["superseded"]] == ["feat/done-123"], b
    assert {t["branch"] for t in b["active"]} == {"feat/live-456", "main"}, b  # main stays active (human)
    assert classify(threads, lambda _b: None)["unverified"][0]["branch"] == "feat/done-123"  # graceful
    out = report(b)
    assert "PROPOSE CLOSE" in out and "feat/done-123" in out and "feat/live-456" not in out.split("ACTIVE")[0]
    # --apply removes ONLY the superseded thread line; active/main/Next preserved byte-for-byte
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        sp = Path(d) / "s.md"
        sp.write_text(txt)
        n = apply_cleanup(sp, b["superseded"])
        after = sp.read_text()
        assert n == 1 and "feat/done-123" not in after, after
        assert "feat/live-456" in after and "`main`" in after and "## Next" in after, after
    print("SELF-CHECK OK: parse Open, merged->superseded, main/unverified stay, propose-only, --apply surgical")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--selfcheck" in argv:
        _selfcheck()
        return 0
    repo_dir = argv[argv.index("--repo-dir") + 1] if "--repo-dir" in argv else "."
    positional = [a for a in argv if not a.startswith("--") and a != repo_dir]
    state_path = Path(positional[0]) if positional else Path("state/current.md")
    if not state_path.exists():
        print(f"no state file at {state_path}", file=sys.stderr)
        return 0
    print(reconcile(state_path, repo_dir))
    return 0  # observe-only, never a failing gate


if __name__ == "__main__":
    sys.exit(main())
