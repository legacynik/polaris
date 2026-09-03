#!/usr/bin/env python3
"""brief_signals — the read-only half of /start: what the system already knows.

Three signals exist today and nothing reads them (polaris-os#243): the deferred session-log
spool, the drift of the MAIN worktree, and the sections a state file has lost. Two more
surfaces landed with the donor's four-file form and had no reader (#240): `state/todos.md`
and `## Recent Context`. And a repo that carries the typed backbone should have its pack id
in the brief, while a repo without one must not even learn that the feature exists (#155).

Every line is emitted ONLY when it has something to say. A row that always reads zero is
noise, and noise is what teaches a reader to skip the brief. Nothing here writes, nothing
fetches, and a missing input is never an error: a brief that fails is worse than a thin one.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# ONE line model for the whole package: the donor writes state as TABLES, and a bullet-only reader
# reported `TODOS_ACTIVE=0` on the real file while quietly losing an overdue follow-up.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "update" / "scripts"))
from state_lines import kinds, table_row  # noqa: E402

# The sections a state file owes. `state_contract.py` in a repo that has one is asked first;
# this is the answer for the host repos that ship only the package.
REGISTRY = {"current.md": ("## Active Priorities", "## Open", "## Recent Context"),
            "todos.md": ("## Active", "## Completed", "## Follow-ups")}
PLACEHOLDER = re.compile(r"^[\s|*]*(none|nessuno)?[\s|*]*$", re.I)
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
ENTRY = re.compile(r"^###\s+(.*)$")
MAX_ROWS = 5


def section(text: str, name: str) -> list[str]:
    """The state lines under `name` — bullets or table rows — minus the empty placeholders."""
    lines = text.splitlines()
    tags, out, inside = kinds(lines), [], False
    for i, line in enumerate(lines):
        if line.startswith("## "):
            inside = line.strip() == name
        elif inside and tags[i] == "thread" and not PLACEHOLDER.match(line):
            out.append(line.strip())
    return out


def due_on(row: str) -> str:
    """The review date of a follow-up: the second cell of a table row, or the bullet's own date."""
    cells = table_row(row)
    if cells:
        return cells[1] if len(cells) > 1 and DATE.match(cells[1]) else ""
    found = re.search(r"Review(?: Date)?:\s*(\d{4}-\d{2}-\d{2})", row)
    return found.group(1) if found else ""


def emit_todos(root: Path, today: str) -> list[str]:
    """D1 — Active rows and the follow-ups that are actually due (polaris#3, #240)."""
    path = root / "state" / "todos.md"
    if not path.is_file():
        return ["TODOS=absent — no state/todos.md in this repo; the weekly plan is the only view"]
    text = path.read_text(encoding="utf-8")
    active = section(text, "## Active")
    rows = [f"TODOS_ACTIVE={len(active)}"] + [f"TODO={row}" for row in active[:MAX_ROWS]]
    for row in section(text, "## Follow-ups"):
        due = due_on(row)
        if due and due <= today:
            rows.append(f"FOLLOWUP_DUE={row}")
    return rows


def emit_recent(current: Path) -> list[str]:
    """D1 — the `## Recent Context` ring, newest first, as `/end` left it."""
    if not current.is_file():
        return []
    inside, out = False, []
    for line in current.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Recent Context"
        elif inside and ENTRY.match(line):
            out.append(f"RECENT={ENTRY.match(line).group(1).strip()}")
    return out[:3]


def git(root: Path, *args: str) -> str:
    """Read-only git, and a failure is simply no signal."""
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def emit_git(main_wt: Path, login: str) -> list[str]:
    """#243 signals 1 and 2 — the deferred spool, and the MAIN worktree parked off its default.

    The spool is counted under the git COMMON dir, which is where `session_commit.sh` really puts
    it: read as `.git/polaris-deferred` from a worktree, the count is always zero.
    """
    out, common = [], git(main_wt, "rev-parse", "--git-common-dir")
    if common:
        spool = Path(common if Path(common).is_absolute() else main_wt / common) / "polaris-deferred"
        n = len([p for p in spool.iterdir() if p.is_file()]) if spool.is_dir() else 0
        out += [f"DEFERRED={n} — session-log entries spooled, not committed"] if n else []
    branch = git(main_wt, "rev-parse", "--abbrev-ref", "HEAD")
    default = git(main_wt, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").split("/")[-1]
    default = default or ("main" if git(main_wt, "rev-parse", "--verify", "-q", "main") else "master")
    if not branch or branch == default:
        return out
    status = [ln for ln in git(main_wt, "status", "--porcelain").splitlines() if ln.strip()]
    foreign = [ln for ln in status if f"team/{login}/" not in ln]
    return out + [f"DRIFT={branch} · {len(foreign)} modified files not yours in the main worktree"]


def emit_sections(root: Path, current: Path) -> list[str]:
    """#243 signal 3 — the sections the state file lost. An absent file invents nothing."""
    out = []
    for path in (current, root / "state" / "todos.md"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [s for s in REGISTRY.get(path.name, ()) if s not in text]
        if missing:
            out.append(f"SECTIONS_MISSING={path.name}: {', '.join(missing)}")
    return out


def emit_pack(root: Path) -> list[str]:
    """D3 — feature-detect: with the typed backbone the brief carries the pack id, else nothing."""
    manifest, compiler = root / "decisions" / "manifest.json", root / "scripts" / "contextpack.py"
    if not (manifest.is_file() and compiler.is_file()):
        return []
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    pack = data.get("pack_id") or data.get("id")
    return [f"PACK={pack}"] if pack else []


def report(opts: argparse.Namespace) -> list[str]:
    """Every signal, in brief order. Read-only, and a missing input is a silent line."""
    root, current = Path(opts.root), Path(opts.current)
    main_wt = Path(opts.main_wt) if opts.main_wt else root.parent
    return (emit_todos(root, opts.now) + emit_recent(current)
            + emit_git(main_wt, opts.login) + emit_sections(root, current) + emit_pack(root))


def _fixture(tmp: Path) -> tuple[Path, Path]:
    """A root carrying a todos file with one due and one future follow-up."""
    root = tmp / "_polaris"
    (root / "state").mkdir(parents=True)
    (root / "state" / "todos.md").write_text(
        "## Active\n\n| Task | Added | Context |\n|---|---|---|\n| #1 — x | W32 | |\n"
        "| | | |\n\n## Completed\n\n| Task | Completed | Note |\n|---|---|---|\n"
        "| *None* | | |\n\n## Follow-ups\n\n| Item | Review Date | Note |\n|---|---|---|\n"
        "| scaduto | 2000-01-01 | |\n| futuro | 2999-01-01 | |\n")
    current = root / "state" / "current.md"
    current.write_text("Updated: 2026-09-03 — @ada\n\n## Recent Context\n\n### b\n\n### a\n")
    return root, current


def cmd_selfcheck() -> int:
    """One fixture per branch that would put a wrong or a missing line in the brief."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root, current = _fixture(Path(d))
        opts = argparse.Namespace(root=str(root), current=str(current), login="ada",
                                  main_wt=d, now="2026-09-03")
        out = report(opts)
        ok = ["TODOS_ACTIVE=1" in out,
              any(o.startswith("FOLLOWUP_DUE=") and "scaduto" in o for o in out),
              not any("futuro" in o for o in out),
              [o for o in out if o.startswith("RECENT=")] == ["RECENT=b", "RECENT=a"],
              not any(o.startswith("DEFERRED=") for o in out),
              any("Active Priorities" in o for o in out if o.startswith("SECTIONS_MISSING=")),
              not any(o.startswith("PACK=") for o in out)]
        (root / "decisions").mkdir()
        (root / "decisions" / "manifest.json").write_text('{"pack_id": "p-1"}')
        (root / "scripts").mkdir()
        (root / "scripts" / "contextpack.py").write_text("#\n")
        ok.append("PACK=p-1" in report(opts))
    print(f"brief_signals selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="read-only signals for the /start brief")
    ap.add_argument("--root", default=".", help="the Polaris root of THIS repo")
    ap.add_argument("--current", default="", help="the resolved cockpit path")
    ap.add_argument("--login", default="", help="the contributor, to tell own files from foreign")
    ap.add_argument("--main-wt", default="", help="the MAIN worktree (default: the root's parent)")
    ap.add_argument("--now", default=date.today().isoformat())
    ap.add_argument("--selfcheck", action="store_true")
    opts = ap.parse_args()
    if opts.selfcheck:
        return cmd_selfcheck()
    for line in report(opts):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
