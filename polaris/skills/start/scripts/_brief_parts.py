#!/usr/bin/env python3
"""The individual signals of the /start brief — one emitter each, so the door stays a door.

Every emitter returns a list of lines and returns it EMPTY when it has nothing to say. A row that
always reads zero is noise, and noise is what teaches a reader to skip the brief. Nothing here
writes, and the ONE emitter that reaches the network is bounded and degrades to silence: a brief
that fails a session is worse than a thin one.
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
from state_sections import ENTRY, OUTER, SECTIONS as REGISTRY, heading  # noqa: E402

# The sections a state file owes come from the ONE registry in `state_lines` (polaris#11):
# a reader with its own copy is a reader that disagrees with the writer the day one of them moves.
PLACEHOLDER = re.compile(r"^[\s|*]*(none|nessuno)?[\s|*]*$", re.I)
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
MAX_ROWS = 5


def section(text: str, name: str) -> list[str]:
    """The state lines under `name` — bullets or table rows — minus the empty placeholders.

    The heading is resolved by the SAME fence-aware finder every writer uses: a reader with its
    own `startswith("## ")` disagrees with the writer the moment a fence or a rule shows up.
    """
    lines = text.splitlines()
    span = body_of(lines, heading(name))
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
        if OUTER.match(line):        # `### ` is an ENTRY of this section, never its end
            inside = bool(heading("## Recent Context").match(line))
        elif inside and ENTRY.match(line):
            out.append(f"RECENT={ENTRY.match(line).group(1).strip()}")
    return out[:3]


def git(root: Path, *args: str) -> str:
    """Read-only git, and a failure is simply no signal."""
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def emit_spool(main_wt: Path) -> list[str]:
    """Signal 1 — what an upgrade left behind, counted under the git COMMON dir.

    Until v0.24.0 a run that could not commit copied the files here and asked the next session to
    drain them. Nothing writes here any more (the log commits on the branch you are on), so a
    non-empty spool is legacy: it is counted, named, and left alone for a human to `git add`.
    `rglob`, because it is NESTED — a flat `iterdir()` counted zero forever and never fired once.
    """
    common = git(main_wt, "rev-parse", "--git-common-dir")
    if not common:
        return []
    spool = Path(common if Path(common).is_absolute() else main_wt / common) / "polaris-deferred"
    n = len([p for p in spool.rglob("*") if p.is_file()]) if spool.is_dir() else 0
    return [f"SPOOL_LEGACY={n} — vecchie entry mai committate in {spool}: "
            "portale a mano con git add, poi cancella la cartella"] if n else []


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
        heads = text.splitlines()
        missing = [s for s in REGISTRY.get(path.name, ())
                   if not any(heading(s).match(ln) for ln in heads)]
        if missing:
            out.append(f"SECTIONS_MISSING={path.name}: {', '.join(missing)}")
    return out


PACK_TIMEOUT = 25


def _pack_verdict(compiler: Path, root: Path) -> str:
    """Run the host resolver and answer ONE line: the pack id, or why it did not emit."""
    try:
        done = subprocess.run([sys.executable, "-I", str(compiler), "resolve", "--root", str(root)],
                              capture_output=True, text=True, timeout=PACK_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return "BLOCKED:the resolver did not answer"
    if done.returncode:
        cause = (done.stderr or done.stdout).strip().splitlines()
        return f"BLOCKED:{cause[0][:120] if cause else 'no cause given'}"
    try:
        return json.loads(done.stdout).get("context_pack_id") or ""
    except ValueError:
        return "BLOCKED:the resolver did not answer JSON"


def emit_pack(root: Path) -> list[str]:
    """D3 — feature-detect: RUN the host resolver, or say nothing when there is no backbone.

    This used to read a `pack_id` key out of `decisions/manifest.json`. The live manifest has no
    such key — its keys are `decisions`, `manifest_hash`, `repo`, `workspace`, `live_documents`,
    `domain_source`, `legacy_sources`, `schema_version` — so the signal was dead in every real
    repository while its fixture wrote the field that made it pass. A blocked emission is now
    LOUD (DB-FR-05: a blocked emission blocks), because a silent empty line is indistinguishable
    from a repository that carries no backbone at all.
    """
    compiler = root / "scripts" / "contextpack.py"
    if not (compiler.is_file() and (root / "decisions" / "manifest.json").is_file()):
        return []
    verdict = _pack_verdict(compiler, root)
    return [f"PACK={verdict}"] if verdict else []


FETCH_TIMEOUT = 8


def _git(wt: Path, *args: str, timeout: int = 5) -> str:
    """One git call, and every failure is the same answer: nothing to say."""
    try:
        done = subprocess.run(("git", "-C", str(wt)) + args,
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def emit_divergence(main_wt: Path) -> list[str]:
    """How far this checkout is from what everyone else can see.

    Two failures, one cause, both silent until 2026-09-10. A checkout that is BEHIND answers
    "not on main" for things that are on main: three answers given that day from a checkout 159
    commits behind were wrong, and a 24-agent census repeated the same mistake. A checkout that is
    AHEAD holds work no other panel can see and any of them can delete -- worktrees share refs, so
    isolation of files does not protect a local branch. The vault-wide count that day: 122 unpushed
    commits, 94 of them session history, the oldest 14 days old.

    This is the only emitter that touches the network, and it is bounded on both ends: one fetch of
    one ref with a timeout, and every failure -- offline, no remote, not a checkout -- returns [].
    """
    if not _git(main_wt, "rev-parse", "--is-inside-work-tree"):
        return []
    upstream = _git(main_wt, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if not upstream:
        return ["NO_UPSTREAM"] if _git(main_wt, "remote") else []
    remote, _, ref = upstream.partition("/")
    _git(main_wt, "fetch", "--quiet", remote, ref, timeout=FETCH_TIMEOUT)
    counts = _git(main_wt, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
    behind, _, ahead = counts.partition("\t")
    out = []
    if ahead.isdigit() and int(ahead):
        out.append(f"AHEAD={ahead}")
    if behind.isdigit() and int(behind):
        out.append(f"BEHIND={behind}")
    return out
