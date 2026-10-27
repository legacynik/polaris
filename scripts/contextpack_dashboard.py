#!/usr/bin/env python3
"""L2-T6 (#405) — the two-stage `/start`: the area index, the choice, and the pack as LINES.

`/start` used to hand the agent one line — `PACK=CTX-<id>` — and #326 measured what that is
worth: the agent ignored it, and the founder kept being the index of his own repository out
loud. This module is the other half of the plan's section 3.

**Time 0, `dashboard`.** Deterministic, always the same shape, and small enough that a
compaction does not eat it: one row per AREA with the three counts the founder asked for on
2026-09-17 (question 1, answered yes) — open issues, open PRs, the newest accepted Decision
— then the cockpit's priority 1. `token_count.py` is the ruler and 1.500 tokens the ceiling.

**One `gh` call per KIND, not per area.** Measured on the vault: 0.75 s a call, so the
per-area query the flight tracker uses would cost ~12 s at every `/start` for eight areas.
One bulk answer per kind is fetched and the labels are counted locally — that IS the cache —
behind a timeout, and `gh` absent, refusing or slow reads `UNKNOWN`. Never a zero: a zero
means *this area has no open work*, and inventing one sends the session to the quiet area.
The labels are read as `domain:<slug>`, `area:<slug>` and the bare slug, because the vault's
own issues carry `domain:` while section 2 of the plan says `area:`.

**Time 0 and a half, `choose_area`.** The three signals of the plan, first answer wins: the
area named outright, the branch, this contributor's open issues, the cockpit's priority 1.
Two areas answering is NO answer — it returns `None` and the caller asks ONE question with
the index already in front of the reader. Never a guess.

**Time 1, `print_rows`.** The resolved pack, one row per line, each naming its layer, its
source id, its path and its freshness. The agent can act on a row; it could not act on an id.

**The receipt.** `brief` calls `contextpack_receipt.configure(sid, area, budget)` before it
resolves, which closes the debt PR #419 left to this task: `configure` was public and
nobody called it, so the real `/start` path wrote no pack receipt at all. The session id is
the one named, else the newest `state/session/*/start.json` — read as a FILE, because
`session_continuity.py` belongs to another task.

The `brief` subcommand lives here and not in `contextpack.py`, which is grandfathered above
the 200-line ceiling and may only shrink. It ships with the resolver (`sync_scripts.py`)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as cbb  # noqa: E402
import contextpack  # noqa: E402
import contextpack_flight_tracker as tracker  # noqa: E402
import contextpack_receipt as receipt  # noqa: E402
import contextpack_seal as sealer  # noqa: E402

AREA_ROW = "AREA: {slug}  issues: {issues}  prs: {prs}  last_decision: {dec}"
PACK_ROW = "layer: {layer}  source_id: {sid}  path: {path}  freshness: {fresh}"
NO_MAP = "UNKNOWN: no area map"
COCKPIT = Path("state") / "current.md"
LABEL_PREFIXES = ("domain:", "area:", "")
PACK_KEYS = ("decisions", "documents", "declared", "flight", "unknown", "dropped")
GH_LIMIT = 200
TIMEOUT = 20             # git only: a local read that hangs is a broken repository
GH_BUDGET = 6.0          # seconds for EVERY `gh` call of one brief, together
SESSION_MAX_AGE = 24 * 3600
ITEM = re.compile(r"^\s*(?:\d+\.|[-*])\s+(.*\S)")
# `fix/1234-…` (plan section 3, signal 2): digits as their own token, so `l2-t6` is not an
# issue number and the lookup is not spent on a branch that names none.
ISSUE_IN_BRANCH = re.compile(r"(?:^|[/_-])(\d{1,6})(?:[/_-]|$)")
UNLABELLED = {"issue": ("ISSUES_UNLABELLED", "issue(s)"), "pr": ("PRS_UNLABELLED", "PR(s)")}
_CACHE: dict[tuple, Any] = {}
_DEADLINE: list[float] = []


def areas(root: Path) -> dict[str, list[str]]:
    """The vocabulary `--area` accepts: this repository's own issue labels, each mapped to
    the domains `DOMAIN.md` declares. Empty when there is no map to read — which is the
    normal case outside the vault, and a line rather than a refusal."""
    try:
        found = contextpack._repo_domain_map(root)
    except (cbb.ContractError, OSError, ValueError, KeyError):
        return {}
    return {slug: domains for slug, domains in found.items() if domains}


def _left() -> float:
    """Seconds left in the ONE network budget a brief gets, armed on first use.

    Three `gh` calls at a 20 s per-call timeout is 40 s, against the 25 s the package allows
    the whole script: a slow tracker cancelled BOTH stages and the brief read `PACK: blocked`.
    The budget is never re-armed, so the worst case is `GH_BUDGET` for the brief — not per
    call — and a tracker that is merely slow costs the counts, never the pack.

    **It bounds the NETWORK, not the brief.** Measured on this vault with a `gh` that sleeps
    3 s: `index` takes 6.0 s for its two calls and the third call returns in 0.0 s with the
    budget spent, which is the shared deadline doing its job; `brief --area memoria` takes
    11.5 s end to end, because the resolve itself is 4.9 s of local work — reading HEAD and
    hashing sources — and no deadline here covers that. 11.5 s against the 25 s the package
    allows the whole script, so it fits; a reader who takes `GH_BUDGET` for the ceiling of
    the brief would be reading it wrong."""
    if not _DEADLINE:
        _DEADLINE.append(time.monotonic() + GH_BUDGET)
    return max(0.0, _DEADLINE[0] - time.monotonic())


def _ask(root: Path, args: tuple[str, ...]) -> Any:
    """The ONE door to `gh`: memoised, inside the shared budget, `None` when nobody looked."""
    key = (root, args)
    if key not in _CACHE:
        _CACHE[key] = None
        left = _left()
        if left > 0:
            try:
                done = subprocess.run(list(args), cwd=root, capture_output=True,
                                      text=True, timeout=left)
                _CACHE[key] = json.loads(done.stdout) if done.returncode == 0 else None
            except (OSError, ValueError, subprocess.SubprocessError):
                _CACHE[key] = None
    return _CACHE[key]


def _gh(root: Path, kind: str, assignee: str = "") -> list[dict] | None:
    """One bulk answer per kind — or `None` when nobody could look. See the docstring."""
    args = ("gh", kind, "list", "--state", "open", "--limit", str(GH_LIMIT),
            "--json", "number,labels") + (("--assignee", assignee) if assignee else ())
    listed = _ask(root, args)
    return listed if isinstance(listed, list) else None


def _gh_issue(root: Path, number: str) -> dict | None:
    """The labels of ONE issue: `gh issue view` answers an object, not a list."""
    found = _ask(root, ("gh", "issue", "view", number, "--json", "labels"))
    return found if isinstance(found, dict) else None


def _labelled(item: dict, slug: str) -> bool:
    """Whether a tracker item carries THIS area's label, in any prefix in use here.

    `P1` and `task` are labels and are not AREAS: the question is whether a known slug is on
    the item, never whether it has labels at all."""
    names = {lab.get("name", "") for lab in item.get("labels") or []}
    return bool(names & {prefix + slug for prefix in LABEL_PREFIXES})


def _counted(listed: list[dict] | None, slug: str) -> str:
    """How many listed items carry this area's label. `UNKNOWN`, never an invented zero."""
    if listed is None:
        return "UNKNOWN"
    return str(sum(1 for item in listed if _labelled(item, slug)))


def _register(root: Path) -> list[dict] | None:
    """The decision records, read once per root per process; None when there is no register
    or a record cannot be read."""
    key = (root, "register")
    if key not in _CACHE:
        try:
            if not (root / "decisions").is_dir():
                raise OSError("no decisions/")
            _CACHE[key] = [cbb._frontmatter(path) for path in sorted((root / "decisions").glob("DEC-*.md"))]
        except (cbb.ContractError, OSError, ValueError, TypeError):
            _CACHE[key] = None
    return _CACHE[key]


def _last_decision(root: Path, domains: list[str]) -> str:
    """The newest ACCEPTED Decision governing this area — `none` when it has none, and
    `UNKNOWN` when the register could not be read, which is not the same answer."""
    found = _register(root)
    if found is None:
        return "UNKNOWN"
    dated = [(str(rec.get("decided_at", "")), rec.get("decision_id", ""))
             for rec in found if rec.get("status") == "accepted"
             and set(rec.get("governs", {}).get("domains") or []) & set(domains)]
    return f"{max(dated)[1]} ({max(dated)[0] or 'undated'})" if dated else "none"


def _unlabelled(listed: list[dict] | None, kind: str, slugs: list[str]) -> list[str]:
    """A per-area zero is honest only while no open item sits outside the area vocabulary.

    The first version asked whether an item had labels AT ALL, which is true of one open PR
    here and false of 19 of the 57 open issues — they carry `P1` and `task` and no area. Four
    areas read `issues: 0` with nothing saying that the reader, not the repository, was quiet."""
    lost = [item for item in listed or []
            if not any(_labelled(item, slug) for slug in slugs)]
    word, many = UNLABELLED[kind]
    return [f"{word}: {len(lost)} open {many} carry no area label"] if lost else []


def _no_map(root: Path) -> str:
    """WHICH of the two absences this is. A reason is a claim, and the adopting repository of
    #344 has a `DOMAIN.md`: leading with «absent» there names the wrong cause."""
    if not (root / "DOMAIN.md").is_file():
        return f"{NO_MAP} — DOMAIN.md absent"
    return f"{NO_MAP} — DOMAIN.md declares no domain an issue label of this repo maps to"


def index(root: Path) -> list[str]:
    """One row per area with its three counts, or the one line an absent map owes."""
    found = areas(root)
    if not found:
        return [_no_map(root)]
    listed = {kind: _gh(root, kind) for kind in ("issue", "pr")}
    slugs = sorted(found)
    return [AREA_ROW.format(slug=slug, issues=_counted(listed["issue"], slug),
                            prs=_counted(listed["pr"], slug),
                            dec=_last_decision(root, found[slug]))
            for slug in slugs] + [line for kind in ("issue", "pr")
                                  for line in _unlabelled(listed[kind], kind, slugs)]


def _first_priority(lines: list[str]) -> str:
    """The first list item under `## Active Priorities`, whatever bullet wrote it.

    Matching `1.` literally made a cockpit whose first active priority is written `2.` or
    `10.` invisible, and the third signal went silent on it."""
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line.lower().startswith("## active priorities")
        elif inside and ITEM.match(line):
            return ITEM.match(line).group(1).strip()
    return ""


def _cockpit_path(root: Path) -> Path:
    """The ONE cockpit of this repository, at the root or one level into the contract.

    A product repository keeps the contract in `_polaris/` and the typed documents beside it,
    so the pack is compiled at the ROOT while the cockpit sits inside `_polaris/`. Reading
    only `state/current.md` reported `no cockpit` on a repository that has one. The root wins
    wherever both exist — the vault is a root that IS its own contract directory."""
    nested = root / "_polaris" / COCKPIT
    return nested if not (root / COCKPIT).is_file() and nested.is_file() else root / COCKPIT


def _priority(root: Path) -> str:
    path = _cockpit_path(root)
    if not path.is_file():
        return ""
    return _first_priority(path.read_text(encoding="utf-8", errors="replace").splitlines())


def _cockpit(root: Path) -> list[str]:
    """The cockpit is gitignored and lives outside the commit: absent is a LINE, not a fault."""
    if not _cockpit_path(root).is_file():
        return [f"UNKNOWN: no cockpit — {COCKPIT.as_posix()} absent, priority 1 unreadable"]
    found = _priority(root)
    return [f"PRIORITY1: {found}"] if found else ["UNKNOWN: no priority 1 in the cockpit"]


def dashboard(root: Path) -> list[str]:
    """Time 0 — where the open work is, per area, under 1.500 tokens."""
    return index(root) + _cockpit(root)


def _named_in(text: str, known: list[str]) -> str:
    """The area a branch or a priority names — and NOTHING when it names two.

    `next()` over the table order answered `memoria` for `feat/gates-memoria` AND for
    `feat/memoria-gates`: a silent choice, in the one function whose docstring says never
    guess. Same shape as `_from_issues` now: a single hit decides, anything else abstains."""
    parts = set(re.split(r"[^a-z0-9]+", text.lower()))
    hit = [slug for slug in known if slug in parts]
    return hit[0] if len(hit) == 1 else ""


def _issue_area(root: Path, branch: str, known: list[str]) -> str:
    """Plan section 3 signal 2: `fix/1234-…` -> issue #1234 -> its area label.

    The code read every open issue of the LOGIN instead, which in this vault spans three
    areas and therefore abstained at every `/start` — a signal that can never fire is not a
    signal. The branch names ONE issue, and that issue either carries one area or names none."""
    found = ISSUE_IN_BRANCH.search(branch)
    item = _gh_issue(root, found.group(1)) if found else None
    hit = [slug for slug in known if _labelled(item or {}, slug)]
    return hit[0] if len(hit) == 1 else ""


def _from_issues(root: Path, login: str, known: list[str]) -> str:
    """The ONE area this contributor has open issues in; two areas name no area."""
    listed = _gh(root, "issue", login) if login else None
    hit = [slug for slug in known if _counted(listed, slug) not in ("0", "UNKNOWN")]
    return hit[0] if len(hit) == 1 else ""


def choose_area(root: Path, signals: dict[str, str]) -> str | None:
    """The signals of plan section 3, in order, first answer wins; `None` means ASK, once.

    An area named outright is not checked against the vocabulary: in a repository with no
    `DOMAIN.md` the declared layer's areas are the prose sections of `CONTEXT.md`, and
    refusing the name there is what made `--area` unusable in every product repository."""
    if signals.get("area"):
        return signals["area"]
    known = list(areas(root))
    branch = signals.get("branch", "")
    for pick in (_named_in(branch, known), _issue_area(root, branch, known),
                 _from_issues(root, signals.get("login", ""), known),
                 _named_in(_priority(root), known)):
        if pick in known:
            return pick
    return None


def print_rows(pack: dict[str, Any]) -> list[str]:
    """Time 1 — the pack as rows. `PACK=CTX-…` told the agent nothing it could act on.

    `path: -` where a row has none. Echoing the `source_id` into the path column read
    `path: DEC-1`, which is not a path and is not where that Decision lives."""
    out = []
    for key in PACK_KEYS:
        for row in pack.get(key) or []:
            out.append(PACK_ROW.format(layer=row.get("layer") or receipt.LAYER.get(key, key),
                                       sid=row.get("source_id", ""),
                                       path=row.get("path") or "-",
                                       fresh=row.get("freshness", "UNKNOWN")))
    for area in pack.get("areas") or []:
        out += print_rows({"documents": area.get("documents")})
    return out


def _resolved(root: Path, area: str) -> dict[str, Any]:
    """Resolve with the flight layer bound to what is LEFT of the one budget, and put its own
    default back afterwards.

    Bound, because that layer makes two `gh` calls per area at 30 s each of its own: bounding
    only the dashboard's calls would still let a stuck tracker cost 66 s and blow the 25 s the
    package allows the whole script, which is the failure the budget exists to end. Restored,
    because the first version of this set the module global and LEFT it set, so every later
    resolve in the process inherited a one-second tracker — a test module that had nothing to
    do with this went red, and a library caller would have inherited it in silence."""
    before = tracker.TIMEOUT
    tracker.TIMEOUT = max(1, int(_left()))
    try:
        return contextpack.resolve(root, "", receipt.selected_domains(root, area, []), degrade=True)
    finally:
        tracker.TIMEOUT = before


def _time_one(root: Path, area: str, sid: str) -> list[str]:
    """Arm the receipt for the chosen area — the debt of #404 — then resolve and print."""
    receipt.configure(sid or None, area, sealer.BUDGET)
    rows = print_rows(_resolved(root, area)) + [f"{layer}: {n} cut by budget"
                                                for layer, n in receipt.last_cut().items()]
    return rows if sid else rows + ["RECEIPT: none — no open session"]


def _stage_one(root: Path, area: str, sid: str) -> list[str]:
    """Time 1, or the reason there is none — and the index is delivered either way.

    A `ContractError` out of here took stdout with it, so an unknown area or an unwritable
    receipt cost the session time 0 as well: the half that always works. `OSError` too, since
    round 2: the invariant held for the errors this code raises and not for the ones the
    filesystem raises, which is the half nobody writes a code for."""
    try:
        return _time_one(root, area, sid)
    except cbb.ContractError as exc:
        return [f"PACK: blocked — {exc.code}: {exc.detail}"]
    except OSError as exc:
        return [f"PACK: blocked — {type(exc).__name__}: {exc.strerror or exc}"]


def _stale_line(root: Path) -> list[str]:
    """One line naming what is STALE, printed at /start before any area is chosen.

    `/start` holds the pack rows for lane entry, so a STALE row would reach nobody until a
    lane opened. A pack that refuses says so HERE too, as `STALE: unknown — …`: with no area
    chosen there is no stage one, and an empty line would be silence (W3c).

    It counts the rows of the pack the session receives, with the function its receipt uses
    (`stale_rows`), so the two cannot disagree: a Decision in `dropped` is not counted by
    either (critic round 2 on #493). Armed with no session, so this emission writes nothing."""
    receipt.configure(None, "", sealer.BUDGET)
    try:
        rows = sealer.stale_rows(_resolved(root, ""))
    except cbb.ContractError as exc:  # never silence: the refusal is what the human must see
        return [f"STALE: unknown — the pack refused ({exc.code}: {exc.detail})"]
    except OSError as exc:
        return [f"STALE: unknown — the pack refused ({type(exc).__name__}: {exc.strerror or exc})"]
    names = sorted(row["path"] for row in rows)
    return [f"STALE: {len(names)} row(s) — {', '.join(names)}"] if names else []


def brief(root: Path, signals: dict[str, str]) -> list[str]:
    """Time 0, the choice, and time 1 — or time 0 and ONE question with the index above it.

    With NO area map there is nothing to ask about and nothing to filter by, so the pack is
    emitted whole. The first version asked `candidates: none declared` and never reached time
    1, which is every adopting repository: the map is this repository's issue labels crossed
    with the host's own `domain_id`s, and an adopting host declares none of them (#344)."""
    lines, area = dashboard(root) + _stale_line(root), choose_area(root, signals)
    sid = signals.get("sid", "")
    if area is None and not areas(root):
        return lines + [f"{NO_MAP} — unfiltered pack"] + _stage_one(root, "", sid)
    if area is None:
        return lines + ["QUESTION: which area? candidates: " + ", ".join(sorted(areas(root)))]
    return lines + [f"AREA_CHOSEN: {area}"] + _stage_one(root, area, sid)


def _sid(root: Path, given: str) -> str:
    """The session the receipt belongs to: the one named, else one still OPEN TODAY.

    An `end.json` beside the `start.json` means closed. An open one from last week means
    ABANDONED, and stamping today's pack with today's `ts` inside it tells the audit that
    session had this context. Neither gets a receipt: no id, and `configure(None, …)` then
    writes nothing at all — T5's rule, held at the bottom. A caller that wants a receipt
    passes `--sid`, which stays the door."""
    if given:
        return given
    found = _open_sessions(root)
    return max(found, key=lambda path: path.stat().st_mtime).parent.name if found else ""


def _open_sessions(root: Path) -> list[Path]:
    """The start receipts of sessions still open, inside a window with BOTH ends.

    A ceiling, because `>= now - 24h` alone let a receipt dated in the FUTURE — clock skew, a
    restored backup, a copied tree — win every comparison and collect the pack of a session
    that has not started. `is_file()`, because `glob` returns a symlink to nowhere and
    `stat()` on it raises `OSError`, which is not a `ContractError` and therefore killed the
    process with an empty stdout: the index went with it."""
    now = time.time()
    return [path for path in (root / "state" / "session").glob("*/start.json")
            if path.is_file() and not (path.parent / "end.json").exists()
            and now - SESSION_MAX_AGE <= path.stat().st_mtime <= now]


def _branch(root: Path) -> str:
    try:
        done = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "rev-parse",
                               "--abbrev-ref", "HEAD"], capture_output=True, text=True,
                              timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def _signals(opts: argparse.Namespace, root: Path) -> dict[str, str]:
    return {"area": opts.area, "branch": opts.branch or _branch(root),
            "login": opts.login, "sid": _sid(root, opts.sid)}


def main() -> int:
    ap = argparse.ArgumentParser(description="#405 — the two-stage /start")
    ap.add_argument("command", nargs="?", choices=["brief", "dashboard"], default="dashboard")
    ap.add_argument("--root", type=Path, default=Path("."))
    for flag in ("--sid", "--area", "--branch", "--login"):
        ap.add_argument(flag, default="")
    opts = ap.parse_args()
    root = opts.root.resolve()
    try:
        lines = (brief(root, _signals(opts, root)) if opts.command == "brief"
                 else dashboard(root))
    except cbb.ContractError as exc:
        print(f"{exc.code}: {exc.detail}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
