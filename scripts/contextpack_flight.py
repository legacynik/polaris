#!/usr/bin/env python3
"""L2-T3 (#410) — the flight layer of the ContextPack.

The sealed layer answers one question: what does HEAD prove? That is the right question
for an authority and the wrong one for everything a repository is currently DOING. The
four repositories carry 484 unmerged branches and 32 open PRs (measured 2026-09-13,
`DEC-polaris-contextpack-flight-layer-001`), and a HEAD-only pack is blind to every one
of them — plus the issue opened this morning, the handoff another panel wrote yesterday,
and the file nobody has committed. Three of the fourteen incidents of #63 are that
blindness: INC-01, INC-03, INC-11.

So this layer reads git and the tracker at a declared moment and emits what it finds
under `layer: "flight"`, every row `landed: false` and `freshness: "UNKNOWN"`. That pair
is the safety property: a flight row is news, never authority, and a reader who promotes
one to truth has ignored two fields that say not to.

**Five sources, one per plan section 5** — open issues and PRs carrying the area's label,
branches nobody merged, worktrees other than this one, another login's session handoffs
inside the 14-day window, and every file the worktree changed and nobody committed. The
window is a contract: an older handoff is not stale news, it is history, and history
enters only on request (plan section 2). It is measured in WHOLE days, so both sides of
the boundary are deterministic instead of racing the clock by microseconds.

**Every row is dated, and the list is newest-first.** Each kind carries a real date in
`ts` — a branch its last commit, a worktree the commit its HEAD sits on, a file its
mtime, an issue or PR its `updatedAt` — because "the budget cuts flight from the oldest"
(plan section 8) is a claim about an order, and an order nobody dated is decoration. The
joined list is sorted newest-first, which is also the contract with the consumer: T5's
`fit` trims a pack by popping the tail, so the tail must be the oldest row.

**The seal does not move.** `attach` runs AFTER `contextpack_seal.seal`, so `pack_seal`
keeps meaning "this is what the commit carries" and an uncommitted edit cannot change it
— the property `test_contextpack_row_contract.py` holds down, and the one T7 needs to
re-inject a pack at a fixed HEAD. The rows travel beside the seal, never inside it, and
so does everything else this layer adds: the unknown row for a tracker it could not read
answers a question about a remote, which is not something a commit carries either.

**The order is fixed by the coordinator, and the plan did not settle it.** Three steps,
and T5 (#419) closes around this layer:

    return receipt.close(root, flight_layer.attach(root, sealer.seal(root, pack), domains))

1. `sealer.seal` computes `pack_seal` over the SEALED rows only, and freezes it.
2. `attach` adds the flight rows outside that seal.
3. `receipt.close` fits the WHOLE pack — sealed, unknown and flight — with
   `CUT_ORDER = (flight, declared)`, never sealed or unknown, and writes the receipt.
   It never recomputes `pack_seal`.

Both other orders were tried and break something: attaching after `close` leaves the
Decision's first cut level with nothing to cut, and attaching before `seal` puts the
worktree inside the seal. This one breaks neither.

**Absence is a row, never silence** (L2-T2's invariant, extended to the tracker). No
remote means no tracker to ask; a `gh` that does not answer is not an empty tracker. Each
is its own `layer: unknown` row, so "no open issues" and "nobody could look" are never
the same sentence. The one absence that gets NO row is a pack asked for no area: the
tracker is a per-area source, so a request naming none never expected it — and T2's
landed contract is that a healthy sealed pack carries no unknown layer at all
(`test_contextpack_unknown.py::TheSealedPathIsUntouched`). The key is created only when
there is something to put in it.

**An area is a label slug, not a domain id.** The tracker is asked for `area:<slug>`
(plan section 2); a `polaris.*` domain id is the sealed layer's vocabulary and names no
label, so it is never queried — which also keeps the resolver off the network for every
call that passes domains rather than areas, the vault's own gates included.

**Nothing here is unbounded.** A file over FILE_MAX is named without a hash rather than
read whole, a symlink is hashed by where it points and never by what is there, and every
kind — the tracker included — is capped at LIMIT with the remainder handed to `cut`. A
pack that budgets context may not be sized by a fifty-megabyte artefact in a worktree or
by a tracker willing to answer with ten thousand issues.

`gh` is invoked, never imported: it is the tracker client we have and it carries its own
auth; shelling out with a timeout degrades to an UNKNOWN row when it is absent. Tests
replay it from `scripts/test/fixtures/flight/bin/gh`, so no gate reaches GitHub.

It lives outside `contextpack.py` because that file is grandfathered above the 200-line
ceiling and may only shrink; it ships with the resolver
(`_standard/sync_scripts.py`).
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

import check_context_backbone as cbb
import contextpack_flight_tracker as tracker

HANDOFF_DAYS = 14
LIMIT = 8               # per kind: the area budget cuts flight from the oldest (section 8)
FILE_MAX = 1_048_576    # bytes a flight row will read to hash — a pack is not a reader
SESSIONS = "team/*/sessions/*.md"
RECEIPTS = "state/session/"
REGISTER = "decisions/"
TIMEOUT = 30


def _git(root: Path, *args: str) -> str:
    """git, read-only, fail-open: what it printed, or "" when it could not answer.

    `--no-optional-locks` because this runs in trees five panels share: `status` would
    otherwise take `index.lock` to refresh the index, and a pack must never block — or
    fail — because somebody else is fetching in the same repository."""
    try:
        done = subprocess.run(["git", "--no-optional-locks", "-C", str(root), *args],
                              capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def _unknown(kind: str, source_id: str, reason: str) -> dict[str, Any]:
    """A source the layer was asked about and could not read — same shape as L2-T2."""
    return {"source_id": source_id, "layer": "unknown", "kind": kind, "path": None,
            "source_hash": "", "freshness": "UNKNOWN", "reason": reason}


def _flight(kind: str, source_id: str, reason: str) -> dict[str, Any]:
    """A row derived from git or the tracker: in the air, and saying so twice.

    `ts` is filled by whoever knows the date — see `rows` for why every kind has one."""
    return dict(_unknown(kind, source_id, reason), layer="flight", landed=False, ts="")


def _when(row: dict[str, Any]) -> datetime:
    """The row's instant, always tz-aware. Parsed, never compared as text: `+03:00` and
    `Z` sort wrong as strings, and a row with no readable date goes last.

    A tracker may answer `2026-01-05` — a date with no time and no offset — which
    `fromisoformat` accepts and returns NAIVE. Sorting that beside an aware row raises
    `TypeError: can't compare offset-naive and offset-aware datetimes`, and the layer
    whose whole contract is to degrade to a row would die with a traceback. A naive
    stamp is read as UTC: an assumption, and the only one that keeps the sort total."""
    try:
        parsed = datetime.fromisoformat(str(row.get("ts") or "").replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _newest(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(found, key=_when, reverse=True)


def _hashed(row: dict[str, Any], path: Path) -> dict[str, Any]:
    """The row carrying the sha256 of the bytes ON DISK — not of HEAD, which for a flight
    row would be a digest of something else, or of nothing at all."""
    try:
        row["source_hash"] = sha256(path.read_bytes()).hexdigest()
    except OSError:
        pass
    return row


def _mtime(path: Path) -> str:
    """When the worktree last touched this file. The disk IS the source for a flight row
    — HEAD has nothing to say about a file nobody committed."""
    try:
        stamp = path.lstat().st_mtime if path.is_symlink() else path.stat().st_mtime
    except OSError:
        return ""
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat()


def _size(path: Path) -> int:
    """Bytes on disk, or 0 when the path cannot be stat-ed (a broken link, a race)."""
    try:
        return path.lstat().st_size if path.is_symlink() else path.stat().st_size
    except OSError:
        return 0


def _committed_at(root: Path, sha: str) -> str:
    """The date of the commit a worktree sits on: its age is that commit's age."""
    return _git(root, "show", "-s", "--format=%cI", sha).strip() if sha else ""


def _top(root: Path) -> Path:
    """The worktree's root, which is what `git status` reports paths against."""
    out = _git(root, "rev-parse", "--show-toplevel").strip()
    return Path(out) if out else root


def _under(root: Path, top: Path, name: str) -> str:
    """A path `git status` printed, re-addressed relative to `root`, or "" if outside it.

    LEXICAL, and that is the whole point. `resolve()` here followed the link: an
    untracked `alias.md -> tracked.md` came back as a row named `tracked.md` claiming a
    committed, clean file was "committed nowhere", and the link itself disappeared; a link
    pointing out of the tree resolved outside the root and was dropped in silence. Only
    the two DIRECTORIES are resolved, because `git rev-parse --show-toplevel` answers in
    real paths while `root` may arrive through a symlinked parent (`/tmp` on macOS), and
    the path component is then rewritten by parts, never by the filesystem."""
    try:
        base = root.resolve().relative_to(top.resolve()).parts
    except (ValueError, OSError):
        return ""
    parts = PurePosixPath(name).parts
    return (PurePosixPath(*parts[len(base):]).as_posix()
            if parts[:len(base)] == base and len(parts) > len(base) else "")


def _owned_elsewhere(rel: str) -> bool:
    """True for a path another layer already answers for: the three live authorities, the
    decision register, and the pack's own receipts.

    Plan section 242 enforced at the source — one document must never appear in two
    layers. For `decisions/` it is also the critic's probe of #348: a record nobody
    committed must not reach the pack AT ALL (`test_emit_authority_seal.py`), because
    panels share trees and a draft that arrives is read as a decision, flight tag or not.
    Its unlanded twin is somebody else's id, which is T9's reservation, not a row.

    `state/session/` is T5's receipts, and this one is a loop rather than an overlap: a
    resolve writes a receipt, and the next resolve reported it as work in flight — two
    packs for one still HEAD, which is what `test_contextpack_receipt.py` measures. This
    vault gitignores that folder, so the loop only shows in a repository that does not;
    the pack must not read its own bookkeeping as news either way."""
    return rel in cbb.LIVE_DOCS or rel.startswith((REGISTER, RECEIPTS))


def _inside(root: Path, link: Path, target: str) -> bool:
    """Whether a link's target stays under the root, decided lexically: following it is
    what let a target outside the tree be read as a path inside it."""
    joined = os.path.normpath(os.path.join(os.path.dirname(str(link)), target))
    return os.path.commonpath([str(root.resolve()), joined]) == str(root.resolve())


def _link_row(root: Path, rel: str, row: dict[str, Any]) -> dict[str, Any]:
    """A symlink is itself: hashed by WHERE IT POINTS, never by what is there.

    Hashing the target would make the row about a file the link merely names — the
    defect this replaces — and reading a target outside the root would read past the
    repository entirely, so that case carries no hash at all."""
    target = os.readlink(root / rel)
    if not _inside(root, root / rel, target):
        return dict(row, reason=f"symlink outside root: -> {target}", source_hash="")
    return dict(row, reason=f"symlink: -> {target}",
                source_hash=sha256(target.encode()).hexdigest())


def _file_row(root: Path, rel: str, status: str) -> dict[str, Any]:
    """One uncommitted path, answered for what it IS on disk.

    A regular file over FILE_MAX is named without a hash: hashing it means reading it
    whole, and a fifty-megabyte artefact in a worktree would be loaded into the process
    that is supposed to be budgeting context."""
    why = f"{status or '??'}: changed in the worktree, committed nowhere"
    row = dict(_flight("worktree-file", rel, why), path=rel, ts=_mtime(root / rel))
    if (root / rel).is_symlink():
        return _link_row(root, rel, row)
    size = _size(root / rel)
    if size > FILE_MAX:
        return dict(row, reason=f"too_large: {size} bytes, not read", source_hash="")
    return _hashed(row, root / rel)


def _dirty(root: Path) -> list[dict[str, Any]]:
    """Every file the worktree changed and nobody committed (plan section 5).

    `-uall` because git collapses an untracked directory into one entry and the point is
    the FILE: INC-11's workaround lived in a folder no commit ever saw. Authority paths
    are skipped — see `_owned_elsewhere`."""
    top, rows = _top(root), []
    for line in _git(root, "status", "--porcelain", "-uall", "--", ".").splitlines():
        rel = _under(root, top, line[3:].strip().split(" -> ")[-1].strip('"'))
        if rel and not _owned_elsewhere(rel):
            rows.append(_file_row(root, rel, line[:2].strip()))
    return rows


def _cockpit(root: Path, seen: set[str]) -> list[dict[str, Any]]:
    """The cockpit, which `git status` will never report: it is gitignored in this vault
    (`state/current.md`, and `team/<login>/current.md` after the migration).

    Ignored files are excluded from `--porcelain -uall` by design — and rightly, or a
    pack would carry `.venv` — but the cockpit is the one ignored file the plan asks for
    by name (section 3, "file modificati non committati nel worktree corrente"). So it is
    read from disk, said to be read from disk, and never twice when git did report it."""
    login = _login(root)
    names = ["state/current.md"] + ([f"team/{login}/current.md"] if login else [])
    rows = []
    for rel in names:
        why = "cockpit: read from disk, ignored by git, committed nowhere"
        if rel not in seen and (root / rel).is_file():
            rows.append(_hashed(dict(_flight("worktree-file", rel, why), path=rel,
                                     ts=_mtime(root / rel)), root / rel))
    return rows


def _branches(root: Path) -> list[dict[str, Any]]:
    """Branches whose tip HEAD cannot reach: work that exists and has not landed."""
    fmt = "%(refname:short)%09%(committerdate:iso-strict)%09%(objectname:short)"
    out = _git(root, "for-each-ref", "--no-merged", "HEAD", "--sort=-committerdate",
               f"--format={fmt}", "refs/heads", "refs/remotes")
    rows = []
    for line in out.splitlines():
        name, when, sha = (line.split("\t") + ["", ""])[:3]
        rows.append(dict(_flight("branch", f"branch:{name}",
                                 f"unmerged branch, last commit {sha} on {when}"), ts=when))
    return rows


def _worktrees(root: Path) -> list[dict[str, Any]]:
    """The other worktrees of this repository — another panel's tree is not this one."""
    here, rows = _top(root).resolve(), []
    for block in _git(root, "worktree", "list", "--porcelain").split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        tree = Path(fields["worktree"]) if "worktree" in fields else here
        head = fields.get("HEAD", "")
        if tree.resolve() != here:
            rows.append(dict(_flight("worktree", f"worktree:{tree.name}",
                                     f"checked out on {fields.get('branch', 'a detached HEAD')} "
                                     f"at {head[:12]}"), ts=_committed_at(root, head)))
    return rows


def _ahead(when: datetime) -> bool:
    """A commit date in the future: a clock, not a handoff."""
    return when > datetime.now(timezone.utc)


def _too_old(when: datetime) -> bool:
    """Outside the window, measured in WHOLE days.

    "Entro 14 giorni" is a window a person reads in days, and a fractional comparison
    makes its edge a race: a handoff committed exactly fourteen days ago loses to the
    microseconds between its own second and the moment the pack is built. Whole days
    make both sides of the boundary deterministic — fourteen is in, fifteen is out."""
    return (datetime.now(timezone.utc) - when).days > HANDOFF_DAYS


def _parsed(stamp: str) -> datetime | None:
    """A commit date git printed, or None — a date this cannot read is not a crash."""
    try:
        return datetime.fromisoformat(stamp)
    except ValueError:
        return None


def _session_commits(root: Path) -> list[tuple[datetime | None, str]]:
    """(commit date or None, path) for every session log committed on ANY ref, newest
    first. `--all` on purpose: INC-01's handoff sat on a branch nobody had merged.

    The date is kept even when it does not parse. Dropping the pair there is how a
    handoff with a nonsense stamp — git will commit any integer — left no trace at all."""
    out = _git(root, "log", "--all", f"--since={HANDOFF_DAYS + 16}.days.ago",
               "--format=%x01%cI", "--name-only", "--", SESSIONS)
    when, seen, rows = None, set(), []
    for line in (raw.strip() for raw in out.splitlines()):
        if line.startswith("\x01"):
            when = _parsed(line[1:])
        elif line and line not in seen:
            seen.add(line)
            rows.append((when, line))
    return rows


def _handoff_row(root: Path, path: str, when: datetime | None) -> dict[str, Any]:
    """One handoff of another login, dated when its commit can be dated."""
    login = (path.split("/") + ["", ""])[1]
    why = (f"handoff by {login}, committed {when:%Y-%m-%d}, not read by this session"
           if when else f"unreadable date: handoff by {login}, when is not knowable")
    row = dict(_flight("handoff", path, why), path=path,
               ts=when.isoformat() if when else "")
    return _hashed(row, root / path)


def _login(root: Path) -> str:
    return _git(root, "config", "--get", "polaris.login").strip()


def _handoffs(root: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """(another login's handoffs inside the window, the ones dropped, what was unreadable).

    The window has TWO sides. A handoff older than it is history, which enters only on
    request (plan section 2) and needs no row. A handoff from the FUTURE is not news,
    it is a clock — and dropping it in silence is how a skewed commit date quietly
    rewrites what a session is told, so that drop is recorded.

    Without `polaris.login` there is no "altrui": `mine` was the empty string, so every
    handoff was somebody else's — the session's own included, handed back to it as news.
    So no handoff is guessed at, and the agent is TOLD, in the layer it will actually
    read: a `flight` row of kind `handoff`.

    Two wrong homes were tried first. An `unknown` row breaks the landed contract that a
    healthy sealed pack carries no unknown layer — a fresh checkout has no local git
    config, so it landed in the vault's own pack and CI went red
    (`test_contextpack_unknown.py::TheSealedPathIsUntouched`). A `cut` entry is worse in
    the other direction: `cut` is what the pack did NOT hand over, and T5's `close` lifts
    it out into the receipt, so a repository without the login would give its agent zero
    handoff rows and not one word about why — which is the exact shape of INC-01, the
    incident this layer exists for. `flight` is neither: it is not `unknown`, so the
    sealed contract holds, and it is in the pack the agent reads."""
    mine, rows, cut = _login(root), [], []
    found = _session_commits(root)
    if not mine:
        return ([dict(_flight("handoff", SESSIONS, "login unknown (git config "
                              "polaris.login): whose handoffs are somebody else's "
                              "cannot be decided, so none of the "
                              f"{len(found)} were read"), path=None)] if found else []), [], []
    for when, path in found:
        if (path.split("/") + ["", ""])[1] == mine or (when and _too_old(when)):
            continue
        row = _handoff_row(root, path, when)
        (cut if when and _ahead(when) else rows).append(
            dict(row, reason="future") if when and _ahead(when) else row)
    return rows, cut, []


def _why(found: dict) -> str:
    """The tracker row's sentence, naming the remote that answered: with three remotes
    configured, "an open issue" is only true of one of them."""
    item, kind = found["item"], found["kind"]
    branch = item.get("headRefName")
    return (f"open {kind} on area {found['area']} via {found['remote']}: "
            f"{str(item.get('title', ''))[:80]}" + (f" [{branch}]" if branch else "")
            + f" (updated {str(item.get('updatedAt', ''))[:10]})")


def _tracker(root: Path, areas: list[str]) -> tuple[list[dict], list[dict]]:
    """(flight rows from the tracker, unknown rows for what it could not read).

    `contextpack_flight_tracker` owns the network and hands back items; the row shape
    stays here, so the vocabulary of a flight row has exactly one definition."""
    found, reasons = tracker.answer(root, areas)
    rows = [dict(_flight(one["kind"], f"{one['kind']}:{one['repo']}#{one['item'].get('number')}",
                         _why(one)), ts=str(one["item"].get("updatedAt") or ""))
            for one in found]
    return rows, [_unknown("tracker", tracker.TRACKER, why) for why in reasons]


def _capped(found: list[dict], kind: str) -> tuple[list[dict], list[dict]]:
    """(the newest LIMIT rows of one kind, the rows the cut removed).

    The budget cuts flight before sealed and from the oldest (plan section 8), so the
    kind is ordered newest-first and the tail is what goes. A SILENT cut is the silence
    this layer exists to end — eight branches reading as "these are the branches" when
    there are two hundred and twenty-three — so the cut hands back the ROWS, each still
    addressable and dated, for T5's receipt to list. A count cannot be audited.

    The cut is NOT an unknown row. `unknown` means an authority the pack could not read,
    and a healthy sealed pack must carry none of them
    (`test_contextpack_unknown.py::TheSealedPathIsUntouched`); a budget event belongs to
    the BUDGET line of plan section 3."""
    ordered = _newest(found)
    return ordered[:LIMIT], [dict(row, reason=f"per-kind cap {LIMIT}")
                             for row in ordered[LIMIT:]]


def _by_kind(found: list[dict]) -> list[tuple[str, list[dict]]]:
    """The tracker's rows split into the kinds the cap counts, in a fixed order."""
    return [(kind, [row for row in found if row["kind"] == kind])
            for kind in ("issue", "pr")]


def rows(root: Path, areas: list[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """(flight rows newest-first, unreadable sources, rows built and not handed over).

    Every kind is dated from its own real source — a branch its last commit, a worktree
    the commit its HEAD sits on, a file its mtime, an issue or PR its `updatedAt` — and
    the joined list is ordered newest-first. That order is a contract with the consumer:
    T5's `fit` trims a pack by popping the tail, so the tail has to be the oldest row.

    EVERY kind is capped, the tracker included. It used to be exempt on the grounds that
    cutting a joined list would drop a whole area rather than the oldest rows — true when
    nothing was dated, false now, and meanwhile a tracker willing to answer with ten
    thousand issues decided the size of the pack. `gh` is asked for at most FETCH_MAX per
    area and never believed past it; the cap then keeps the newest LIMIT per kind.

    `cut` is every row this layer built and did not hand over, each with the reason it
    was dropped — the per-kind cap, or a commit date from the future. T5's receipt lists
    them, which is why they are rows and not a count: a count cannot be audited."""
    tracker, unknown = _tracker(root, areas)
    handoffs, cuts, blind = _handoffs(root)
    dirty, flight = _dirty(root), []
    unknown += blind
    for kind, found in (_by_kind(tracker) + [("branch", _branches(root)),
                                             ("worktree", _worktrees(root)),
                                             ("handoff", handoffs),
                                             ("worktree-file", dirty + _cockpit(
                                                 root, {r["source_id"] for r in dirty}))]):
        kept, cut = _capped(found, kind)
        flight, cuts = flight + kept, cuts + cut
    return _newest(flight), unknown, cuts


def attach(root: Path, pack: dict[str, Any], areas: list[str]) -> dict[str, Any]:
    """The flight rows, added AFTER the seal: `pack_seal` means "what the commit carries"
    and a changing worktree must not move it (T7, and the row-contract tests)."""
    flight, unknown, cuts = rows(root.resolve(), areas)
    pack["flight"] = flight
    pack["flight_budget"] = {"limit_per_kind": LIMIT, "cut": cuts}
    if unknown or "unknown" in pack:
        pack["unknown"] = list(pack.get("unknown") or []) + unknown
    return pack
