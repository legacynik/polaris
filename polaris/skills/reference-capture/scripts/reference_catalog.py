#!/usr/bin/env python3
"""Build a fail-closed Markdown catalog from opted-in external-reference dossiers."""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import quote, unquote



# The root list is part of the commit, not of whoever's shell ran the build:
# an undeclared root cannot be told apart from a legitimately absent dossier.
ROOTS_FILE = Path(__file__).resolve().parents[3] / "references" / "CATALOG.roots"

DEPTHS = {"note", "study", "deep"}
RELEVANCE = {"core", "adjacent", "watch"}
STATUSES = {"captured", "verified", "adopted", "rejected", "stale"}
REQUIRED = {
    "title", "description", "source_url", "analyzed_at", "reference_depth",
    "reference_relevance", "reference_status", "serves", "domains", "aliases", "capabilities",
}
SKIP_DIRS = {".git", ".wiki", "node_modules", "_archived", "__pycache__"}
BODY_HEADINGS = (
    "## Why relevant",
    "## Reusable mechanisms",
    "## What not to copy",
    "## Promotion status",
)
SOURCE_TYPES = {"video", "repo", "article", "paper", "changelog", "thread", "course"}
# The extraction spine, required from schema_version 2 at depth study/deep. Version 1 validated
# only the four verdict headings above, all of which describe our judgment of a source; none of
# them ever required the source's own content, so a dossier could pass every gate while holding
# no command, version or reproducible step. These are the sections that carry the content.
SPINE_HEADINGS = (
    "## Executive summary",
    "## Problemi che risolve",
    "## Problemi che NON risolve",
    "## Correlati",
    "## Punti di partenza",
    "## Contenuto completo",
    "## Rischi e caveat",
    "## Dati e numeri citati",
    "## Risorse citate",
    "## Alternative e scelte",
    "## Mapping sul nostro sistema",
    "## Actionable",
)
SPINE_DEPTHS = {"study", "deep"}
# `[` is excluded from the target so an inline list — `related: [[[x]]]` — yields `x` and not
# `[x`: both the inline and the block list form are legal, and a link must parse the same in each.
WIKILINK_RE = re.compile(r"\[\[([^\[\]|]+?)(?:\|[^\]]*)?\]\]")
_LINK_INDEX: dict[Path, set[str]] = {}
URL_RE = re.compile(r"https?://[^\s<>()\"']+")


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class Dossier:
    path: Path
    root: Path
    meta: dict[str, object]


def _scalar(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _inline_list(raw: str) -> list[str]:
    body = raw.strip()[1:-1].strip()
    if not body:
        return []
    return [_scalar(item) for item in next(csv.reader([body], skipinitialspace=True))]


def parse_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 3)
    if end < 0:
        raise CatalogError(f"{path}: unterminated frontmatter")
    lines = text[4:end].splitlines()
    meta: dict[str, object] = {}
    active_list: str | None = None
    bracket_key: str | None = None  # key whose `[` opened on its own line
    for number, line in enumerate(lines, 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if bracket_key:
            item = line.strip()
            if item == "]":
                bracket_key = None
            else:
                item = item.rstrip(",")
                if item:
                    cast = meta.setdefault(bracket_key, [])
                    cast.append(_scalar(item))
            continue
        if line.strip() == "[" and active_list:
            bracket_key = active_list
            continue
        if line.startswith("  - ") and active_list:
            cast = meta.setdefault(active_list, [])
            if not isinstance(cast, list):
                raise CatalogError(f"{path}:{number}: malformed list {active_list}")
            cast.append(_scalar(line[4:]))
            continue
        if line[:1].isspace() or ":" not in line:
            active_list = None
            continue
        key, raw = line.split(":", 1)
        key, raw = key.strip(), raw.strip()
        if not raw:
            meta[key] = []
            active_list = key
        elif raw.startswith("[") and raw.endswith("]"):
            meta[key] = _inline_list(raw)
            active_list = None
        elif raw.lower() in {"true", "false"}:
            meta[key] = raw.lower() == "true"
            active_list = None
        else:
            meta[key] = _scalar(raw)
            active_list = None
    return meta


def _list(meta: dict[str, object], key: str, path: Path) -> list[str]:
    value = meta.get(key)
    if not isinstance(value, list) or not value or not all(str(v).strip() for v in value):
        raise CatalogError(f"{path}: {key} must be a non-empty list")
    return [str(v).strip() for v in value]


def validate(path: Path, meta: dict[str, object], root: Path | None = None) -> None:
    missing = sorted(key for key in REQUIRED if key not in meta or meta[key] in ("", None, []))
    if missing:
        raise CatalogError(f"{path}: missing required fields: {', '.join(missing)}")
    _list(meta, "serves", path)
    _list(meta, "domains", path)
    _list(meta, "aliases", path)
    _list(meta, "capabilities", path)
    for key, allowed in (
        ("reference_depth", DEPTHS),
        ("reference_relevance", RELEVANCE),
        ("reference_status", STATUSES),
    ):
        if meta.get(key) not in allowed:
            raise CatalogError(f"{path}: invalid {key}={meta.get(key)!r}; allowed={sorted(allowed)}")
    if meta["reference_status"] in {"verified", "adopted"}:
        for key in ("source_version", "last_verified_at"):
            if not str(meta.get(key) or "").strip():
                raise CatalogError(f"{path}: reference_status {meta['reference_status']} requires {key}")
    text = path.read_text(encoding="utf-8", errors="replace")
    missing_headings = [heading for heading in BODY_HEADINGS if heading not in text]
    if missing_headings:
        raise CatalogError(f"{path}: missing body headings: {', '.join(missing_headings)}")
    _validate_v2(path, meta, text, root)


def _stem_index(root: Path) -> set[str]:
    """Basenames of every Markdown file under a root, memoized.

    Wikilink targets are written the way a human types them, so they resolve by stem far more
    often than by exact relative path. Building this once per root keeps link validation cheap
    enough to stay in the gate instead of becoming an optional lint nobody runs.
    """
    if root not in _LINK_INDEX:
        stems = set()
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                if name.endswith(".md"):
                    stems.add(name[:-3])
        _LINK_INDEX[root] = stems
    return _LINK_INDEX[root]


def _frontmatter_links(text: str) -> list[str]:
    """Wikilink targets declared in the frontmatter block.

    Read from the raw text rather than the parsed mapping so that both the inline and the block
    list form work: the field matters more than its YAML shape, and a dossier should not fail
    because of how someone wrote a list.
    """
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    head = text[:end]
    marker = head.find("related:")
    if marker == -1:
        return []
    return [m.strip() for m in WIKILINK_RE.findall(head[marker:])]


def _validate_v2(path: Path, meta: dict[str, object], text: str, root: Path | None) -> None:
    """Checks that apply only once a dossier declares schema_version 2.

    Absence of the field means version 1 and is validated exactly as before. Making the spine
    retroactive would invalidate every existing dossier on the day it lands, and a contract that
    breaks the whole corpus at once does not get adopted, it gets bypassed. Migration happens per
    file, the next time someone has that dossier open anyway.
    """
    if str(meta.get("schema_version") or "").strip() != "2":
        return
    source_type = str(meta.get("source_type") or "").strip()
    if source_type not in SOURCE_TYPES:
        raise CatalogError(
            f"{path}: schema_version 2 requires source_type in {sorted(SOURCE_TYPES)}; got {source_type!r}"
        )
    if meta["reference_depth"] not in SPINE_DEPTHS:
        return
    missing_spine = [heading for heading in SPINE_HEADINGS if heading not in text]
    if missing_spine:
        raise CatalogError(f"{path}: missing spine headings: {', '.join(missing_spine)}")
    links = _frontmatter_links(text)
    if not links:
        raise CatalogError(
            f"{path}: schema_version 2 at depth {meta['reference_depth']} requires at least one related link"
        )
    if root is None:
        return
    stems = _stem_index(root)
    dangling = []
    for target in links:
        candidate = target.strip().lstrip("/")
        if (root / candidate).exists() or (root / f"{candidate}.md").exists():
            continue
        if Path(candidate).name in stems:
            continue
        dangling.append(target)
    if dangling:
        raise CatalogError(f"{path}: related targets do not resolve: {', '.join(dangling)}")


def _candidate_files(root: Path):
    for base in (root / "references", root / "docs" / "references", root / "docs" / "research"):
        if not base.is_dir():
            continue
        for current, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (Path(current) / d / ".git").exists()]
            for name in files:
                if name.endswith(".md") and name not in {"INDEX.md", "CATALOG.md"}:
                    yield Path(current) / name


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/.,;]}").lower()


def _source_urls(meta: dict[str, object]) -> set[str]:
    urls: set[str] = set()
    for key in ("source_url", "source", "url"):
        value = meta.get(key)
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, str):
                continue
            urls.update(_normalize_url(match) for match in URL_RE.findall(item))
    return urls


def find_source_claims(roots: list[Path], source_url: str) -> list[tuple[Path, bool]]:
    target = _normalize_url(source_url)
    claims: list[tuple[Path, bool]] = []
    for root in roots:
        root = root.resolve()
        if not root.is_dir():
            raise CatalogError(f"root does not exist: {root}")
        for path in _candidate_files(root):
            meta = parse_frontmatter(path)
            if target in _source_urls(meta):
                claims.append((path.resolve(), meta.get("catalog") is True))
    return sorted(set(claims))


def lookup(roots: list[Path], source_url: str) -> int:
    claims = find_source_claims(roots, source_url)
    if not claims:
        print(f"NONE — no existing owner for {_normalize_url(source_url)}")
        return 0
    for path, admitted in claims:
        print(f"FOUND — {path} [{'catalog' if admitted else 'legacy'}]")
    if len(claims) > 1:
        print("COLLISION — update or consolidate existing claims before creating a dossier", file=sys.stderr)
        return 2
    return 0


def _roots_entry(line: str) -> str:
    """One roots-file line: full-line `#` comment, or a path with an optional ` #` note."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return ""
    return re.split(r"\s+#", stripped, maxsplit=1)[0].strip()


def home_checkout(repo: Path) -> Path:
    """This repo's MAIN checkout — the same commit must build from any worktree.

    Resolving `../../acme-web` against the running checkout made the catalog a
    function of WHERE it was built: from a linked worktree the sibling landed
    inside `.claude/worktrees/`, and every emitted link carried that depth.
    `git worktree list --porcelain` prints the main worktree first — the trick
    `hooks/scratchpad_stop_hook.py` already relies on. Outside a repository
    there is no worktree indirection, so the checkout is its own home.
    """
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CatalogError(f"cannot locate the main checkout of {repo}: git failed: {exc}") from exc
    if done.returncode != 0:
        return repo
    first = done.stdout.splitlines()[0] if done.stdout else ""
    if not first.startswith("worktree "):
        raise CatalogError(f"cannot locate the main checkout of {repo}: git said {first!r}")
    return Path(first[len("worktree "):]).resolve()


def _under(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _in_checkout(target: Path, repo: Path, home: Path) -> Path:
    """A canonical (main-checkout) path, brought back into the running checkout."""
    return repo / target.relative_to(home) if _under(target, home) else target


def read_roots_file(path: Path) -> list[Path]:
    """Declared roots. Entries resolve against the MAIN checkout's `references/`.

    An entry therefore reads exactly like the link it produces in CATALOG.md and
    means the same repository from every worktree of this one. A root inside this
    repo is still scanned in the checkout that is running: the catalog describes
    the commit under test, not whatever the main clone happens to have on disk.
    """
    if not path.is_file():
        raise CatalogError(
            f"roots file not found: {path} — declare the catalog roots there, "
            "or pass --root explicitly"
        )
    repo = path.parent.parent.resolve()
    home = home_checkout(repo)
    roots: list[Path] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        entry = _roots_entry(line)
        if not entry:
            continue
        root = _in_checkout((home / path.parent.name / entry).resolve(), repo, home)
        if not root.is_dir():
            # A silently skipped root is exactly how a whole repo's dossiers
            # went missing from the catalog without anyone noticing.
            raise CatalogError(f"{path}:{number}: declared root does not exist: {entry} -> {root}")
        roots.append(root)
    if not roots:
        raise CatalogError(f"{path}: declares no roots")
    return roots


def resolve_roots(cli_roots: list[Path], roots_file: Path) -> list[Path]:
    """Declared roots unless `--root` overrides them; either way, each root once."""
    roots = [Path(r).resolve() for r in cli_roots] if cli_roots else read_roots_file(roots_file)
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def collect(roots: list[Path]) -> list[Dossier]:
    dossiers: list[Dossier] = []
    by_source: dict[str, list[Path]] = {}
    for root in roots:
        root = root.resolve()
        if not root.is_dir():
            raise CatalogError(f"root does not exist: {root}")
        for path in _candidate_files(root):
            meta = parse_frontmatter(path)
            if meta.get("catalog") is not True:
                continue
            validate(path, meta, root)
            source = _normalize_url(str(meta["source_url"]))
            by_source.setdefault(source, []).append(path.resolve())
            dossiers.append(Dossier(path.resolve(), root, meta))
    dupes = {source: paths for source, paths in by_source.items() if len(set(paths)) > 1}
    if dupes:
        details = "; ".join(f"{source}: {', '.join(map(str, paths))}" for source, paths in sorted(dupes.items()))
        raise CatalogError(f"duplicate source ownership: {details}")
    return sorted(
        dossiers,
        key=lambda d: (str(d.meta["reference_relevance"]), str(d.meta["title"]).lower()),
    )


def _link(from_dir: Path, target: Path) -> str:
    rel = os.path.relpath(target, from_dir).replace(os.sep, "/")
    return quote(rel, safe="/._-")


def render(dossiers: list[Dossier], output: Path) -> str:
    lines = [
        "---",
        "title: External references catalog",
        "description: Generated cross-repo catalog of founder-selected external research dossiers.",
        "status: derived",
        "generated_by: reference-capture/scripts/reference_catalog.py",
        "---",
        "",
        "# External references catalog",
        "",
        "> Generated. Do not edit by hand; update the canonical dossier and rebuild.",
        "",
        f"**Dossiers:** {len(dossiers)}",
        "",
    ]
    for relevance in ("core", "adjacent", "watch"):
        group = [d for d in dossiers if d.meta["reference_relevance"] == relevance]
        lines.extend([f"## {relevance.title()}", ""])
        if not group:
            lines.extend(["_None._", ""])
            continue
        lines.extend([
            "| Reference | Depth | Status | Serves | Domains | Capabilities | Source |",
            "|---|---|---|---|---|---|---|",
        ])
        for dossier in group:
            meta = dossier.meta
            link = _link(output.parent.resolve(), dossier.path)
            serves = ", ".join(_list(meta, "serves", dossier.path))
            domains = ", ".join(_list(meta, "domains", dossier.path))
            caps = ", ".join(_list(meta, "capabilities", dossier.path))
            source = str(meta["source_url"])
            lines.append(
                f"| [{meta['title']}]({link}) | {meta['reference_depth']} | "
                f"{meta['reference_status']} | "
                f"{serves} | {domains} | {caps} | [upstream]({source}) |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _canonical(dossiers: list[Dossier], output: Path, repo: Path) -> tuple[list[Dossier], Path]:
    """Restate this checkout's paths as the main checkout's, so links stay stable.

    Only the relative distance between a dossier and the catalog is written to
    disk, so a build from a linked worktree must measure it where the file will
    live — otherwise the same commit emits `../../acme-web/...` from one
    checkout and `../../../../<home>/...` from another. For the same reason the
    catalog has to land inside the repo that declared the roots: written
    anywhere else its links resolve from there and nowhere else, which reads as
    a plausible file and is the last quiet wrong answer this tool had left.
    """
    out = output.resolve()
    if not _under(out, repo):
        raise CatalogError(
            f"output must live inside the repo that declares the roots: {out} is outside {repo}"
        )
    home = home_checkout(repo)
    if home == repo:
        return dossiers, out
    moved = [
        replace(d, path=home / d.path.relative_to(repo)) if _under(d.path, repo) else d
        for d in dossiers
    ]
    return moved, home / out.relative_to(repo)


def build(roots: list[Path], output: Path, repo: Path | None = None) -> int:
    """`repo` is the checkout that declared the roots; by contract it holds the catalog."""
    dossiers = collect(roots)
    content = render(*_canonical(dossiers, output, repo or output.resolve().parent.parent))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False) as handle:
        handle.write(content)
        temp = Path(handle.name)
    temp.replace(output)
    print(f"PASS — {len(dossiers)} dossiers -> {output}")
    return 0


def _write_dossier(path: Path, **overrides: object) -> None:
    data: dict[str, object] = {
        "title": path.stem,
        "description": f"Study of {path.stem}",
        "catalog": True,
        "source_url": f"https://example.test/{path.stem}",
        "source_version": "v1",
        "analyzed_at": "2026-08-18",
        "last_verified_at": "2026-08-18",
        "reference_depth": "study",
        "reference_relevance": "adjacent",
        "reference_status": "verified",
        "serves": ["polaris"],
        "domains": ["wiki"],
        "aliases": [path.stem],
        "capabilities": ["retrieval"],
    }
    data.update(overrides)
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, list):
            lines.append(f"{key}: [{', '.join(map(str, value))}]")
        else:
            lines.append(f"{key}: {value}")
    lines.extend([
        "---", "", "# Reference", "",
        "## Why relevant", "Useful to the served project.", "",
        "## Reusable mechanisms", "- Retrieval metadata.", "",
        "## What not to copy", "- Unverified implementation details.", "",
        "## Promotion status", "Reference only.", "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _selfcheck_roots_file() -> int:
    """The declared root list is the default input, and every way it fails is loud."""
    with tempfile.TemporaryDirectory(prefix="catalog roots ") as td:
        base = Path(td)
        index, other = base / "Index Repo", base / "Other Repo"
        _write_dossier(index / "references" / "own.md", reference_relevance="core")
        _write_dossier(other / "docs" / "research" / "other.md")
        roots_file = index / "references" / "CATALOG.roots"
        out = index / "references" / "CATALOG.md"
        argv = ["--roots-file", str(roots_file), "--output", str(out)]
        assert main(argv) == 1 and not out.exists(), "absent roots file must not build"
        roots_file.write_text("# self\n..\n# sibling\n../../Other Repo\n", encoding="utf-8")
        assert main(argv) == 0 and out.read_text().count("[upstream]") == 2
        assert main(argv + ["--root", str(other)]) == 0
        assert out.read_text().count("[upstream]") == 1, "--root must override the file"
        (base / "Empty Repo" / "references").mkdir(parents=True)
        roots_file.write_text("# self\n..\n# none yet\n../../Empty Repo\n", encoding="utf-8")
        assert main(argv) == 0 and out.read_text().count("[upstream]") == 1
        roots_file.write_text("# self\n..\n# same repo twice\n../../Index Repo\n", encoding="utf-8")
        assert main(argv) == 0 and out.read_text().count("[upstream]") == 1
        stray = base / "Elsewhere" / "CATALOG.md"
        assert main(["--roots-file", str(roots_file), "--output", str(stray)]) == 1
        assert not stray.exists(), "a catalog outside the declaring repo must not be written"
        prior = out.read_text()
        roots_file.write_text("# self\n..\n# typo\n../../Gone Repo\n", encoding="utf-8")
        assert main(argv) == 1 and out.read_text() == prior, "missing root must not rewrite"
        return 7


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _selfcheck_worktree_invariance() -> int:
    """The same commit builds the same catalog from a linked worktree."""
    with tempfile.TemporaryDirectory(prefix="catalog worktree ") as td:
        base = Path(td)
        index, other = base / "Index Repo", base / "Other Repo"
        _write_dossier(index / "references" / "own.md", reference_relevance="core")
        _write_dossier(other / "docs" / "research" / "other.md")
        roots_file = index / "references" / "CATALOG.roots"
        roots_file.write_text("# self\n..\n# sibling\n../../Other Repo\n", encoding="utf-8")
        _git(index, "init", "-q", "-b", "main")
        _git(index, "config", "user.email", "selfcheck@example.test")
        _git(index, "config", "user.name", "Selfcheck")
        _git(index, "add", "-A")
        _git(index, "commit", "-qm", "fixture")
        out = index / "references" / "CATALOG.md"
        assert main(["--roots-file", str(roots_file), "--output", str(out)]) == 0
        expected = out.read_text()
        assert "../../Other%20Repo/" in expected, expected
        linked = index / ".claude" / "worktrees" / "wt"
        _git(index, "worktree", "add", "-q", "--detach", str(linked), "HEAD")
        linked_out = linked / "references" / "CATALOG.md"
        argv = ["--roots-file", str(linked / "references" / "CATALOG.roots"),
                "--output", str(linked_out)]
        assert main(argv) == 0, "a sibling must not be looked for inside .claude/worktrees"
        assert linked_out.read_text() == expected, "a worktree must emit the same catalog"
        return 2


def _write_v2(path: Path, *, spine: bool = True, drop: str | None = None, **overrides: object) -> None:
    """Fixture for a schema_version 2 dossier, with a switch to omit one spine heading.

    `drop` exists so a test can prove the gate catches a *single* missing section rather than only
    an obviously empty body: a dossier that is 11/12 complete is the realistic failure, and a gate
    that only catches the empty case would pass it.
    """
    data: dict[str, object] = {
        "title": path.stem,
        "description": f"Study of {path.stem}",
        "catalog": True,
        "schema_version": 2,
        "source_type": "article",
        "source_url": f"https://example.test/v2/{path.stem}",
        "source_version": "v1",
        "analyzed_at": "2026-09-09",
        "last_verified_at": "2026-09-09",
        "reference_depth": "study",
        "reference_relevance": "adjacent",
        "reference_status": "verified",
        "serves": ["polaris"],
        "domains": ["wiki"],
        "aliases": [path.stem],
        "capabilities": ["retrieval"],
    }
    data.update(overrides)
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, list):
            lines.append(f"{key}: [{', '.join(map(str, value))}]")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.extend(["", "# Reference", ""])
    if spine:
        for heading in SPINE_HEADINGS:
            if heading == drop:
                continue
            lines.extend([heading, "Content.", ""])
    for heading in BODY_HEADINGS:
        lines.extend([heading, "Verdict.", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _rejects(path: Path, root: Path, needle: str) -> None:
    meta = parse_frontmatter(path)
    try:
        validate(path, meta, root)
    except CatalogError as exc:
        assert needle in str(exc), f"expected {needle!r} in {exc}"
        return
    raise AssertionError(f"{path.name}: expected rejection containing {needle!r}")


def _selfcheck_schema_v2() -> int:
    """Every branch introduced by schema_version 2, including the ones that must stay permissive.

    A gate is only worth its cost if it rejects the near-miss and accepts the legitimate variant;
    testing only the obvious failure proves the error string, not the boundary.
    """
    with tempfile.TemporaryDirectory(prefix="reference v2 ") as td:
        root = Path(td) / "Repo"
        refs = root / "references"
        target = refs / "linked.md"
        _write_dossier(target)

        # 1. legacy dossiers are untouched by the new rules
        legacy = refs / "legacy.md"
        _write_dossier(legacy)
        validate(legacy, parse_frontmatter(legacy), root)

        # 2-3. source_type is mandatory and closed at v2
        bad_type = refs / "bad-type.md"
        _write_v2(bad_type, source_type="podcast", related=["[[linked]]"])
        _rejects(bad_type, root, "source_type")
        no_type = refs / "no-type.md"
        _write_v2(no_type, related=["[[linked]]"])
        text = no_type.read_text().replace("source_type: article\n", "")
        no_type.write_text(text, encoding="utf-8")
        _rejects(no_type, root, "source_type")

        # 4. a note stays exempt from the spine, which is why the exemption is safe to keep
        note = refs / "note.md"
        _write_v2(note, reference_depth="note", spine=False, related=["[[linked]]"])
        validate(note, parse_frontmatter(note), root)

        # 5. one missing section out of twelve is still a rejection
        partial = refs / "partial.md"
        _write_v2(partial, drop="## Dati e numeri citati", related=["[[linked]]"])
        _rejects(partial, root, "Dati e numeri citati")

        # 6. an isolated dossier is a file, not knowledge
        lonely = refs / "lonely.md"
        _write_v2(lonely)
        _rejects(lonely, root, "related link")

        # 7. a link that looks like a connection but resolves nowhere is worse than no link
        dangling = refs / "dangling.md"
        _write_v2(dangling, related=["[[does-not-exist]]"])
        _rejects(dangling, root, "do not resolve")

        # 8-9. both the way a human writes a link and the way a path is written must resolve
        by_stem = refs / "by-stem.md"
        _write_v2(by_stem, related=["[[linked]]"])
        validate(by_stem, parse_frontmatter(by_stem), root)
        by_path = refs / "by-path.md"
        _write_v2(by_path, related=["[[references/linked]]"])
        validate(by_path, parse_frontmatter(by_path), root)

        # 10. deep is held to the same bar as study, not a laxer one
        deep = refs / "deep.md"
        _write_v2(deep, reference_depth="deep", drop="## Actionable", related=["[[linked]]"])
        _rejects(deep, root, "Actionable")

        # 11. without a root the link check cannot run, and must not invent a verdict
        rootless = refs / "rootless.md"
        _write_v2(rootless, related=["[[does-not-exist]]"])
        validate(rootless, parse_frontmatter(rootless), None)
        return 11


def selfcheck() -> int:
    checks = _selfcheck_roots_file() + _selfcheck_worktree_invariance() + _selfcheck_schema_v2()
    with tempfile.TemporaryDirectory(prefix="reference catalog ") as td:
        base = Path(td)
        a, b = base / "Repo A", base / "Repo B"
        _write_dossier(
            a / "references" / "note.md",
            reference_depth="note",
            reference_relevance="core",
        )
        _write_dossier(
            a / "references" / "study.md",
            reference_depth="study",
            reference_relevance="adjacent",
        )
        _write_dossier(
            b / "docs" / "research" / "deep.md",
            reference_depth="deep",
            reference_relevance="watch",
        )
        ignored = a / "references" / "ignored.md"
        ignored.write_text("---\ntitle: ignored\n---\n", encoding="utf-8")
        empty = a / "references" / "empty.md"
        empty.write_text("---\n---\n\n# Empty\n", encoding="utf-8")
        malformed = a / "references" / "malformed.md"
        malformed.write_text("---\ncatalog: true\n", encoding="utf-8")
        try:
            parse_frontmatter(malformed)
            raise AssertionError("unterminated frontmatter passed")
        except CatalogError as exc:
            assert "unterminated frontmatter" in str(exc)
        malformed.unlink()
        checks += 1
        # A multi-line bracketed list (`[` on its own line, one item per line,
        # closing `]` on its own line) must parse the same as an inline `[a, b]`
        # list. Real dossiers use this style for long `capabilities` lists;
        # dropping it silently emptied the field and failed the required-field
        # check with a misleading "missing capabilities" error.
        multiline = a / "references" / "multiline-bracket.md"
        multiline.write_text(
            "---\ncapabilities:\n  [\n    first item,\n    second item,\n  ]\n---\n",
            encoding="utf-8",
        )
        assert parse_frontmatter(multiline)["capabilities"] == ["first item", "second item"]
        multiline.unlink()
        checks += 1
        out = base / "Index Repo" / "references" / "CATALOG.md"
        assert build([a, b], out) == 0 and out.read_text().count("[upstream]") == 3
        checks += 1
        assert not out.read_text().endswith("\n\n")
        checks += 1
        encoded = next(line for line in out.read_text().splitlines() if "note.md" in line).split("](", 1)[1].split(")", 1)[0]
        assert (out.parent / unquote(encoded)).resolve().exists()
        checks += 1
        _write_dossier(b / "references" / "duplicate.md", source_url="https://example.test/note/")
        prior = out.read_text()
        try:
            build([a, b], out)
            raise AssertionError("duplicate source_url passed")
        except CatalogError as exc:
            assert "duplicate source ownership" in str(exc) and "note.md" in str(exc) and "duplicate.md" in str(exc)
            assert out.read_text() == prior
        checks += 1
        (b / "references" / "duplicate.md").unlink()
        for missing in ("source_version", "last_verified_at"):
            bad = b / "references" / f"missing-{missing}.md"
            _write_dossier(bad, **{missing: ""})
            try:
                collect([a, b])
                raise AssertionError(f"missing {missing} passed")
            except CatalogError as exc:
                assert missing in str(exc)
            bad.unlink()
            checks += 1
        bad_rel = b / "references" / "bad-relevance.md"
        _write_dossier(bad_rel, reference_relevance="important")
        try:
            collect([a, b])
            raise AssertionError("unknown relevance passed")
        except CatalogError as exc:
            assert "invalid reference_relevance" in str(exc)
        checks += 1
        bad_rel.unlink()
        bad_body = b / "references" / "bad-body.md"
        _write_dossier(bad_body)
        bad_body.write_text(
            bad_body.read_text().replace("## Promotion status", "## Missing promotion"),
            encoding="utf-8",
        )
        try:
            collect([a, b])
            raise AssertionError("missing required body heading passed")
        except CatalogError as exc:
            assert "missing body headings" in str(exc) and "Promotion status" in str(exc)
        checks += 1
        bad_body.unlink()
        assert len(collect([a, b])) == 3 and ignored.exists() and empty.exists()
        checks += 1
        legacy = a / "references" / "legacy.md"
        legacy.write_text(
            "---\ntitle: legacy\nsource: https://example.test/legacy\n---\n",
            encoding="utf-8",
        )
        assert find_source_claims([a, b], "https://example.test/legacy/") == [
            (legacy.resolve(), False)
        ]
        checks += 1
        # A legacy reference note that declares its source as `url:` must still be
        # found. 38 real dossiers use that key (every donor-family analysis and
        # every transcript); missing them makes the dedup gate answer NONE for a
        # source we already own, which is the duplicate this tool exists to block.
        legacy_url = a / "references" / "legacy-url.md"
        legacy_url.write_text(
            "---\ntitle: legacy url key\nurl: https://example.test/legacy-url\n---\n",
            encoding="utf-8",
        )
        assert find_source_claims([a, b], "https://example.test/legacy-url") == [
            (legacy_url.resolve(), False)
        ]
        checks += 1
        legacy_url.unlink()
        _write_dossier(b / "references" / "legacy-copy.md", source_url="https://example.test/legacy")
        assert lookup([a, b], "https://example.test/legacy") == 2
        checks += 1
    assert checks >= 9
    print(f"SELFCHECK OK — {checks} adversarial assertions")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, default=[],
                        help="override the declared roots file (repeatable)")
    parser.add_argument("--roots-file", type=Path, default=ROOTS_FILE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--lookup")
    parser.add_argument("--selfcheck", action="store_true")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if not args.lookup and not args.output:
        parser.error("--output is required (or --lookup <url>)")
    try:
        roots = resolve_roots(args.root, args.roots_file)
        if args.lookup:
            return lookup(roots, args.lookup)
        return build(roots, args.output, args.roots_file.parent.parent.resolve())
    except CatalogError as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
