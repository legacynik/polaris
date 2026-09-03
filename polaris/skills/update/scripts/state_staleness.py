#!/usr/bin/env python3
"""state_staleness.py — is this state file due for consolidation? MEASURE ONLY, never consolidate.

The donor (references/marvin-template-1.1.0, .claude/commands/{update,end}.md step 5) makes /end
itself do the rebuild when state is 3+ days stale. We split that in two, deliberately: /end MEASURES
(this script, cheap, read-only) and OFFERS; the expensive consolidation runs in polaris-status, which
the contributor approves with a yes/no. /start stays the cheap command, /status the expensive one.

So this script writes NOTHING. It reads a state file and prints one JSON verdict on stdout:

    FRESH   — nothing fired; no consolidation offer needed
    DUE     — at least one signal fired; reason names which, with the measured numbers
    UNKNOWN — the date is missing or unparseable; we refuse to call that fresh

DUE outranks UNKNOWN: an unknown date does not erase a signal that already fired on its own
(a 47k-token file with no `Updated:` line is due for consolidation whatever its date says).

THE FILE IS NOT ONE STATE WITH ONE AGE. Overwrite is PER-LANE (founder, 2026-09-01): seven lanes can
be open, and updating one leaves the other six byte-identical, dates included. So the file verdict is
a ROLLUP, never the unit of action — `lanes` carries the per-lane truth, each lane FRESH / DUE /
PARKED / UNKNOWN on its own, so a consumer can say "lane X has not moved in 9 days and is not marked
parked" instead of "your file is stale". A parked lane is a DECLARED STATE, not a defect to repair:
parking is the normal shape of parallel development, and age alone never makes a lane DUE.
`actions` says out loud that a whole-file rebuild — the donor's step 5 answer to staleness — is
UNSUPPORTED here, because against a multi-lane file it would destroy every parked lane.

Usage:  state_staleness.py PATH [--now YYYY-MM-DD]
        state_staleness.py --selfcheck
Exit is 0 whenever a verdict was emitted — the verdict is the payload, not the exit code.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# --- thresholds ------------------------------------------------------------------------------
# The 3-day figure is the DONOR's, verbatim ("If 3+ days old: flag it", marvin-template-1.1.0
# update.md step 5 / end.md step 5). It is a STARTING POINT to be measured against our own
# sessions, not a law we inherited. Only MAX_OPEN_ITEMS below is measured; the rest are guesses.
STALE_AFTER_DAYS = 3  # donor wording is "3+ days", so >= fires: exactly 3 days is DUE
MAX_UPDATED_LINES = 1  # the contract is ONE `Updated:` line, overwritten (_polaris/CLAUDE.md)
MAX_OPEN_SECTIONS = 1  # one `Open` section; more means session blocks were appended, not overwritten
# Load, not corruption: a busy week is a busy week, and a big number here is not a defect. Measured
# from the vault as it stands (2026-09-01): the two files in canonical form carry 7 (_polaris) and
# 12 items in a second, 62 in a third and 30 in current-state.md. 15 clears both healthy files with room for
# a busy week. Starting point to calibrate against real sessions, not an inherited law.
MAX_OPEN_ITEMS = 15
MAX_TOKENS = 4000  # measured 2026-08-30: current.md at ~7.8k tokens was already bloat
CHARS_PER_TOKEN = 4  # rough estimate — stdlib only, no tokenizer here; report it as approximate
# A LANE is not the file. The `end` skill states it plainly: "a branch with no recent commits is
# parked, not dead", and "work parked on a live branch while its owner spent the week elsewhere is
# the normal shape of parallel development". So a lane gets a week before anyone asks about it —
# well past the file-level 3. Starting point, to calibrate against real sessions.
LANE_STALE_AFTER_DAYS = 7

THRESHOLDS = {
    "stale_after_days": STALE_AFTER_DAYS,
    "lane_stale_after_days": LANE_STALE_AFTER_DAYS,
    "max_updated_lines": MAX_UPDATED_LINES,
    "max_open_sections": MAX_OPEN_SECTIONS,
    "max_open_items": MAX_OPEN_ITEMS,
    "max_tokens": MAX_TOKENS,
}

# Founder's correction, 2026-09-01: overwrite is PER-LANE, not per-file. Updating one lane leaves
# every other lane byte-identical, parked ones included. The donor's step 5 answers "3+ days stale"
# with a whole-file rewrite; against a seven-lane file that destroys six lanes of parked work. The
# schema says so out loud, so no consumer can read DUE as licence to rebuild.
ACTIONS = {
    "supported": ["reconcile_lane"],
    "unsupported": ["rebuild_file"],
    "why": "state is overwritten per lane, not per file: a whole-file rebuild destroys every parked "
           "lane. DUE is never licence to rewrite this file — reconcile the named lanes instead.",
}

# `Updated:` / `Last updated:` as the line's OWN header — column 0, bold markers allowed
# (the donor writes `**Last updated:** {date}`). Deliberately NO leading bullet and NO indent:
# `- **updated:** 2026-07-14` and `    Updated: ...` are a nested block's field, not the file's
# header. Counting them inflates the stacking signal and, worse, can rescue a stale file into
# looking fresh (real case in a product repo: `state/current.md` lines 168 and 195).
UPDATED_LINE = re.compile(r"^(?:\*\*)?(?:last\s+updated|updated)(?:\*\*)?\s*:", re.I)
ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
HEADING = re.compile(r"^#{1,6}\s")
OPEN_HEADING = re.compile(r"^#{1,6}\s+open\b", re.I)
LIST_ITEM = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
THREAD_LEAD = re.compile(r"^\*\*")  # the vault opens a thread with `**Topic** — ...`

# Lane parsing, against the format the `end` skill documents:
#   - `branch` — <done; next; blocker> · wt: <worktree path> · since YYYY-MM-DD
# `since` is the ONLY date read as a lane's last-touched. Deliberately not any ISO date on the
# line: real lanes carry prose dates that mean something else entirely — "Moratoria skill fino al
# 2026-09-28" is a future deadline, "CHIUSA 2026-08-31" a closure date. Reading either as
# last-touched would invent a false age, and a false age is what authorises destroying a lane.
LANE_SINCE = re.compile(r"\bsince\s*:?\s*(\d{4}-\d{2}-\d{2})\b", re.I)
LANE_WT = re.compile(r"\bwt\s*:\s*\S", re.I)  # a live worktree still holds the branch
# Pause words observed in the live vault, not invented: `SOSPESO` in one repo's state/current.md,
# `FREEZE` and `Moratoria` (_polaris/state/current.md).
LANE_PAUSED = re.compile(r"\b(?:parked|paused|parcheggiat\w*|sospes\w*|freeze|frozen|"
                         r"moratoria|on hold|in pausa)\b", re.I)
LANE_BRANCH = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)`([^`]+)`")
LANE_BOLD = re.compile(r"^\*\*([^*]+)\*\*")

# (state text, expected verdict, substring the reason must name) — evaluated against 2026-09-01.
_SELFCHECK_CASES = [
    ("Updated: 2026-08-30 — x\n", "FRESH", "2 days"),
    ("**Last updated:** 2026-08-30\n", "FRESH", "2 days"),          # donor's bold header form
    ("Updated: 2026-08-28 — x\n", "DUE", "4 days"),                 # age
    ("Updated: 2026-08-29\n", "DUE", "3 days"),                     # boundary: donor's "3+" fires
    ("# no date anywhere\n", "UNKNOWN", "no `Updated:` line"),
    ("Last updated: Not yet configured\n", "UNKNOWN", "none with a parseable date"),
    ("Updated: 2026-09-01\nUpdated: 2026-08-31\n", "DUE", "2 stacked"),
    # two Open signals, deliberately distinct: stacked sections = broken, many items = busy
    ("Updated: 2026-09-01\n## Open (a)\n## Open (b)\n", "DUE", "appended, not overwritten: 2 `Open`"),
    ("Updated: 2026-09-01\n# Open\n\n- a\n- b\n- c\n", "FRESH", "no signal fired"),   # one section
    ("Updated: 2026-09-01\n# Priorities\n\n- a\n", "FRESH", "no signal fired"),       # zero sections
    ("Updated: 2026-09-01\n# Open\n" + "- t\n" * (MAX_OPEN_ITEMS + 1), "DUE", "open items"),
    # lanes: parked is a DECLARED STATE, age alone never makes it DUE
    ("Updated: 2026-09-01\n# Open\n- `x` — a · wt: /tmp/w · since 2026-08-01\n", "FRESH", "no signal"),
    ("Updated: 2026-09-01\n# Open\n- `x` — a **SOSPESO** · since 2026-08-01\n", "FRESH", "no signal"),
    ("Updated: 2026-09-01\n# Open\n- `x` — a · since 2026-08-01\n", "DUE", "`x` (31 days"),
    ("Updated: 2026-09-01\n# Open\n- `x` — a · since 2026-08-31\n", "FRESH", "no signal"),
    ("Updated: 2026-09-01\n# Open\n- `x` — no date at all\n", "FRESH", "no signal"),  # UNKNOWN age
    ("Updated: 2026-09-01\n" + "x" * (MAX_TOKENS + 1) * CHARS_PER_TOKEN, "DUE", "tokens"),
    ("Updated: 2026-08-28\n- **updated:** 2026-09-01\n", "DUE", "4 days"),   # nested field ignored
    ("Updated: 2026-08-28\n    Updated: 2026-09-01\n", "DUE", "4 days"),     # indented, ditto
    ("## Open (a)\n## Open (b)\n", "DUE", "date unknown"),          # DUE outranks UNKNOWN, and says so
]


def _parse_date(line: str) -> date | None:
    """First ISO date on the line, or None (the donor placeholder 'Not yet configured' hits None)."""
    m = ISO_DATE.search(line)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:  # e.g. 2026-13-45 — shaped like a date, isn't one
        return None


def _open_blocks(lines: list[str]) -> tuple[int, list[tuple[int, str]]]:
    """(`Open` sections, [(1-based line no, text)] of each thread line inside them).
    ponytail: block detection is a heuristic tuned to the shapes actually in the vault — a thread
    line is a column-0 line that OPENS a block: it follows a blank line, or is a list marker, or is
    a `**bold lead**`. Swap in a real markdown parse if a state file ever nests deeper."""
    sections, items = 0, []
    inside, prev_blank = False, True
    for no, ln in enumerate(lines, 1):
        if HEADING.match(ln):
            inside = bool(OPEN_HEADING.match(ln))
            sections += inside
            prev_blank = True
            continue
        if inside and ln.strip() and not ln[:1].isspace():
            if prev_blank or LIST_ITEM.match(ln) or THREAD_LEAD.match(ln):
                items.append((no, ln))
        prev_blank = not ln.strip()
    return sections, items


def _lane_id(text: str) -> str:
    """The branch in backticks if the line follows the documented format, else its bold lead, else
    the lead before the ` — ` separator. This id is what a consumer acts on, so it must never be a
    mid-token truncation of prose (real case: a product repo's current.md:48, branch not in backticks)."""
    for pat in (LANE_BRANCH, LANE_BOLD):
        m = pat.match(text)
        if m:
            return m.group(1).strip()
    lead = LIST_ITEM.sub("", text.strip(), count=1)
    return re.split(r"\s+[—–-]\s+", lead, maxsplit=1)[0].strip()[:60]


def _lane_status(parked: bool, age: int | None) -> str:
    """A parked lane is a DECLARED STATE, not a defect: age alone NEVER makes it DUE. An undecidable
    age is UNKNOWN, never DUE — today's real lanes carry no `since` at all, and inventing staleness
    for them is exactly what would authorise destroying parked work."""
    if parked:
        return "PARKED"
    if age is None:
        return "UNKNOWN"
    return "DUE" if age >= LANE_STALE_AFTER_DAYS else "FRESH"


def _lane(no: int, text: str, now: date) -> dict:
    """One lane record, enough for a consumer to act on THIS lane without touching the others."""
    m = LANE_SINCE.search(text)
    since = _parse_date(m.group(1)) if m else None
    age = (now - since).days if since else None
    parked_by = [name for name, pat in (("wt", LANE_WT), ("pause-word", LANE_PAUSED))
                 if pat.search(text)]
    return {
        "id": _lane_id(text), "line": no,
        "since": since.isoformat() if since else None, "age_days": age,
        "parked": bool(parked_by), "parked_by": parked_by,
        "status": _lane_status(bool(parked_by), age),
    }


def measure(text: str) -> dict:
    """Raw counts, no judgement. `last_updated` is the NEWEST dated line: stacking is penalised by
    its own signal, so it must not also make a freshly-touched file look stale by age."""
    lines = text.splitlines()
    updated = [ln for ln in lines if UPDATED_LINE.match(ln)]
    dates = [d for d in (_parse_date(ln) for ln in updated) if d is not None]
    newest = max(dates) if dates else None
    sections, items = _open_blocks(lines)
    return {
        "updated_lines": len(updated),
        "dated_updated_lines": len(dates),
        "last_updated": newest.isoformat() if newest else None,
        "age_days": None,  # filled by assess_text, which owns `now`
        "open_sections": sections,
        "open_items": len(items),
        "tokens_estimate": len(text) // CHARS_PER_TOKEN,
        "bytes": len(text.encode("utf-8")),
    }


def _stale_lane_signal(lanes: list[dict]) -> list[tuple[str, str]]:
    """Names the lanes and their line numbers: the offer must be actionable on THOSE lanes, never
    on the file. PARKED and UNKNOWN lanes are excluded by _lane_status, which is the whole point."""
    stale = [ln for ln in lanes if ln["status"] == "DUE"]
    if not stale:
        return []
    return [("stale_lanes", "not moved and not marked parked: " + ", ".join(
        f"`{ln['id']}` ({ln['age_days']} days, line {ln['line']})" for ln in stale))]


def _signals(m: dict, lanes: list[dict]) -> list[tuple[str, str]]:
    """(name, human reason) for every threshold crossed. Empty list = nothing is due."""
    out: list[tuple[str, str]] = _stale_lane_signal(lanes)
    if m["age_days"] is not None and m["age_days"] >= STALE_AFTER_DAYS:
        out.append(("age", f"{m['age_days']} days since {m['last_updated']} "
                           f"(threshold {STALE_AFTER_DAYS})"))
    if m["updated_lines"] > MAX_UPDATED_LINES:
        out.append(("stacked_updated_lines", f"{m['updated_lines']} stacked `Updated:` lines "
                                             f"(contract is {MAX_UPDATED_LINES})"))
    if m["open_sections"] > MAX_OPEN_SECTIONS:  # corruption: appended instead of overwritten
        out.append(("open_sections", f"appended, not overwritten: {m['open_sections']} `Open` "
                                     f"sections (contract is {MAX_OPEN_SECTIONS})"))
    if m["open_items"] > MAX_OPEN_ITEMS:  # load: the file is busy, not broken
        out.append(("open_items", f"carrying {m['open_items']} open items "
                                  f"(threshold {MAX_OPEN_ITEMS})"))
    if m["tokens_estimate"] > MAX_TOKENS:
        out.append(("size", f"~{m['tokens_estimate']} tokens (threshold {MAX_TOKENS})"))
    return out


def _date_note(m: dict) -> str:
    """Said out loud in the reason even when the verdict is DUE for another cause — otherwise a
    reader concludes that clearing the other signal alone makes the file fresh again."""
    if m["updated_lines"] == 0:
        return "date unknown (no `Updated:` line)"
    return f"date unknown ({m['updated_lines']} `Updated:` line(s), none with a parseable date)"


def _due(m: dict, fired: list[tuple[str, str]]) -> dict:
    """DUE outranks UNKNOWN: an undecidable date does not erase a signal that already fired."""
    parts = [r for _, r in fired]
    if m["last_updated"] is None:
        parts.insert(0, _date_note(m))
    return {"verdict": "DUE", "reason": "; ".join(parts), "signals": [n for n, _ in fired],
            "measured": m, "lanes": [], "thresholds": THRESHOLDS, "actions": ACTIONS}


def _settled(kind: str, reason: str, m: dict) -> dict:
    """FRESH or UNKNOWN — the two verdicts reached with no signal fired."""
    return {"verdict": kind, "reason": reason, "signals": [], "measured": m,
            "lanes": [], "thresholds": THRESHOLDS, "actions": ACTIONS}


def assess_text(text: str, now: date) -> dict:
    """The whole decision, on a string. No IO, no clock — both are injected by the caller.
    The file verdict is a ROLLUP over the lanes, never the unit of action: `lanes` carries the
    per-lane truth so a consumer reconciles the lanes that moved and leaves the parked ones alone."""
    m = measure(text)
    lanes = [_lane(no, txt, now) for no, txt in _open_blocks(text.splitlines())[1]]
    if m["last_updated"]:
        m["age_days"] = (now - date.fromisoformat(m["last_updated"])).days
    fired = _signals(m, lanes)
    if fired:
        out = _due(m, fired)
    elif m["last_updated"] is None:
        out = _settled("UNKNOWN", f"{_date_note(m)} — refusing to assume fresh", m)
    else:
        out = _settled("FRESH", f"{m['age_days']} days since {m['last_updated']}, "
                                f"~{m['tokens_estimate']} tokens, no signal fired", m)
    out["lanes"] = lanes
    return out


def assess_path(path: Path, now: date) -> dict:
    """Read-only. An unreadable file is UNKNOWN, never FRESH, and still valid JSON."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _settled("UNKNOWN", f"cannot read {path}: {exc.strerror or exc}", measure(""))
    return assess_text(text, now)


def _selfcheck_lanes(now: date) -> None:
    """A fresh lane is never dragged in by a stale sibling: per-lane, not per-file."""
    mixed = assess_text("Updated: 2026-09-01\n# Open\n- `keep` — a · since 2026-08-31\n"
                        "- `stale` — b · since 2026-08-01\n", now)
    assert [ln["status"] for ln in mixed["lanes"]] == ["FRESH", "DUE"], mixed["lanes"]
    assert "`stale`" in mixed["reason"] and "`keep`" not in mixed["reason"], mixed["reason"]
    assert mixed["actions"]["unsupported"] == ["rebuild_file"], mixed["actions"]
    parked = assess_text("Updated: 2026-09-01\n# Open\n- `p` — a · wt: /w · since 2026-01-01\n", now)
    assert parked["lanes"][0]["status"] == "PARKED", parked["lanes"]
    assert parked["verdict"] == "FRESH", parked  # 8 months old and still not an alarm


def _selfcheck() -> None:
    """Same branches the unittest gate covers, runnable with no test runner (repo convention)."""
    now = date(2026, 9, 1)
    for text, want_verdict, want_in_reason in _SELFCHECK_CASES:
        got = assess_text(text, now)
        assert got["verdict"] == want_verdict, (want_verdict, got)
        assert want_in_reason in got["reason"], (want_in_reason, got["reason"])
        json.loads(json.dumps(got))  # every branch must serialise
    stacked = assess_text("Updated: 2026-09-01\nUpdated: 2026-08-31\n", now)
    assert stacked["measured"]["age_days"] == 0 and "age" not in stacked["signals"], stacked
    assert assess_path(Path("/nonexistent/state.md"), now)["verdict"] == "UNKNOWN"
    _selfcheck_lanes(now)
    print(f"SELF-CHECK OK ({len(_SELFCHECK_CASES)} cases): fresh/due/unknown, 3-day boundary both "
          "sides, stacked lines, Open sections (broken) vs Open items (busy), size, "
          "nested+indented non-headers, unknown date under a fired signal, unreadable file, "
          "per-lane parked/stale/unknown, rebuild declared unsupported, JSON in every branch")


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="state file staleness verdict (read-only, JSON on stdout)")
    ap.add_argument("path", nargs="?", type=Path, help="state file, e.g. state/current.md")
    ap.add_argument("--now", help="YYYY-MM-DD — inject the date instead of reading the clock")
    ap.add_argument("--selfcheck", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = _parser()
    args = ap.parse_args(argv)
    if args.selfcheck:
        return _selfcheck() or 0
    if not args.path:
        ap.error("path required (or --selfcheck)")
    try:
        now = date.fromisoformat(args.now) if args.now else date.today()
    except ValueError:
        now = None
        out = _settled("UNKNOWN", f"--now is not an ISO date: {args.now!r}", measure(""))
    else:
        out = assess_path(args.path, now)
    # every branch carries the same top-level keys: a consumer must never KeyError on the path it
    # can least afford to crash on
    out["now"] = now.isoformat() if now else None
    out["path"] = str(args.path)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
