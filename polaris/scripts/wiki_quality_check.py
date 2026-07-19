#!/usr/bin/env python3
"""wiki_quality_check — the wiki-retrieval-quality signal for /polaris-status (not the hot paths).

Founder non-negotiable: stale/archived docs must NOT degrade retrieval. Recall already scores
`lifecycle: archived/disputed` at −100 (deprioritized) — but the draft→archived PROMOTION never
fires, so genuinely-stale docs sit at `active/draft/reviewed` and pollute the top-k. This finds them
(active + not touched in > max_age days) and PROPOSES promotion to archived; it never writes — like
state_reconcile, /polaris-status surfaces it and the founder confirms. Deterministic, on-demand.

Reuses the existing wiki frontmatter (`lifecycle:`, `updated:`); no new graph, no full rewrite (the
clean incremental distiller already exists in distill_runner.sh).

Usage: wiki_quality_check.py [wiki_dir] [--max-age 45] [--today YYYY-MM-DD]
       wiki_quality_check.py --selfcheck
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

ACTIVE = {"draft", "reviewed", "active", ""}  # NOT archived/disputed → still scored full in recall


def parse_frontmatter(text: str) -> dict:
    """lifecycle + updated (YYYY-MM-DD) from the leading --- block. Missing → {}."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    out: dict = {}
    for line in text[3:end if end > 0 else len(text)].splitlines():
        for key in ("lifecycle", "updated"):
            if line.strip().startswith(key + ":"):
                out[key] = line.split(":", 1)[1].strip().strip("'\"")[:10]
    return out


def age_days(updated: str, today: datetime.date) -> int | None:
    """Days between `updated` (YYYY-MM-DD) and today; None if unparseable."""
    try:
        return (today - datetime.date.fromisoformat(updated[:10])).days
    except (ValueError, TypeError):
        return None


def classify(docs: list[tuple[str, dict]], today: datetime.date, max_age: int) -> dict[str, list]:
    """Split docs into stale_active (degrade retrieval → propose archive), archived, fresh."""
    buckets: dict[str, list] = {"stale_active": [], "archived": [], "fresh": []}
    for name, fm in docs:
        lifecycle = fm.get("lifecycle", "")
        if lifecycle not in ACTIVE:
            buckets["archived"].append((name, fm))
            continue
        age = age_days(fm.get("updated", ""), today)
        buckets["stale_active" if (age is not None and age > max_age) else "fresh"].append((name, fm, age))
    return buckets


def scan(wiki_dir: Path, today: datetime.date, max_age: int) -> dict[str, list]:
    docs = []
    for p in wiki_dir.rglob("*.md"):
        if p.name.startswith("_") or "/journal/" in str(p):
            continue
        try:
            docs.append((str(p.relative_to(wiki_dir)), parse_frontmatter(p.read_text())))
        except OSError:
            continue
    return classify(docs, today, max_age)


def front_door_lag(wiki_dir: Path, repo_dir: str, max_lag: int) -> list[str]:
    """The real degrade signal (cardaq audit 2026-07-19): entry points that don't reflect recent work.
    A wiki can be 'clean' on absolute doc-age yet have a stale front door. Uses the doc's own
    `updated:` frontmatter (author-written) — NOT mtime, which git checkout resets to a meaningless
    'now'. Flags hot.md / newest journal entry when their `updated:` lags the newest commit by
    > max_lag days. This is exactly what an LLM audit finds by reading, made deterministic."""
    import subprocess
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI"], cwd=repo_dir,
                             capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        newest_commit = datetime.date.fromisoformat(out[:10])
    except (OSError, subprocess.SubprocessError, ValueError):
        return []  # graceful: no git → skip this signal, never block
    flags = []
    for label, path in [("hot.md", wiki_dir / "hot.md"), ("journal (newest)", _newest(wiki_dir / "journal"))]:
        if not (path and path.exists()):
            continue
        try:
            updated = parse_frontmatter(path.read_text()).get("updated", "")
        except OSError:
            continue
        lag = age_days(updated, newest_commit)  # days between doc's `updated:` and the newest commit
        if lag is not None and lag > max_lag:
            flags.append(f"  [front-door] {label} `updated:` {updated} lags newest commit by {lag}d — stale vetrina")
    return flags


def _newest(d: Path) -> Path | None:
    files = sorted(d.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True) if d.exists() else []
    return files[0] if files else None


def git_age(repo_dir: str, rel: str, today: datetime.date) -> int | None:
    """Days since the file's real last commit — the objectivity cross-check. A doc's `updated:`
    frontmatter lies (authors forget to bump it); git history doesn't. Only called on the handful
    that already failed the age filter, so it's cheap (never a full-repo scan)."""
    import subprocess
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cd", "--date=short", "--", rel],
                             cwd=repo_dir, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        return (today - datetime.date.fromisoformat(out)).days if out else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def report(buckets: dict[str, list], max_age: int, wiki_dir: Path | None = None) -> str:
    stale = buckets["stale_active"]
    if not stale:
        return f"wiki quality: clean — no active doc older than {max_age}d polluting retrieval."
    repo, sub = (str(wiki_dir.parent), wiki_dir.name) if wiki_dir else (".", ".wiki")
    archive, metadata_lag = [], []  # git-old too → real candidate; git-recent → live doc, stale field only
    for name, _fm, age in sorted(stale, key=lambda x: -(x[2] or 0)):
        g = git_age(repo, f"{sub}/{name}", datetime.date.today()) if wiki_dir else None
        (metadata_lag if (g is not None and g <= max_age) else archive).append((name, age, g))
    lines = [f"═══ WIKI QUALITY — {len(stale)} active doc(s) with stale `updated:` (>{max_age}d) ═══"]
    for name, age, g in archive[:12]:
        gt = f", git-touch {g}d" if g is not None else ""
        lines.append(f"  [archive?] {name} — updated {age}d{gt} → propose lifecycle: archived (verify supersession)")
    for name, age, g in metadata_lag[:12]:
        lines.append(f"  [metadata-lag] {name} — updated {age}d but git-touch {g}d → LIVE, just bump `updated:` — do NOT archive")
    lines.append(f"  Archived deprioritize at −100 in recall. {len(buckets['archived'])} already archived. Non-blocking.")
    return "\n".join(lines)


def _selfcheck() -> None:
    import tempfile
    today = datetime.date(2026, 7, 19)
    assert parse_frontmatter("---\nlifecycle: draft\nupdated: 2026-07-01\n---\nx") == {"lifecycle": "draft", "updated": "2026-07-01"}
    assert age_days("2026-07-01", today) == 18 and age_days("bad", today) is None
    with tempfile.TemporaryDirectory() as d:
        w = Path(d)
        (w / "old.md").write_text("---\nlifecycle: draft\nupdated: 2026-05-01\n---\nstale")
        (w / "new.md").write_text("---\nlifecycle: reviewed\nupdated: 2026-07-18\n---\nfresh")
        (w / "arch.md").write_text("---\nlifecycle: archived\nupdated: 2026-01-01\n---\ngone")
        (w / "_skip.md").write_text("---\nlifecycle: draft\nupdated: 2026-01-01\n---\nskip")
        b = scan(w, today, max_age=45)
        assert [n for n, *_ in b["stale_active"]] == ["old.md"], b        # old draft > 45d
        assert [n for n, *_ in b["fresh"]] == ["new.md"], b               # recent reviewed
        assert [n for n, *_ in b["archived"]] == ["arch.md"], b           # archived never "stale_active"
        assert "old.md" in report(b, 45) and "_skip" not in report(b, 45)
        (w / "hot.md").write_text("---\nupdated: 2026-07-15\n---\nsnapshot")
        (w / "journal").mkdir()
        (w / "journal" / "j.md").write_text("entry")
        assert _newest(w / "journal").name == "j.md"
        assert _newest(w / "empty") is None
        assert front_door_lag(w, str(w), max_lag=5) == []  # no git in tempdir → graceful, never raises
        assert git_age(str(w), "old.md", today) is None    # not a git repo → graceful, never raises
        assert "old.md" in report(b, 45, w)                # no git → falls to archive bucket, still surfaced
    # the real signal is deterministic: `updated:` 4d before the commit date > 3d threshold → flagged
    assert age_days("2026-07-15", datetime.date(2026, 7, 19)) == 4
    print("SELF-CHECK OK: frontmatter, age, stale/archived/fresh, _skip, _newest, front-door, git-gate graceful")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--selfcheck" in argv:
        _selfcheck()
        return 0
    max_age = int(argv[argv.index("--max-age") + 1]) if "--max-age" in argv else 45
    max_lag = int(argv[argv.index("--front-door-lag") + 1]) if "--front-door-lag" in argv else 5
    today = datetime.date.fromisoformat(argv[argv.index("--today") + 1]) if "--today" in argv else datetime.date.today()
    pos = [a for a in argv if not a.startswith("--") and a not in (str(max_age), str(max_lag), str(today))]
    wiki_dir = Path(pos[0]) if pos else Path("wiki")
    if not wiki_dir.exists():
        print(f"no wiki dir at {wiki_dir}", file=sys.stderr)
        return 0
    print(report(scan(wiki_dir, today, max_age), max_age, wiki_dir))
    # the real degrade signal: entry points that lag recent activity (cardaq audit)
    fd = front_door_lag(wiki_dir, str(wiki_dir.parent), max_lag)
    if fd:
        print(f"═══ FRONT-DOOR STALE — entry points don't reflect recent work (>{max_lag}d behind newest commit) ═══")
        print("\n".join(fd))
        print("  → the auto-distill trigger (distill_trigger.sh) keeps these fresh; this is its root symptom.")
    return 0  # observe-only, never a gate


if __name__ == "__main__":
    sys.exit(main())
