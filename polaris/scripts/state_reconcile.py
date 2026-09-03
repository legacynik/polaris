#!/usr/bin/env python3
"""state_reconcile — the deterministic core of /polaris-status's state-decay check.

The gap it closes: /update never closes a thread and /end only closes on merge-evidence, so if you
only /update, a DONE thread stays stuck in state/current.md forever (at best a 14d `stale?` flag).
This runs on-demand (from /polaris-status, NOT the per-session hot paths) and, per thread in `## Open`,
resolves it against GROUND TRUTH (is its branch merged?) — the vault's own rule "recall != stato
attuale, lo stato si risolve su codice/GitHub". It PROPOSES fixes (close superseded, flag stale); it
never writes — /polaris-status is observe-only, the founder confirms.

Bounded (one git check per thread), graceful (unresolvable → 'unverified', never blocks), propose-only.

Usage: state_reconcile.py [path] [--repo-dir .] [--apply]   (prints the proposal; --apply
       removes the provably-merged threads, which is `/end`'s step; default path =
       the MAIN worktree's cockpit, resolved by state_home — never a cwd-relative one)
       state_reconcile.py --selfcheck
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
import sys as _sys

_sys.path.insert(0, __file__.rsplit('/', 1)[0])
from merge_truth import git_merged  # noqa: E402  (sibling script, no package on disk)
from state_staleness import _lane_id  # noqa: E402
from state_upsert import _locked, _section, _write_atomic  # noqa: E402  (one lock, one writer)

# is_merged(branch) -> True (merged into origin/main), False (not), None (unverified). Injected for tests.
MergeChecker = Callable[[str], "bool | None"]
_THREAD = re.compile(r"^-\s+`([^`]+)`(?:\s+\(([^)]+)\))?.*?(?:since\s+([\d-]+))?\s*$")


def parse_threads(text: str) -> list[dict]:
    """Threads from the `## Open` section: {branch, repo, since, line}. First backtick token = branch."""
    out, in_open = [], False
    for no, line in enumerate(text.splitlines()):
        if line.startswith("## "):
            in_open = line.strip().lower().startswith("## open")
            continue
        m = _THREAD.match(line) if in_open else None
        if m:
            out.append({"branch": m.group(1), "repo": m.group(2) or "", "no": no,
                        "since": m.group(3) or "", "line": line})
    return out


def classify(threads: list[dict], is_merged: MergeChecker, here: str = "") -> dict[str, list[dict]]:
    """Split threads into superseded (branch merged), unverified, and active.

    A thread carries the repo it belongs to and the cockpit is explicitly cross-repo. Judging
    a foreign branch against whatever repo was passed deletes live work whenever the name
    happens to exist here too, and then credits the local evidence to the other repo. A
    foreign thread is UNVERIFIED, never closed: the burden of proof is on removing.
    """
    buckets: dict[str, list[dict]] = {"superseded": [], "unverified": [], "active": []}
    for t in threads:
        if t["branch"] in ("main", "master", ""):  # trunk threads aren't feature branches; leave to human
            buckets["active"].append(t)
            continue
        if t["repo"] and here and t["repo"] != here:
            buckets["unverified"].append(dict(t, why="other repository"))
            continue
        m = is_merged(t["branch"])
        buckets["superseded" if m is True else "unverified" if m is None else "active"].append(t)
    return buckets


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


def reconcile(state_path: Path, repo_dir: str, apply: bool = False) -> str:
    """The proposal, and with `apply` the removal of the threads proved merged.

    The removal lived in a function the CLI never called, so closing a settled thread was a
    command someone had to remember — and `/update` never closes. `/end` owns this step now.
    Nothing is removed on an unverifiable branch: `git_merged` returns None and the thread
    stays `unverified`.
    """
    threads = parse_threads(state_path.read_text())
    here = Path(repo_dir).resolve().name
    buckets = classify(threads, lambda b: git_merged(b, repo_dir), here)
    if not apply:
        return report(buckets)
    removed = apply_cleanup(state_path, buckets["superseded"])
    return f"{report(buckets)}\nAPPLIED: {removed} superseded thread(s) removed"


def _survivors(lines: list[str], span: tuple[int, int], keys: set[str]) -> list[str]:
    """Every line except the settled threads inside `span` — header and indented children."""
    keep, dropping = [], False
    for i, ln in enumerate(lines):
        if not span[0] <= i < span[1]:
            keep.append(ln)                      # outside `## Open`: never ours to remove
            continue
        if ln.strip() and not ln[:1].isspace():  # a thread header, not one of its children
            dropping = _lane_id(ln) in keys
        elif not ln.strip():
            dropping = False                     # a blank line ends the thread
        if not dropping:
            keep.append(ln)
    return keep


def apply_cleanup(state_path: Path, superseded: list[dict]) -> int:
    """Remove settled threads — header and children — by key, in `## Open`, under the lock.

    Text-matching swept `## Next` too; parse-time indices were worse, because any write
    between the read and the apply (another panel's /update, or the stamp collapsing three
    stacked `Updated:` lines) shifted them and deleted a LIVE lane. Re-resolve by key on the
    content about to be written, inside the writer's own lock, and replace atomically.
    """
    keys = {_lane_id(t["line"]) for t in superseded}
    if not keys:
        return 0
    with _locked(state_path):
        lines = state_path.read_text().splitlines()
        keep = _survivors(lines, _section(lines, "thread"), keys)
        _write_atomic(state_path, "\n".join(keep) + "\n")
    return len(lines) - len(keep)


def _selfcheck_apply(txt: str, b: dict) -> None:
    """--apply removes ONLY the superseded line; active/main/Next survive byte-for-byte."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        sp = Path(d) / "s.md"
        sp.write_text(txt)
        n = apply_cleanup(sp, b["superseded"])
        after = sp.read_text()
        assert n == 1 and "feat/done-123" not in after, after
        assert "feat/live-456" in after and "`main`" in after and "## Next" in after, after


def _selfcheck() -> None:
    txt = ("# Current\n## Open\n"
           "- `feat/done-123` (_polaris) — shipped · since 2026-07-01\n"
           "- `feat/live-456` (acme-web) — in progress · since 2026-07-18\n"
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
    _selfcheck_apply(txt, b)
    print("SELF-CHECK OK: parse Open, merged->superseded, main/unverified stay, propose-only, --apply surgical")


def default_state_path() -> Path:
    """The repo's ONE cockpit, resolved against the MAIN worktree — never the panel's cwd.

    `apply_cleanup` REWRITES this file, and a cwd-relative default made that write land on
    the gitignored copy stranded inside a worktree (polaris-os#34). Fail-open on purpose:
    this whole script is observe-only and must never become a failing gate.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import state_home
        return Path(state_home.resolve()["cockpit"])
    except Exception:
        return Path("state/current.md")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--selfcheck" in argv:
        _selfcheck()
        return 0
    repo_dir = argv[argv.index("--repo-dir") + 1] if "--repo-dir" in argv else "."
    positional = [a for a in argv if not a.startswith("--") and a != repo_dir]
    state_path = Path(positional[0]) if positional else default_state_path()
    if not state_path.exists():
        print(f"no state file at {state_path}", file=sys.stderr)
        return 0
    print(reconcile(state_path, repo_dir, "--apply" in argv))
    return 0  # observe-only, never a failing gate


if __name__ == "__main__":
    sys.exit(main())
