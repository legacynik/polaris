#!/usr/bin/env python3
"""The founder's queue at the top of /start, and one line when the cockpit needs a rewrite.

`## Coda founder` holds what lives ONLY in the cockpit — an ok awaited, a key to rotate, a paused
job, a deadline — and a rewrite that drops it loses it for good (measured 2026-10-19: 2-4 live
items lost per repo without the section, 0 with it). So /start prints its top, every security
item and every deadline within a week, counts the rest by kind, and asks about ONE old item.

Local and read-only: the cockpit file plus at most one `git log -1`. A missing file or section is
silence, never an error, and a repo with no commit in 60 days costs nothing at all.
"""
from __future__ import annotations

import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "end" / "scripts"))
from _brief_parts import git, section  # noqa: E402
from state_lines import read  # noqa: E402

QUEUE = "## Coda founder"
SHOWN, WIDTH, DEADLINE_DAYS, ASK_DAYS, DORMANT_DAYS, MAX_CHARS = 5, 120, 7, 30, 60, 8000
# Whole words only: `down` is in "markdown", `key` in "keyword", `prod` in "prodotto".
# ponytail: `token` also means an LLM token count; split it from a credential if that ever shows up.
SECURITY = re.compile(r"\b(secrets?|segret[oi]|password|passwd|api[ _-]?keys?|keys?|tokens?|"
                      r"chiav[ei]|credenzial\w*|credentials?|ruot\w*|rotat\w*|rotazion\w*)\b", re.I)
PROD = re.compile(r"\b(prod|production|produzione|paus\w*|paused|bloccat\w*|blocked|down)\b", re.I)
SOON = re.compile(r"\b(oggi|domani|today|tomorrow)\b", re.I)
KINDS = (("ok", re.compile(r"\b(ok|via libera|approv\w*)\b", re.I)),
         ("decisions", re.compile(r"\b(decid\w*|decision\w*|scelta|sì o no|sì/no|yes-no|yes/no)",
                                  re.I)))
# The age slot of the contract line `<what> · <since YYYY-MM-DD, from …> · <unblock>`.
AGE = re.compile(r"(?:·\s*|\bsince\s+|\bdal\s+)(\d{4}-\d{2}-\d{2})", re.I)
ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def _iso(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _age(item: str) -> date | None:
    m = AGE.search(item)
    return _iso(m.group(1)) if m else None


def _deadline(item: str, now: date) -> bool:
    """A date in [now, now+7] that is NOT the age slot, or «oggi»/«domani»."""
    m = AGE.search(item)
    rest = item[:m.start(1)] + item[m.end(1):] if m else item
    dates = [d for d in map(_iso, ISO.findall(rest)) if d]
    return bool(SOON.search(rest)) or any(now <= d <= now + timedelta(DEADLINE_DAYS) for d in dates)


def _urgency(item: str, now: date) -> int:
    """0 security · 1 deadline within a week · 2 production blocked or paused · 3 the rest."""
    if SECURITY.search(item):
        return 0
    if _deadline(item, now):
        return 1
    return 2 if PROD.search(item) else 3


def _kind(item: str) -> str:
    return next((name for name, pat in KINDS if pat.search(item)), "other")


def _cut(item: str) -> str:
    return item if len(item) <= WIDTH else item[:WIDTH - 1].rstrip() + "…"


def _queue(items: list[str], now: date) -> list[str]:
    """QUEUE lines (forced ones always), one typed QUEUE_MORE, at most one QUEUE_ASK."""
    order = sorted(range(len(items)), key=lambda i: (
        _urgency(items[i], now), _age(items[i]) or date.max, i))
    forced = [i for i in order if _urgency(items[i], now) < 2]
    shown = forced + [i for i in order if i not in forced][:max(0, SHOWN - len(forced))]
    out = [f"QUEUE: {_cut(items[i])}" for i in shown]
    rest = [_kind(items[i]) for i in order if i not in shown]
    counts = [f"+{rest.count(k)} {k}" for k in ("ok", "decisions", "other") if k in rest]
    out += [f"QUEUE_MORE: {' · '.join(counts)}"] if counts else []
    old = [i for i in order if (_age(items[i]) or now) <= now - timedelta(ASK_DAYS)]
    oldest = min(old, key=lambda i: _age(items[i]), default=None)
    ask = [f"QUEUE_ASK: keep or drop? {_cut(items[oldest])}"] if oldest is not None else []
    return out + ask


def _reasons(current: Path, lines: list[str], now: str) -> list[str]:
    """Short tokens step 2 acts on. The stale rule is `state_priorities.staleness`, never a copy."""
    import state_priorities
    text = "\n".join(lines)
    updated = sum(1 for ln in lines if ln.startswith("Updated:"))
    out = [f"updated-lines={updated}"] if updated > 1 else []
    out += [f"size={len(text)}"] if len(text) > MAX_CHARS else []
    out += [] if _has_queue(lines) else ["no-queue"]
    return out + (["priorities-stale"] if state_priorities.staleness(current, now) else [])


def _has_queue(lines: list[str]) -> bool:
    from state_sections import heading
    return any(heading(QUEUE).match(ln) for ln in lines)


def _dormant(main_wt: Path, now: date) -> bool:
    """No commit in 60 days. A failed git (no repo, no commit) is NOT dormant: it says nothing."""
    stamp = git(main_wt, "log", "-1", "--format=%ct")
    if not stamp.isdigit():
        return False
    return (now - datetime.fromtimestamp(int(stamp)).date()).days > DORMANT_DAYS


def emit_cockpit(current: Path, main_wt: Path, now: str) -> list[str]:
    """The queue and the rewrite signal, or nothing. Never raises: a brief that fails is worse."""
    try:
        today = date.fromisoformat(now)
        if not current.is_file() or _dormant(main_wt, today):
            return []
        lines, _, _ = read(current)
        body = section("\n".join(lines), QUEUE)
        items = [re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", ln) for ln in body]
        reasons = _reasons(current, lines, now)
        signal = [f"COCKPIT_REWRITE: {' · '.join(reasons)}"] if reasons else []
        return _queue(items, today) + signal
    except (OSError, ValueError, UnicodeDecodeError):
        return []


def _selfcheck() -> int:
    """Urgency by whole words, forced lines always shown, one typed count, one question."""
    import tempfile
    now = date(2026, 9, 3)
    ok = [_urgency("ruotare la chiave Stripe", now) == 0,
          _urgency("demo il 2026-09-05", now) == 1,
          _urgency("· since 2026-09-05, from x · ok", now) == 3,   # the age slot is no deadline
          _urgency("job in pausa", now) == 2,
          _urgency("aggiornare il markdown", now) == 3]            # `down` inside a word is not prod
    items = ["token da ruotare", *[f"ok sul piano {n}" for n in range(6)],
             "decidere il nome · since 2026-07-01"]
    out = _queue(items, now)
    shown = [ln for ln in out if ln.startswith("QUEUE: ")]
    ok += [shown[0] == "QUEUE: token da ruotare", len(shown) == SHOWN,
           any(ln.startswith("QUEUE_MORE: +") for ln in out),
           any(ln.startswith("QUEUE_ASK: ") and "decidere il nome" in ln for ln in out)]
    with tempfile.TemporaryDirectory() as d:
        ok.append(emit_cockpit(Path(d) / "absent.md", Path(d), "2026-09-03") == [])
    print(f"_cockpit_signal selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--selfcheck"]):
        print("usage: _cockpit_signal.py [--selfcheck]", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selfcheck())
