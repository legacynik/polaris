#!/usr/bin/env python3
"""The individual signals of the /start brief — one emitter each, so the door stays a door.

Every emitter returns a list of lines and returns it EMPTY when it has nothing to say. A row that
always reads zero is noise, and noise is what teaches a reader to skip the brief. Nothing here
writes and nothing fetches: a brief that fails a session is worse than a thin one.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

# ONE line model for the whole package: the donor writes state as TABLES, and a bullet-only reader
# reported `TODOS_ACTIVE=0` on the real file while quietly losing an overdue follow-up.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "end" / "scripts"))
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
    return [f"SPOOL_LEGACY={n} — old entries never committed in {spool}: "
            "bring them over by hand with git add, then delete the directory"] if n else []


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


def emit_priorities(current: Path, now: str) -> list[str]:
    """The cockpit's order, when /end has not written it for a week (2026-09-23): named, never
    presented as today's. A missing cockpit is `emit_sections`' line, not a second one here."""
    import state_priorities  # the writer's own reader: one rule for "stale", in one place
    try:
        return [line] if current.is_file() and (line := state_priorities.staleness(current, now)) else []
    except (OSError, ValueError):
        return []


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
RESOLVER = Path("scripts") / "contextpack_dashboard.py"
LEGACY_KEY = "polaris.vault-root"  # one fact, one key: read for one cycle, then gone


def _brief_lines(compiler: Path, root: Path, login: str) -> list[str]:
    """Run the host's two-stage brief and hand back its LINES, or why it did not answer."""
    args = [sys.executable, "-I", str(compiler), "brief", "--root", str(root)]
    try:
        done = subprocess.run(args + (["--login", login] if login else []),
                              capture_output=True, text=True, errors="replace",
                              timeout=PACK_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return [f"PACK: blocked — the resolver did not answer ({compiler})"]
    if done.returncode:
        cause = (done.stderr or done.stdout).strip().splitlines()
        return [f"PACK: blocked — {cause[0][:120] if cause else 'no cause given'}"
                f" ({compiler})"]
    return [line for line in done.stdout.splitlines() if line.strip()] or ["PACK: none"]


def _vault(root: Path) -> Path | None:
    """The vault this repository declares — `$POLARIS_VAULT` first, then `polaris.vault`.

    The SAME contract the vault's own `arch_doctor_sources.vault` holds: the environment wins
    over the declaration, a candidate counts only when it is a directory on this machine, and
    neither is ever invented. The declaration is LOCAL (`git config polaris.vault <path>`), so
    it never travels in a commit.

    Two shapes a human writes and a bare `Path` gets wrong, both measured as SILENCE — the one
    answer indistinguishable from a repository that declared nothing. `~/dev/vault` unexpanded
    is a directory that does not exist. And a relative `../vault` resolved against the PROCESS
    cwd answers a different thing from every directory: the declaration belongs to the
    repository, so it resolves against the repository.

    ONE key names the vault. `/end` shipped a second spelling of the same fact,
    `polaris.vault-root`, and two keys for one fact is a repository that answers one door and
    not the other. The legacy key is still READ — a machine that set it keeps working — and
    says so on stderr, once per call, naming the key that replaces it.
    """
    for key, candidate in (("", os.environ.get("POLARIS_VAULT", "")),
                           ("", git(root, "config", "--get", "polaris.vault")),
                           (LEGACY_KEY, git(root, "config", "--get", LEGACY_KEY))):
        if not candidate:
            continue
        declared = Path(candidate).expanduser()
        declared = declared if declared.is_absolute() else root / declared
        if declared.is_dir():
            if key:
                print(f"NOTE: {key} is deprecated — git config polaris.vault {declared}",
                      file=sys.stderr)
            return declared
    return None


def _resolver(root: Path, rel: Path = RESOLVER) -> Path | None:
    """Where a vault script is: the host's own first, then the declared vault, nothing else."""
    for base in (root, _vault(root)):
        if base is not None and (base / rel).is_file():
            return base / rel
    return None


def emit_pack(root: Path, login: str = "") -> list[str]:
    """D3 / polaris-os#405 — feature-detect: RUN the two-stage brief, or say nothing.

    Until #405 this printed ONE line, `PACK=CTX-<id>`, and polaris-os#326 measured what that
    is worth: the agent ignored it, so the whole resolver was invisible to the session it was
    built for. It now prints what the resolver answers — the area index with its counts, the
    area chosen or the one question to ask, and the pack of that area as one row per line.

    Two things changed for the product repositories. The compiler is looked up in the HOST
    first and then in the **vault the repository declares**, because a product repo carries
    the contract and never the harness: the host-only lookup is why `/start` showed nothing
    in repositories whose vault already answers with a full pack. And the pack is compiled
    against the CHECKOUT — `git rev-parse --show-toplevel`, falling back to `root` outside a
    checkout — not against `$ROOT`, which is the `_polaris/` contract directory: the typed
    documents live beside it, so compiling there answered zero `declared` rows.

    No `decisions/manifest.json` is required. A prose pack — the `declared` layer, freshness
    `UNKNOWN` stated row by row — is a valid pack by contract (T4, polaris-os#403), and the
    manifest is one shape of one repository. The resolver refuses when it must, out loud.

    Feature-detection is unchanged in spirit (#155): a repository with neither a resolver nor
    a declared vault that holds one must not even learn the feature exists, so an absent
    resolver is SILENCE, not a line. A resolver that exists and refuses is still loud — the
    cause is named — because a blocked emission blocks (DB-FR-05).
    """
    compiler = _resolver(root)
    if compiler is None:
        return []
    lines = _brief_lines(compiler, Path(git(root, "rev-parse", "--show-toplevel") or root), login)
    return _held_for_lane(lines)


def _held_for_lane(lines: list[str]) -> list[str]:
    """2026-09-23: /start prints no pack rows and asks no area — the pack loads on entering
    a lane. Measured: 0 of 131 rows changed a brief across three repositories. The rows are
    counted in one line; everything else the resolver says (blocked, UNKNOWN) stays."""
    rows = [ln for ln in lines if ln.startswith("layer: ")]
    kept = [ln for ln in lines if not ln.startswith(("layer: ", "QUESTION:", "AREA_CHOSEN:"))]
    return kept + ([f"PACK: {len(rows)} rows held for lane entry"] if rows else [])


def _selfcheck() -> int:
    """The pure readers and the vault lookup; the emitters run end to end in brief_signals."""
    import tempfile
    todos = ("## Active\n\n| Task | Added | Context |\n|---|---|---|\n| `a` — x | W32 | c |\n"
             "| *None* | | |\n\n## Follow-ups\n\n| Item | Review Date | Note |\n|---|---|---|\n"
             "| riprendi | 2026-09-01 | |\n")
    ok = [section(todos, "## Active") == ["| `a` — x | W32 | c |"],          # placeholder dropped
          due_on("| riprendi | 2026-09-01 | |") == "2026-09-01",
          due_on("- riprendi · Review: 2026-09-02") == "2026-09-02",
          _held_for_lane(["AREA: x", "layer: a", "layer: b", "QUESTION: which?"])
          == ["AREA: x", "PACK: 2 rows held for lane entry"]]
    saved = os.environ.pop("POLARIS_VAULT", None)
    try:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ok.append(emit_todos(root, "2026-09-03")[0].startswith("TODOS=absent"))
            (root / "vault" / "scripts").mkdir(parents=True)
            os.environ["POLARIS_VAULT"] = str(root / "vault")
            ok.append(_vault(root) == root / "vault")
            ok.append(_resolver(root) is None)                 # a vault without the script
            (root / "vault" / RESOLVER).write_text("")
            ok.append(_resolver(root) == root / "vault" / RESOLVER)
            os.environ["POLARIS_VAULT"] = str(root / "nowhere")
            ok.append(_vault(root) != root / "nowhere")          # never invented
    finally:
        os.environ.pop("POLARIS_VAULT", None)
        if saved is not None:
            os.environ["POLARIS_VAULT"] = saved
    print(f"_brief_parts selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--selfcheck"]):
        print("usage: _brief_parts.py [--selfcheck]", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selfcheck())
