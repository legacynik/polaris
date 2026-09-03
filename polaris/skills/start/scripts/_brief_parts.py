#!/usr/bin/env python3
"""The individual signals of the /start brief — one emitter each, so the door stays a door.

Every emitter returns a list of lines and returns it EMPTY when it has nothing to say. A row that
always reads zero is noise, and noise is what teaches a reader to skip the brief. Nothing here
writes and nothing fetches: a brief that fails a session is worse than a thin one.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# ONE line model for the whole package: the donor writes state as TABLES, and a bullet-only reader
# reported `TODOS_ACTIVE=0` on the real file while quietly losing an overdue follow-up.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "update" / "scripts"))
from state_lines import kinds, section as body_of, table_row  # noqa: E402

# The sections a state file owes. `state_contract.py` in a repo that has one is asked first;
# this is the answer for the host repos that ship only the package.
REGISTRY = {"current.md": ("## Active Priorities", "## Open", "## Recent Context"),
            "todos.md": ("## Active", "## Completed", "## Follow-ups")}
PLACEHOLDER = re.compile(r"^[\s|*]*(none|nessuno)?[\s|*]*$", re.I)
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
ENTRY = re.compile(r"^###\s+(.*)$")
MAX_ROWS = 5


def section(text: str, name: str) -> list[str]:
    """The state lines under `name` — bullets or table rows — minus the empty placeholders.

    The heading is resolved by the SAME fence-aware finder every writer uses: a reader with its
    own `startswith("## ")` disagrees with the writer the moment a fence or a rule shows up.
    """
    lines = text.splitlines()
    span = body_of(lines, re.compile(rf"^#{{1,6}}\s+{re.escape(name.lstrip('# '))}\s*$", re.I))
    tags = kinds(lines)
    return [lines[i].strip() for i in range(*(span or (0, 0)))
            if tags[i] == "thread" and not PLACEHOLDER.match(lines[i])]


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


def emit_spool(main_wt: Path) -> list[str]:
    """#243 signal 1 — counted under the git COMMON dir, where `session_commit.sh` really puts it.

    `rglob`, because the spool is NESTED (it mirrors the repo path under the branch it deferred
    from). A flat `iterdir()` counted zero forever and this signal never fired once.
    """
    common = git(main_wt, "rev-parse", "--git-common-dir")
    if not common:
        return []
    spool = Path(common if Path(common).is_absolute() else main_wt / common) / "polaris-deferred"
    n = len([p for p in spool.rglob("*") if p.is_file()]) if spool.is_dir() else 0
    return [f"DEFERRED={n} — session-log entries spooled, not committed"] if n else []


def emit_drift(main_wt: Path, login: str) -> list[str]:
    """#243 signal 2 — the MAIN worktree parked off its default, with somebody else's files."""
    out = []
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
