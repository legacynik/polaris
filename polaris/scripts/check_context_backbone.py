#!/usr/bin/env python3
"""Validate Polaris live documents, scoped Decisions, and their sealed manifest."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any


LIVE_DOCS = {
    "CONTEXT.md": "context",
    "ARCHITECTURE.md": "architecture",
    "DOMAIN.md": "domain",
}
DOC_REQUIRED = {
    "schema_version",
    "document_type",
    "status",
    "owner",
    "workspace",
    "repo",
    "snapshot_ref",
    "snapshot_scope",
    "review_trigger",
}
DECISION_REQUIRED = {
    "schema_version",
    "decision_id",
    "decision_key",
    "title",
    "kind",
    "status",
    "owner",
    "decided_at",
    "workspace",
    "repos",
    "governs",
    "supersedes",
    "superseded_by",
    "source_ref",
    "evidence",
    "enforcement",
    "call_sites",
    "prerequisites",
    "closure_check",
    "review_trigger",
    "scope_ref",
}
MODULE_REQUIRED = {
    "schema_version",
    "module_id",
    "status",
    "owner",
    "canonical_prd",
    "active_work",
    "default_context",
    "context_seal",
    "required_requirement_ids",
    "active_plan",
    "active_validation",
    "external_contracts",
    "history_excluded_by_default",
    "review_trigger",
}
SOURCE_REF = re.compile(r"git:[0-9a-f]{40}\Z")
SCOPE_REF = re.compile(r"scope-sha256:[0-9a-f]{64}\Z")
AUTHORITY_BASENAMES = {
    "CONTEXT.md",
    "ARCHITECTURE.md",
    "DOMAIN.md",
    "VISION.md",
    "POLARIS.md",
    "POLARIS-VISION.md",
    "POLARIS-BOARD.md",
}
AUDIT_TREE_DIRS = {"plans", "memo", "wiki", ".wiki", "audit", "references", "adr"}
AUDIT_EXCLUDED_DIRS = {".git", ".omx", "node_modules", "__pycache__", ".venv", "venv"}


class ContractError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _json_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode()).hexdigest()


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _source_bytes(root: Path, path: Path, at_head: bool = False) -> bytes:
    """The file as the chosen tree sees it.

    #199: emission must read ONLY committed content. Parsing and hashing go
    through this one door so they always read the SAME bytes — hashing at HEAD
    while parsing from disk would seal a claim about a version nobody read.
    """
    if not at_head or not (root / ".git").exists():
        return path.read_bytes()
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    blob = subprocess.run(
        ["git", "show", f"HEAD:{relative}"], cwd=root, capture_output=True, check=False
    )
    if blob.returncode != 0:
        raise ContractError("HEAD_UNREADABLE", relative)
    return blob.stdout


def _source_hash(root: Path, path: Path, at_head: bool = False) -> str:
    return sha256(_source_bytes(root, path, at_head)).hexdigest()


def _sources_at(root: Path, relative: str, at_head: bool = False) -> list[Path]:
    """The files under a directory, as the chosen tree sees them.

    Sealing file CONTENT at HEAD is not enough while the LIST of records is
    globbed off the disk: another panel's untracked draft would still decide
    the outcome, which is #199 in another shape.
    """
    if at_head and (root / ".git").exists():
        return [root / name for name, _, _ in _head_entries(root, [relative])]
    return sorted(path for path in (root / relative).rglob("*") if path.is_file())


def _head_entries(root: Path, scope: list[str]) -> list[tuple[str, str, str]]:
    """(path, blob oid, mode) for every committed file under the scope."""
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "HEAD", "--", *scope],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if listing.returncode != 0:
        detail = listing.stderr.strip()[:200] or "git ls-tree HEAD failed"
        raise ContractError("HEAD_UNREADABLE", detail)
    rows: list[tuple[str, str, str]] = []
    for row in listing.stdout.split("\0"):
        if not row:
            continue
        meta, name = row.split("\t", 1)
        fields = meta.split(" ")
        if fields[1] == "blob" and "__pycache__" not in name.split("/"):
            rows.append((name, fields[2], fields[0]))
    return rows


def _head_link_hash(root: Path, name: str, oid: str) -> str | None:
    """Follow a committed symlink the way the working tree does.

    git stores the target string; the working tree hashes the followed content.
    Hashing the string here would make the two seals disagree forever on a
    clean tree (#199 FAIL-3). None when the target is not committed, which is
    the working tree's own behaviour for a broken link: skip it.
    """
    blob = subprocess.run(
        ["git", "cat-file", "blob", oid], cwd=root, capture_output=True, check=False
    )
    if blob.returncode != 0:
        raise ContractError("HEAD_UNREADABLE", name)
    target = Path(os.path.normpath((root / name).parent / blob.stdout.decode().strip()))
    try:
        _safe_path(root, str(target.relative_to(root)))
    except ValueError as exc:
        raise ContractError("PATH_OUTSIDE_ROOT", name) from exc
    kind = subprocess.run(
        ["git", "cat-file", "-t", f"HEAD:{target.relative_to(root).as_posix()}"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if kind.stdout.strip() != "blob":
        # A directory symlink, or a target absent from HEAD. The working tree
        # skips both (`is_file()` is False), so the HEAD seal must skip them too
        # or the two disagree on a byte-clean tree (#199 r2 FAIL-A).
        return None
    try:
        return sha256(_source_bytes(root, target, True)).hexdigest()
    except ContractError:
        return None


def _split_batch(stream: bytes, expected: int) -> list[str]:
    """sha256 each payload of a `git cat-file --batch` response, in order."""
    hashes: list[str] = []
    cursor = 0
    for _ in range(expected):
        end = stream.index(b"\n", cursor)
        header = stream[cursor:end].split(b" ")
        if len(header) != 3:
            raise ContractError(
                "HEAD_UNREADABLE", stream[cursor:end].decode("utf-8", "replace")[:80]
            )
        start = end + 1
        size = int(header[2])
        hashes.append(sha256(stream[start:start + size]).hexdigest())
        cursor = start + size + 1
    return hashes


def _blob_hashes(root: Path, oids: list[str]) -> list[str]:
    """One `git cat-file --batch` for the whole scope.

    A `git show` per file costs seconds here: the Decisions govern ~1200 file
    slots on this repository, and emission recomputes the seal for each one.
    """
    if not oids:
        return []
    proc = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=root,
        input="\n".join(oids).encode() + b"\n", capture_output=True, check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()[:200]
        raise ContractError("HEAD_UNREADABLE", detail or "git cat-file failed")
    return _split_batch(proc.stdout, len(oids))


def _scope_ref_at_head(root: Path, scope: list[str]) -> str:
    """Seal the committed content of the governed scope.

    Same hash FORM as the working-tree seal — sha256 of the file bytes, never the
    git blob oid — so a seal stored by `--reseal` on a clean tree matches in both
    modes. HEAD is the only view a shared checkout and CI see identically, so
    emission reads it and another panel's uncommitted work cannot block the pack.
    """
    entries = _head_entries(root, scope)
    plain = [item for item in entries if item[2] != "120000"]
    hashes = _blob_hashes(root, [oid for _, oid, _ in plain])
    sealed = dict(zip((name for name, _, _ in plain), hashes))
    for name, oid, _ in (item for item in entries if item[2] == "120000"):
        followed = _head_link_hash(root, name, oid)
        if followed is not None:
            sealed[name] = followed
    if not sealed:
        raise ContractError("SCOPE_PATH_MISSING", ",".join(scope))
    return f"scope-sha256:{_json_hash(sorted(sealed.items()))}"


def _head_commit(root: Path) -> str | None:
    """The commit the HEAD-mode seals refer to; None when there is no git."""
    if not (root / ".git").exists():
        return None
    found = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    return found.stdout.strip() if found.returncode == 0 else None


def _frontmatter_optional(path: Path) -> dict[str, Any]:
    try:
        return _frontmatter(path)
    except (ContractError, OSError, UnicodeDecodeError):
        return {}


def _is_authority_candidate(relative: Path) -> bool:
    parts = relative.parts
    name = relative.name
    if not parts:
        return False
    if parts[0] == ".worktrees":
        return name in AUTHORITY_BASENAMES
    if len(parts) == 1:
        return name.endswith(".md") or name == "decisions.md.new"
    if parts[0] in AUDIT_TREE_DIRS:
        return name.endswith(".md") or (
            parts[0] == ".wiki" and name == ".manifest.json"
        )
    if parts[0] == "decisions":
        return name.endswith(".md") or name == "manifest.json"
    if parts[0] in {"hand", "sweep"}:
        return name.endswith(".md")
    if parts[:2] == ("docs", "architecture"):
        return name.endswith(".md")
    if parts[0] == "skills-suite":
        return name in AUTHORITY_BASENAMES
    return False


def _authority_candidates(root: Path) -> list[Path]:
    paths: list[Path] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root)
        dirs[:] = sorted(
            directory
            for directory in dirs
            if directory not in AUDIT_EXCLUDED_DIRS
            and not (
                relative_dir.parts
                and relative_dir.parts[0] not in {".worktrees"}
                and directory.startswith(".")
                and directory not in {".wiki", ".worktrees"}
            )
        )
        for name in sorted(files):
            path = current_path / name
            relative = path.relative_to(root)
            if _is_authority_candidate(relative):
                paths.append(path)
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _primary_role(relative: Path) -> tuple[str, str, bool]:
    path = relative.as_posix()
    first = relative.parts[0]
    if first == ".worktrees":
        return "derived", "explicit worktree scope", True
    if path in LIVE_DOCS:
        return "technical-authority", path, False
    if path in {"POLARIS-VISION.md", "POLARIS-BOARD.md", "POLARIS.md", "CLAUDE.md"}:
        return "company-os-authority", path, False
    if path == "AGENTS.md":
        return "derived", "CLAUDE.md", True
    if first == "decisions" and relative.name.startswith("DEC-"):
        return "decision", "decisions/", False
    if path == "decisions/manifest.json":
        return "derived", "rebuildable decision projection", True
    if path in {"decisions.md", "log.md"} or first == "adr" or relative.parts[:2] == ("docs", "architecture"):
        return "history", "history", True
    if first == "plans" or path == "skills-backlog.md":
        return "plan", "plans/", False
    if first == "memo" or path == "lessons.md":
        return "history", "history", True
    if first in {"wiki", ".wiki"} or path in {"HOME.md", ".wiki-build-log.md"}:
        return "derived", "rebuildable projection", True
    if first in {"audit", "references"} or path in {"README.md", "PROJECT.md", "PRODUCT.md", "DESIGN.md"}:
        return "evidence", "cold retrieval", True
    if first in {"hand", "sweep", "skills-suite"} or path == "skills.allowlist.md":
        return "derived", "component projection", True
    return "conflict", "decision frontier", False


def _source_id(relative: Path, record: dict[str, Any]) -> str:
    declared = record.get("doc_id") or record.get("decision_id")
    return str(declared) if declared else f"source:path:{relative.as_posix()}"


def _declared_authority_role(
    root: Path,
    relative: Path,
    record: dict[str, Any],
    inferred: tuple[str, str, bool],
) -> tuple[str, str, bool, str | None]:
    declared = str(record.get("authority_role", "")).casefold()
    if not declared:
        return *inferred, None
    if inferred[0] not in {"conflict", "derived", "history"}:
        return *inferred, "AUTHORITY_DECLARATION_INVALID"
    if record.get("default_context") not in {False, "false"}:
        return *inferred, "AUTHORITY_DECLARATION_INVALID"

    field = {"projection": "projection_of", "history": "superseded_by"}.get(declared)
    target = record.get(field) if field else None
    if not isinstance(target, str) or not target:
        return *inferred, "AUTHORITY_DECLARATION_INVALID"
    try:
        target_path = _safe_path(root, target)
    except ContractError:
        return *inferred, "AUTHORITY_DECLARATION_INVALID"
    if not target_path.exists():
        return *inferred, "AUTHORITY_DECLARATION_INVALID"
    if declared == "projection":
        if not record.get("component_id") or _primary_role(Path(target))[0] not in {
            "technical-authority",
            "company-os-authority",
        }:
            return *inferred, "AUTHORITY_DECLARATION_INVALID"
        return "derived", target, True, None
    if declared == "history":
        return "history", target, True, None
    return *inferred, "AUTHORITY_DECLARATION_INVALID"


def _heading_role(
    relative: Path, heading: str, primary: str, primary_target: str
) -> tuple[str, str, str]:
    text = heading.casefold()
    if relative.as_posix() not in {"POLARIS-VISION.md", "POLARIS-BOARD.md", "POLARIS.md"}:
        return primary, primary_target, "primary-document-contract"
    if text.strip() == "plan":
        return "plan", "POLARIS-BOARD.md", "heading-exact:plan"
    rules = (
        (("decision", "scelta", "open question", "source of truth"), "decision", "decisions/"),
        (("backlog", "roadmap", "goal", "next", "todo", "piano", "piani", "rollout", "deadline", "priorità", "priority", "go-to-market", "p0"), "plan", "POLARIS-BOARD.md"),
        (("status", "stato", "current", "alert", "capacity", "building", "blocked", "activity", "today"), "state", "POLARIS.md"),
        (("vision", "princip", "north star", "philosoph", "identità", "direction"), "company-os-authority", "POLARIS-VISION.md"),
    )
    for needles, role, target in rules:
        match = next((needle for needle in needles if needle in text), None)
        if match:
            return role, target, f"heading-keyword:{match}"
    defaults = {
        "POLARIS-VISION.md": ("company-os-authority", "POLARIS-VISION.md"),
        "POLARIS-BOARD.md": ("plan", "POLARIS-BOARD.md"),
        "POLARIS.md": ("state", "POLARIS.md"),
    }
    role, target = defaults[relative.as_posix()]
    return role, target, f"document-contract:{relative.as_posix()}"


def _claims(
    path: Path, relative: Path, source_id: str, primary: str, primary_target: str
) -> list[dict[str, Any]]:
    if path.suffix != ".md":
        return [{"claim_id": f"{source_id}#document", "heading": "document", "content_kind": primary, "target": primary_target, "classification_basis": "primary-document-contract"}]
    text = path.read_text(errors="replace")
    headings = re.findall(r"^(#{1,6})\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if primary in {"evidence", "history", "derived"} or not headings:
        headings = [("#", "document")]
    claims: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for marks, heading in headings:
        slug = re.sub(r"[^a-z0-9]+", "-", heading.casefold()).strip("-") or "section"
        seen[slug] = seen.get(slug, 0) + 1
        role, target, basis = _heading_role(relative, heading, primary, primary_target)
        claims.append(
            {
                "claim_id": f"{source_id}#h{len(marks)}:{slug}:{seen[slug]}",
                "heading": heading,
                "content_kind": role,
                "target": target,
                "classification_basis": basis,
            }
        )
    return claims


def _git_head(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _declared_freshness_windows(root: Path) -> list[int]:
    """Every applicable window declared for this repo, deduplicated.

    Hard-coding `last_updated == date.today()` is what turned main red at four
    separate midnights on a file no PR had touched (#246): a rule nobody had
    decided, enforced by a line. Reading only the first matching record would
    repeat the mistake one level up — an alphabetically earlier Decision would
    silently outrank the real one — so every applicable record is collected and
    disagreement is an error, not a race.
    """
    repo = _frontmatter_optional(root / "CONTEXT.md").get("repo")
    found: list[int] = []
    for path in sorted((root / "decisions").glob("DEC-*.md")):
        record = _frontmatter_optional(path)
        days = record.get("freshness_ttl_days")
        if record.get("status") != "accepted" or record.get("superseded_by"):
            continue
        if repo and repo not in (record.get("repos") or [repo]):
            continue
        if isinstance(days, int) and not isinstance(days, bool) and days > 0:
            found.append(days)
    return sorted(set(found))


def _daily_reconciled(
    root: Path, record: dict[str, Any], today: date
) -> tuple[str, str | None]:
    """A dashboard's value is recency, so it is judged by a window, not by a date.

    `today` is a parameter and not a call inside: the verdict has to be
    reproducible from the commit plus a stated instant, which is what the four
    incident replays in test_polaris_freshness_rule.py rest on.
    """
    windows = _declared_freshness_windows(root)
    if not windows:
        return "UNKNOWN", "FRESHNESS_RULE_UNDECLARED"
    if len(windows) > 1:
        return "UNKNOWN", "FRESHNESS_RULE_AMBIGUOUS"
    days = windows[0]
    if not record.get("reconciled_sources"):
        return "STALE", "FRESHNESS_SOURCES_MISSING"
    try:
        seen = date.fromisoformat(str(record.get("last_updated")))
    except ValueError:
        return "STALE", "FRESHNESS_DATE_INVALID"
    age = today - seen
    if age < timedelta() or age > timedelta(days=days):
        return "STALE", "FRESHNESS_TTL_EXPIRED"
    return "CURRENT", None


def _freshness(root: Path, path: Path, record: dict[str, Any], role: str) -> tuple[str, str | None]:
    if path.name == "CLAUDE.md" and role == "company-os-authority":
        return "CURRENT", None
    if path.name == "POLARIS.md" and role == "company-os-authority" and record.get("freshness_model") == "daily-reconciled":
        return _daily_reconciled(root, record, date.today())
    if role == "company-os-authority" and record.get("freshness_model") == "normative":
        required = record.get("status") == "active" and record.get("owner") and record.get("review_trigger")
        return ("CURRENT", None) if required else ("UNKNOWN", "NORMATIVE_CONTRACT_INCOMPLETE")
    if "snapshot_ref" in record and "snapshot_scope" in record:
        try:
            actual = _scope_ref(root, record["snapshot_scope"])
        except ContractError as exc:
            return "UNKNOWN", exc.code
        return ("CURRENT", None) if actual == record["snapshot_ref"] else ("STALE", "SOURCE_REF_STALE")
    if role == "decision":
        value = record.get("source_ref")
        if not isinstance(value, str) or not SOURCE_REF.fullmatch(value):
            return "UNKNOWN", "SOURCE_REF_INVALID"
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{value.removeprefix('git:')}^{{commit}}"],
            cwd=root,
            capture_output=True,
            check=False,
        )
        return ("CURRENT", None) if result.returncode == 0 else ("STALE", "SOURCE_REF_UNKNOWN")
    if role in {"technical-authority", "company-os-authority"}:
        return "UNKNOWN", "FRESHNESS_UNKNOWN"
    return "NOT_APPLICABLE", None


def audit_authorities(root: Path) -> dict[str, Any]:
    root = root.resolve()
    sources: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for name in LIVE_DOCS:
        if not (root / name).is_file():
            findings.append(
                {"code": "LIVE_DOC_MISSING", "source_id": f"source:path:{name}", "blocking": True}
            )
    for path in _authority_candidates(root):
        relative = path.relative_to(root)
        read_error = None
        try:
            path.resolve().relative_to(root)
            content_hash = _file_hash(path)
        except (OSError, ValueError) as exc:
            content_hash = None
            read_error = type(exc).__name__
        record = _frontmatter_optional(path) if path.suffix == ".md" and not read_error else {}
        inferred = _primary_role(relative)
        role, target, excluded, declaration_error = _declared_authority_role(
            root, relative, record, inferred
        )
        source_id = _source_id(relative, record)
        freshness, freshness_cause = (
            ("UNKNOWN", "SOURCE_UNREADABLE")
            if read_error
            else _freshness(root, path, record, role)
        )
        source = {
            "source_id": source_id,
            "path": relative.as_posix(),
            "sha256": content_hash,
            "scope": "worktree" if relative.parts[0] == ".worktrees" else "repo",
            "lifecycle": record.get("status") or record.get("lifecycle") or "undeclared",
            "freshness": freshness,
            "primary_role": role,
            "target": target,
            "declared_authority_role": record.get("authority_role"),
            "default_context_eligible": not excluded
            and (
                role in {"technical-authority", "company-os-authority"}
                or (role == "decision" and record.get("status") == "accepted")
            ),
        }
        sources.append(source)
        source_claims = (
            _claims(path, relative, source_id, role, target)
            if not read_error
            else [{"claim_id": f"{source_id}#document", "heading": "unreadable", "content_kind": "conflict", "target": "decision frontier", "classification_basis": f"read-error:{read_error}"}]
        )
        claims.extend(source_claims)
        if read_error:
            findings.append({"code": "SOURCE_UNREADABLE", "source_id": source_id, "blocking": True})
        if declaration_error:
            findings.append({"code": declaration_error, "source_id": source_id, "blocking": True})
        if role == "conflict":
            findings.append({"code": "UNCLASSIFIED_SOURCE", "source_id": source_id, "blocking": True})
        if freshness_cause and not read_error and role in {"technical-authority", "company-os-authority", "decision"}:
            findings.append({"code": freshness_cause, "source_id": source_id, "blocking": True})
        declared_shadow_role = str(record.get("authority_role", "")).casefold()
        if relative.name in AUTHORITY_BASENAMES and relative.parts[0] not in {".worktrees"} and role in {"derived", "history"} and not (
            declared_shadow_role in {"projection", "history"} and declaration_error is None
        ):
            findings.append({"code": "AUTHORITY_SHADOW", "source_id": source_id, "blocking": True})
        if relative.parts[0] == ".worktrees":
            findings.append({"code": "WORKTREE_SOURCE_EXCLUDED", "source_id": source_id, "blocking": False})
        elif role in {"derived", "history"} and str(record.get("status", "")).casefold() == "active":
            findings.append({"code": "NONLIVE_STATUS_IGNORED", "source_id": source_id, "blocking": False})
        claim_roles = {claim["content_kind"] for claim in source_claims}
        if len(claim_roles) > 1:
            findings.append({"code": "MIXED_DOCUMENT", "source_id": source_id, "blocking": False, "roles": sorted(claim_roles)})
        expected_claim_role = {
            "POLARIS-VISION.md": "company-os-authority",
            "POLARIS-BOARD.md": "plan",
            "POLARIS.md": "state",
        }.get(relative.as_posix())
        if expected_claim_role:
            for claim in source_claims:
                if claim["content_kind"] != expected_claim_role:
                    findings.append(
                        {
                            "code": "TYPE_MISPLACED",
                            "source_id": source_id,
                            "claim_id": claim["claim_id"],
                            "actual": claim["content_kind"],
                            "required_target": claim["target"],
                            "blocking": True,
                        }
                    )

    source_ids = [source["source_id"] for source in sources]
    duplicate_ids = sorted({item for item in source_ids if source_ids.count(item) > 1})
    for source_id in duplicate_ids:
        findings.append({"code": "SOURCE_ID_DUPLICATE", "source_id": source_id, "blocking": True})
    coverage: dict[str, int | str] = {
        "discovered_sources": len(sources),
        "governed_sources": sum(source["scope"] == "repo" for source in sources),
        "excluded_worktree_sources": sum(source["scope"] == "worktree" for source in sources),
        "classified_sources": sum(bool(source["primary_role"]) for source in sources),
        "discovered_claims": len(claims),
        "classified_claims": sum(bool(claim["content_kind"] and claim["target"]) for claim in claims),
    }
    coverage["status"] = (
        "COMPLETE"
        if coverage["discovered_sources"] == coverage["classified_sources"]
        and coverage["discovered_claims"] == coverage["classified_claims"]
        else "PARTIAL"
    )
    manifest_payload = {"sources": sources, "claims": claims}
    blocking = [finding for finding in findings if finding["blocking"]]
    verdict = "BLOCK" if blocking or coverage["status"] != "COMPLETE" else "READY"
    execution_sources = [
        source for source in sources if source["default_context_eligible"]
    ]
    candidate_execution_hash = _json_hash(execution_sources)
    result = {
        "schema_version": 1,
        "kind": "AUTHORITY_AUDIT",
        "snapshot_ref": _git_head(root),
        "scope": {
            "candidate_roots": sorted(AUDIT_TREE_DIRS | {"decisions", "docs/architecture", "hand", "sweep", "skills-suite", "repository-root", ".worktrees/**/authority-shaped"}),
            "excluded_runtime_dirs": sorted(AUDIT_EXCLUDED_DIRS),
            "worktree_sources_default_excluded": True,
        },
        "coverage": coverage,
        "sources": sources,
        "claims": claims,
        "findings": findings,
        "source_manifest_hash": _json_hash([source for source in sources if source["scope"] == "repo"]),
        "inventory_hash": _json_hash(sources),
        "candidate_execution_source_hash": candidate_execution_hash,
        "execution_source_seal": (
            f"source-sha256:{candidate_execution_hash}" if verdict == "READY" else None
        ),
        "audit_hash": _json_hash(manifest_payload | {"findings": findings}),
        "verdict": verdict,
    }
    return result


def _safe_path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ContractError("PORTABILITY_LEAK", relative)
    if ".." in candidate.parts:
        raise ContractError("PATH_OUTSIDE_ROOT", relative)
    target = root / candidate
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ContractError("PATH_OUTSIDE_ROOT", relative) from exc
    return target


def _scope_ref(root: Path, paths: list[str], at_head: bool = False) -> str:
    """Hash the governed sources.

    Default: the working tree. The gate answers "is my context true right now",
    so a governed source that moved must make it stale, committed or not. With
    ``at_head``: the committed tree, which is what emission seals against — see
    ``_scope_ref_at_head``. A root with no ``.git`` has no HEAD to read, so it
    degrades to the working tree, the same convention ``_validate_git_ref``
    already uses; inside a repository a failing git stays fail-closed.
    """
    if (
        not isinstance(paths, list)
        or not paths
        or not all(isinstance(path, str) and path for path in paths)
    ):
        raise ContractError("SCOPE_PATHS_INVALID", repr(paths))
    scope = sorted(set(paths))
    targets: list[Path] = []
    for relative in scope:
        target = _safe_path(root, relative)
        if not target.exists() and not at_head:
            raise ContractError("SCOPE_PATH_MISSING", relative)
        targets.append(target)
    if at_head and (root / ".git").exists():
        return _scope_ref_at_head(root, scope)
    visible = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            *scope,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    candidates = (
        [root / relative for relative in visible.stdout.split("\0") if relative]
        if visible.returncode == 0
        else [
            item
            for target in targets
            for item in ([target] if target.is_file() else sorted(target.rglob("*")))
        ]
    )
    entries: list[tuple[str, str]] = []
    for item in candidates:
        try:
            item.resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise ContractError(
                "PATH_OUTSIDE_ROOT", str(item.relative_to(root))
            ) from exc
        if not item.is_file() or "__pycache__" in item.parts:
            continue
        entries.append((str(item.relative_to(root)), _file_hash(item)))
    return f"scope-sha256:{_json_hash(sorted(entries))}"


def _frontmatter(path: Path) -> dict[str, Any]:
    return _parse_frontmatter(path.read_text(), path)


def _frontmatter_at(root: Path, path: Path, at_head: bool = False) -> dict[str, Any]:
    return _parse_frontmatter(_source_bytes(root, path, at_head).decode(), path)


def _parse_frontmatter(text: str, path: Path) -> dict[str, Any]:
    if not text.startswith("---\n"):
        raise ContractError("FRONTMATTER_MISSING", str(path))
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ContractError("FRONTMATTER_INVALID", str(path))
    raw = text[4:end].strip()
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractError("FRONTMATTER_INVALID", f"{path}: {exc}") from exc

    result: dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith(("[", "{")):
            try:
                result[key.strip()] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
        result[key.strip()] = int(value) if value.isdigit() else value.strip('"')
    return result


def _require(record: dict[str, Any], required: set[str], path: Path) -> None:
    missing = sorted(required - record.keys())
    if missing:
        raise ContractError("REQUIRED_FIELD_MISSING", f"{path}: {','.join(missing)}")


def _validate_git_ref(value: Any, path: Path, root: Path) -> None:
    if not isinstance(value, str) or not SOURCE_REF.fullmatch(value):
        raise ContractError("SOURCE_REF_INVALID", f"{path}: {value}")
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{value.removeprefix('git:')}^{{commit}}"],
            cwd=root,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise ContractError("SOURCE_REF_UNKNOWN", f"{path}: {value}")


def _validate_scope_ref(record: dict[str, Any], path: Path, actual: str) -> None:
    claimed = record["snapshot_ref"]
    if not isinstance(claimed, str) or not SCOPE_REF.fullmatch(claimed):
        raise ContractError("SOURCE_REF_INVALID", f"{path}: {claimed}")
    if claimed != actual:
        raise ContractError("SOURCE_REF_STALE", f"{path}: {claimed}!={actual}")


def _require_scope_ref(value: Any, path: Path) -> str:
    if not isinstance(value, str) or not SCOPE_REF.fullmatch(value):
        raise ContractError("DECISION_SCOPE_REF_INVALID", f"{path}: {value}")
    return value


def _validate_module_dossiers(root: Path, at_head: bool = False) -> list[dict[str, Any]]:
    modules_root = root / "docs" / "modules"
    if not modules_root.exists():
        return []
    if not (modules_root / "README.md").is_file():
        raise ContractError("MODULE_GUIDE_MISSING", "docs/modules/README.md")

    modules: list[dict[str, Any]] = []
    ids: set[str] = set()
    relatives = [
        path.relative_to(modules_root)
        for path in _sources_at(root, "docs/modules", at_head)
    ]
    for module_root in sorted(
        {modules_root / item.parts[0] for item in relatives if len(item.parts) > 1}
    ):
        if not (module_root / "CHANGELOG.md").is_file():
            raise ContractError(
                "MODULE_CHANGELOG_MISSING", str(module_root.relative_to(root))
            )
        manifest_path = module_root / "module-context.json"
        if not manifest_path.is_file():
            raise ContractError(
                "MODULE_MANIFEST_MISSING", str(module_root.relative_to(root))
            )
        try:
            record = json.loads(_source_bytes(root, manifest_path, at_head).decode())
        except json.JSONDecodeError as exc:
            raise ContractError("MODULE_MANIFEST_INVALID", f"{manifest_path}: {exc}") from exc
        _require(record, MODULE_REQUIRED, manifest_path)

        module_id = record["module_id"]
        if record["schema_version"] != 1:
            raise ContractError("MODULE_SCHEMA_INVALID", str(record["schema_version"]))
        if not isinstance(module_id, str) or not module_id or module_id in ids:
            raise ContractError("MODULE_ID_INVALID", repr(module_id))
        ids.add(module_id)
        if not isinstance(record["owner"], str) or not record["owner"]:
            raise ContractError("MODULE_OWNER_INVALID", module_id)
        if not isinstance(record["status"], str) or record["status"] not in {
            "active",
            "paused",
            "complete",
            "archived",
        }:
            raise ContractError("MODULE_STATUS_INVALID", f"{module_id}: {record['status']}")
        if record["history_excluded_by_default"] is not True:
            raise ContractError("MODULE_HISTORY_DEFAULT_INVALID", module_id)
        if not isinstance(record["review_trigger"], list) or not record["review_trigger"] or not all(
            isinstance(item, str) and item for item in record["review_trigger"]
        ):
            raise ContractError("REVIEW_TRIGGER_EMPTY", str(manifest_path))
        if (
            not isinstance(record["active_work"], list)
            or (record["status"] == "active" and not record["active_work"])
            or not all(
                isinstance(item, str) and item.startswith("issue:")
                for item in record["active_work"]
            )
        ):
            raise ContractError("MODULE_ACTIVE_WORK_INVALID", module_id)

        relative_module = module_root.relative_to(root)

        def module_path(value: Any, field: str, *, optional: bool = False) -> Path | None:
            if optional and value is None:
                return None
            if not isinstance(value, str) or not value:
                raise ContractError("MODULE_PATH_INVALID", f"{module_id}: {field}")
            target = _safe_path(root, value)
            try:
                target.resolve().relative_to(module_root.resolve())
            except ValueError as exc:
                raise ContractError("MODULE_PATH_OUTSIDE_DOSSIER", f"{module_id}: {value}") from exc
            if not target.is_file():
                raise ContractError("MODULE_PATH_MISSING", f"{module_id}: {value}")
            return target

        prd_path = module_path(record["canonical_prd"], "canonical_prd")
        assert prd_path is not None
        expected_prd_name = f"{module_root.name}.md"
        if prd_path.name != expected_prd_name:
            raise ContractError(
                "MODULE_PRD_NAME_INVALID",
                f"{module_id}: {prd_path.name}!={expected_prd_name}",
            )
        prd = _frontmatter_at(root, prd_path, at_head)
        if (
            prd.get("document_type") != "prd"
            or prd.get("authority_role") != "canonical-spec"
            or prd.get("status") != "final"
            or prd.get("module_id") != module_id
        ):
            raise ContractError("MODULE_PRD_INVALID", str(prd_path.relative_to(root)))

        default_context = record["default_context"]
        if (
            not isinstance(default_context, list)
            or not default_context
            or not all(isinstance(item, str) and item for item in default_context)
            or len(default_context) != len(set(default_context))
        ):
            raise ContractError("MODULE_DEFAULT_CONTEXT_INVALID", module_id)
        default_paths = [module_path(item, "default_context") for item in default_context]
        required_default = {
            module_root / "README.md",
            prd_path,
        }
        if not required_default.issubset(set(default_paths)):
            raise ContractError("MODULE_DEFAULT_CONTEXT_INCOMPLETE", module_id)

        active_plan = module_path(record["active_plan"], "active_plan", optional=True)
        # I19 progressive disclosure: the active set is the map, the canonical document
        # and the active plan. A `specs/` or `archive/` file added here is a folder
        # smuggled into every ContextPack, so it blocks instead of widening the pack.
        beyond = set(default_paths) - required_default - {active_plan}
        if beyond:
            raise ContractError(
                "MODULE_DEFAULT_CONTEXT_BEYOND_MAP",
                f"{module_id}: " + ",".join(sorted(p.name for p in beyond)),
            )
        if active_plan is not None:
            if active_plan not in default_paths:
                raise ContractError("MODULE_ACTIVE_PLAN_NOT_LOADED", module_id)
            try:
                active_plan.resolve().relative_to((module_root / "plans").resolve())
            except ValueError as exc:
                raise ContractError("MODULE_ACTIVE_PLAN_PATH_INVALID", module_id) from exc
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-.+-plan\.md", active_plan.name):
                raise ContractError(
                    "MODULE_ACTIVE_PLAN_NAME_INVALID", f"{module_id}: {active_plan.name}"
                )
        active_validation = module_path(
            record["active_validation"], "active_validation", optional=True
        )
        if active_validation is not None:
            try:
                active_validation.resolve().relative_to(
                    (module_root / "validation").resolve()
                )
            except ValueError as exc:
                raise ContractError(
                    "MODULE_ACTIVE_VALIDATION_PATH_INVALID", module_id
                ) from exc
            if not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}-.+\.md", active_validation.name
            ):
                raise ContractError(
                    "MODULE_ACTIVE_VALIDATION_NAME_INVALID",
                    f"{module_id}: {active_validation.name}",
                )

        external = record["external_contracts"]
        if (
            not isinstance(external, list)
            or not external
            or not all(isinstance(item, str) and item for item in external)
            or len(external) != len(set(external))
        ):
            raise ContractError("MODULE_EXTERNAL_CONTRACT_INVALID", module_id)
        for relative in external:
            if not isinstance(relative, str) or not (
                relative in LIVE_DOCS
                or (relative.startswith("decisions/DEC-") and relative.endswith(".md"))
            ):
                raise ContractError("MODULE_EXTERNAL_CONTRACT_INVALID", f"{module_id}: {relative}")
            if not _safe_path(root, relative).is_file():
                raise ContractError("MODULE_PATH_MISSING", f"{module_id}: {relative}")

        expected_ids = record["required_requirement_ids"]
        if (
            not isinstance(expected_ids, list)
            or not expected_ids
            or not all(isinstance(item, str) and item for item in expected_ids)
            or len(expected_ids) != len(set(expected_ids))
        ):
            raise ContractError("MODULE_REQUIREMENT_SET_INVALID", module_id)
        text = _source_bytes(root, prd_path, at_head).decode()
        for requirement_id in expected_ids:
            if len(re.findall(rf"(?m)^### {re.escape(requirement_id)}(?:\s|$)", text)) != 1:
                raise ContractError("MODULE_REQUIREMENT_MISSING", f"{module_id}: {requirement_id}")

        expected_seal = _scope_ref(root, default_context, at_head=at_head)
        if record["context_seal"] != expected_seal:
            raise ContractError(
                "MODULE_CONTEXT_STALE",
                f"{module_id}: {record['context_seal']}!={expected_seal}",
            )
        modules.append(
            {
                "module_id": module_id,
                "path": relative_module.as_posix(),
                "context_seal": expected_seal,
                # The ContextPack resolver consumes these instead of re-reading the
                # manifest: re-reading it from the worktree while this validated HEAD
                # is how an uncommitted edit walks into a sealed pack.
                "default_context": list(default_context),
                "active_work": list(record["active_work"]),
            }
        )
    return modules


def _validate_landing(
    record: dict[str, Any], path: Path, root: Path, governed_paths: list[str]
) -> None:
    call_sites = record["call_sites"]
    prerequisites = record["prerequisites"]
    closure_check = record["closure_check"]
    if not isinstance(call_sites, list) or not all(
        isinstance(item, str) and item for item in call_sites
    ):
        raise ContractError("DECISION_LANDING_INVALID", f"{path}: call_sites")
    if record["status"] == "accepted" and not call_sites:
        raise ContractError("DECISION_LANDING_INVALID", f"{path}: call_sites empty")
    if not isinstance(prerequisites, list) or not all(
        isinstance(item, str) and item for item in prerequisites
    ):
        raise ContractError("DECISION_LANDING_INVALID", f"{path}: prerequisites")
    if not isinstance(closure_check, str) or not closure_check.strip():
        raise ContractError("DECISION_LANDING_INVALID", f"{path}: closure_check")

    governed = [_safe_path(root, item).resolve() for item in governed_paths]
    for relative in call_sites:
        target = _safe_path(root, relative)
        if not target.exists():
            raise ContractError("DECISION_CALL_SITE_MISSING", relative)
        resolved = target.resolve()
        if record["status"] == "accepted" and not any(
            resolved == scope or scope in resolved.parents for scope in governed
        ):
            raise ContractError(
                "DECISION_CALL_SITE_OUTSIDE_SCOPE",
                f"{record['decision_id']}: {relative}",
            )


def _manifest(model: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "workspace": model["workspace"],
        "repo": model["repo"],
        "domain_source": {
            "path": "DOMAIN.md",
            "sha256": model["source_hashes"]["DOMAIN.md"],
        },
        "live_documents": {
            name: model["source_hashes"][name] for name in sorted(LIVE_DOCS)
        },
        "legacy_sources": model["legacy_sources"],
        "decisions": [
            {
                "decision_id": item["record"]["decision_id"],
                "decision_key": item["record"]["decision_key"],
                "status": item["record"]["status"],
                "workspace": item["record"]["workspace"],
                "repos": item["record"]["repos"],
                "governs": item["record"]["governs"],
                "path": item["path"],
                "sha256": model["source_hashes"][item["path"]],
            }
            for item in model["decisions"]
        ],
    }
    payload["manifest_hash"] = _json_hash(payload)
    return payload


def validate(
    root: Path, require_manifest: bool = True, at_head: bool = False
) -> dict[str, Any]:
    """``at_head`` seals the governed scopes against the committed tree.

    The gate leaves it False. Emission sets it so another panel's uncommitted
    work in a shared checkout cannot block a pack for an unchanged commit.
    """
    root = root.resolve()
    docs: dict[str, dict[str, Any]] = {}
    source_hashes: dict[str, str] = {}
    for name, expected_type in LIVE_DOCS.items():
        path = root / name
        if not path.is_file():
            raise ContractError("LIVE_DOC_MISSING", name)
        record = _frontmatter_at(root, path, at_head)
        _require(record, DOC_REQUIRED, path)
        if record["document_type"] != expected_type:
            raise ContractError(
                "DOCUMENT_TYPE_INVALID", f"{name}: {record['document_type']}"
            )
        if record["status"] != "active":
            raise ContractError("LIVE_DOC_NOT_ACTIVE", f"{name}: {record['status']}")
        if (
            not isinstance(record["snapshot_scope"], list)
            or not record["snapshot_scope"]
        ):
            raise ContractError("SNAPSHOT_SCOPE_EMPTY", name)
        if (
            not isinstance(record["review_trigger"], list)
            or not record["review_trigger"]
        ):
            raise ContractError("REVIEW_TRIGGER_EMPTY", name)
        seal = _scope_ref(root, record["snapshot_scope"], at_head=at_head)
        _validate_scope_ref(record, path, seal)
        docs[name] = record
        source_hashes[name] = _source_hash(root, path, at_head)

    identities = {(record["workspace"], record["repo"]) for record in docs.values()}
    if len(identities) != 1 or not all(
        isinstance(value, str) and value for identity in identities for value in identity
    ):
        raise ContractError("SCOPE_CONFLICT", f"live documents: {sorted(identities)}")
    workspace, repo = identities.pop()
    modules = _validate_module_dossiers(root, at_head=at_head)

    domain = docs["DOMAIN.md"]
    domains = {item["domain_id"] for item in domain.get("domains", [])}
    components = {item["component_id"]: item for item in domain.get("components", [])}
    if not domains or not components:
        raise ContractError("DOMAIN_MAP_EMPTY", "DOMAIN.md")
    for component_id, component in components.items():
        unknown = sorted(set(component.get("domains", [])) - domains)
        if unknown:
            raise ContractError(
                "UNKNOWN_DOMAIN", f"{component_id}: {','.join(unknown)}"
            )
        if not component.get("paths"):
            raise ContractError("COMPONENT_PATHS_EMPTY", component_id)
        missing_paths = sorted(
            path for path in component["paths"] if not _safe_path(root, path).exists()
        )
        if missing_paths:
            raise ContractError(
                "COMPONENT_PATH_MISSING", f"{component_id}: {','.join(missing_paths)}"
            )

    decision_dir = root / "decisions"
    decision_paths = [
        path
        for path in _sources_at(root, "decisions", at_head)
        if path.parent == decision_dir and path.name.startswith("DEC-")
        and path.suffix == ".md"
    ]
    if not decision_paths:
        raise ContractError("DECISION_SET_EMPTY", str(decision_dir))
    decisions: list[dict[str, Any]] = []
    legacy_sources: dict[str, str] = {}
    ids: set[str] = set()
    accepted_keys: set[tuple[str, tuple[str, ...], str]] = set()
    for path in decision_paths:
        record = _frontmatter_at(root, path, at_head)
        _require(record, DECISION_REQUIRED, path)
        if record["workspace"] != workspace or repo not in record["repos"]:
            raise ContractError(
                "SCOPE_CONFLICT",
                f"{record['decision_id']}: {record['workspace']}/{record['repos']} != {workspace}/{repo}",
            )
        _validate_git_ref(record["source_ref"], path, root)
        decision_id = record["decision_id"]
        if decision_id in ids:
            raise ContractError("DECISION_ID_DUPLICATE", decision_id)
        ids.add(decision_id)
        governs = record["governs"]
        unknown_domains = sorted(set(governs.get("domains", [])) - domains)
        unknown_components = sorted(
            set(governs.get("components", [])) - set(components)
        )
        if unknown_domains:
            raise ContractError(
                "UNKNOWN_DOMAIN", f"{decision_id}: {','.join(unknown_domains)}"
            )
        if unknown_components:
            raise ContractError(
                "UNKNOWN_COMPONENT", f"{decision_id}: {','.join(unknown_components)}"
            )
        if record["status"] == "accepted":
            legacy_review = record.get("legacy_review")
            legacy_scope = legacy_review.get("scope") if isinstance(legacy_review, dict) else None
            governed_components = set(governs.get("components", []))
            if not isinstance(legacy_scope, list) or set(legacy_scope) != governed_components:
                raise ContractError(
                    "LEGACY_REVIEW_SCOPE_INCOMPLETE",
                    f"{decision_id}: {legacy_scope}!={sorted(governed_components)}",
                )
        governed_paths = [
            path
            for component_id in governs.get("components", [])
            for path in components[component_id]["paths"]
        ]
        _validate_landing(record, path, root, governed_paths)
        actual_scope_ref = _scope_ref(root, governed_paths, at_head=at_head)
        if _require_scope_ref(record["scope_ref"], path) != actual_scope_ref:
            raise ContractError(
                "DECISION_SCOPE_STALE",
                f"{decision_id}: {record['scope_ref']}!={actual_scope_ref}",
            )
        if record["status"] == "accepted":
            key = (
                record["workspace"],
                tuple(sorted(record["repos"])),
                record["decision_key"],
            )
            if key in accepted_keys:
                raise ContractError(
                    "CONTEXT_CONFLICT", "|".join((key[0], *key[1], key[2]))
                )
            accepted_keys.add(key)
        relative = str(path.relative_to(root))
        source_hashes[relative] = _source_hash(root, path, at_head)
        for legacy_path in record.get("legacy_review", {}).get("sources", []):
            target = _safe_path(root, legacy_path)
            if not target.is_file():
                raise ContractError("LEGACY_SOURCE_MISSING", legacy_path)
            source_hashes[legacy_path] = _source_hash(root, target, at_head)
            legacy_sources[legacy_path] = source_hashes[legacy_path]
        decisions.append({"path": relative, "record": record})

    if not accepted_keys:
        raise ContractError("ACCEPTED_DECISION_SET_EMPTY", str(decision_dir))

    by_id = {item["record"]["decision_id"]: item["record"] for item in decisions}
    for item in decisions:
        record = item["record"]
        for old_id in record["supersedes"]:
            if old_id not in ids:
                raise ContractError("SUPERSESSION_TARGET_MISSING", old_id)
            old = by_id[old_id]
            if (
                old["status"] != "superseded"
                or old["superseded_by"] != record["decision_id"]
            ):
                raise ContractError(
                    "SUPERSESSION_NOT_SYMMETRIC", f"{record['decision_id']}->{old_id}"
                )
        if record["superseded_by"] and record["superseded_by"] not in ids:
            raise ContractError("SUPERSESSION_TARGET_MISSING", record["superseded_by"])
        if record["superseded_by"]:
            successor = by_id[record["superseded_by"]]
            if record["decision_id"] not in successor["supersedes"]:
                raise ContractError(
                    "SUPERSESSION_NOT_SYMMETRIC",
                    f"{record['decision_id']}->{record['superseded_by']}",
                )

    accepted_legacy: list[str] = []
    legacy_dir = root / "adr"
    if legacy_dir.is_dir():
        accepted_legacy = [
            str(path.relative_to(root)).removesuffix(".md")
            for path in _sources_at(root, "adr", at_head)
            if path.suffix == ".md"
            if _frontmatter_at(root, path, at_head).get("status") in {"accepted", "active"}
        ]
    for item in decisions:
        record = item["record"]
        if record["status"] != "accepted":
            continue
        for call_site in record["call_sites"]:
            target = _safe_path(root, call_site)
            if not target.is_file() or target.suffix != ".md":
                continue
            text = _source_bytes(root, target, at_head).decode()
            for legacy in accepted_legacy:
                if f"[[{legacy}]]" in text or f"[[{legacy}.md]]" in text:
                    raise ContractError(
                        "LEGACY_AUTHORITY_REFERENCED",
                        f"{record['decision_id']}: {call_site}->{legacy}",
                    )

    model = {
        "root": str(root),
        "workspace": workspace,
        "repo": repo,
        "documents": docs,
        "domains": sorted(domains),
        "components": components,
        "decisions": decisions,
        "legacy_sources": legacy_sources,
        "source_hashes": source_hashes,
        "modules": modules,
    }
    expected_manifest = _manifest(model)
    if require_manifest:
        manifest_path = decision_dir / "manifest.json"
        if not manifest_path.is_file():
            raise ContractError("DECISION_MANIFEST_MISSING", str(manifest_path))
        try:
            actual_manifest = json.loads(_source_bytes(root, manifest_path, at_head).decode())
        except json.JSONDecodeError as exc:
            raise ContractError("DECISION_MANIFEST_INVALID", str(exc)) from exc
        if actual_manifest != expected_manifest:
            raise ContractError("DECISION_MANIFEST_TAMPERED", str(manifest_path))
    model["manifest"] = expected_manifest
    return model


def write_manifest(root: Path) -> dict[str, Any]:
    model = validate(root, require_manifest=False)
    path = root / "decisions" / "manifest.json"
    path.write_text(json.dumps(model["manifest"], indent=2, sort_keys=True) + "\n")
    return model["manifest"]


def _replace_frontmatter_scalar(path: Path, key: str, value: str) -> bool:
    text = path.read_text()
    if text.startswith("---\n{"):
        pattern = re.compile(rf'(?m)^(\s*)"{re.escape(key)}":\s*"[^"]+"(,?)$')
        replacement = lambda match: f'{match.group(1)}"{key}": "{value}"{match.group(2)}'
    else:
        pattern = re.compile(rf"(?m)^{re.escape(key)}:\s*\S+\s*$")
        replacement = f"{key}: {value}"
    updated, count = pattern.subn(replacement, text)
    if count != 1:
        raise ContractError("FRONTMATTER_INVALID", f"{path}: {key} count={count}")
    if updated == text:
        return False
    path.write_text(updated)
    return True


def _governed_union(root: Path) -> list[str]:
    """Every path that can enter a seal this command is about to write."""
    domain = _frontmatter_optional(root / "DOMAIN.md")
    paths = {
        item
        for component in domain.get("components", [])
        for item in component.get("paths", [])
    }
    for name in LIVE_DOCS:
        paths.update(_frontmatter_optional(root / name).get("snapshot_scope", []) or [])
    for manifest in sorted((root / "docs" / "modules").glob("*/module-context.json")):
        paths.update(json.loads(manifest.read_text()).get("default_context", []))
    return sorted(paths)


def _reseal_precheck(root: Path) -> None:
    """A stored seal must describe a commit, not one machine's working tree.

    Emission compares the stored value against HEAD, so resealing while a
    governed scope carries uncommitted work bakes in a value that no commit can
    satisfy: `--check` goes green and emission blocks forever (#199 FAIL-2).
    Commit the governed change first, then reseal.

    This compares the two seals rather than asking `git status`, which is a
    proxy and not the invariant: assume-unchanged, skip-worktree and any
    smudge/eol filter hide a difference from status that the seals still see
    (#199 r2 FAIL-B).
    """
    if not (root / ".git").exists():
        return
    for relative in _governed_union(root):
        if _scope_ref(root, [relative]) != _scope_ref(root, [relative], at_head=True):
            raise ContractError("RESEAL_TREE_DIRTY", relative)


def reseal_backbone(root: Path) -> dict[str, Any]:
    root = root.resolve()
    _reseal_precheck(root)
    decision_paths = sorted((root / "decisions").glob("DEC-*.md"))
    module_manifests = sorted((root / "docs" / "modules").glob("*/module-context.json"))
    targets = [root / name for name in LIVE_DOCS] + decision_paths + [
        root / "decisions" / "manifest.json"
    ] + module_manifests
    originals = {path: path.read_text() if path.exists() else None for path in targets}
    changed: list[str] = []
    try:
        for path in module_manifests:
            try:
                record = json.loads(path.read_text())
            except json.JSONDecodeError as exc:
                raise ContractError("MODULE_MANIFEST_INVALID", f"{path}: {exc}") from exc
            _require(record, MODULE_REQUIRED, path)
            value = _scope_ref(root, record["default_context"])
            if record["context_seal"] != value:
                record["context_seal"] = value
                path.write_text(json.dumps(record, indent=2) + "\n")
                changed.append(f"{path.relative_to(root)}#context_seal")

        for name in ("CONTEXT.md", "ARCHITECTURE.md"):
            path = root / name
            record = _frontmatter(path)
            _require(record, DOC_REQUIRED, path)
            value = _scope_ref(root, record["snapshot_scope"])
            if _replace_frontmatter_scalar(path, "snapshot_ref", value):
                changed.append(f"{name}#snapshot_ref")

        domain_path = root / "DOMAIN.md"
        domain = _frontmatter(domain_path)
        _require(domain, DOC_REQUIRED, domain_path)
        value = _scope_ref(root, domain["snapshot_scope"])
        if _replace_frontmatter_scalar(domain_path, "snapshot_ref", value):
            changed.append("DOMAIN.md#snapshot_ref")
        domain = _frontmatter(domain_path)
        components = {
            item["component_id"]: item for item in domain.get("components", [])
        }
        if not components:
            raise ContractError("DOMAIN_MAP_EMPTY", "DOMAIN.md")

        for path in decision_paths:
            record = _frontmatter(path)
            _require(record, DECISION_REQUIRED, path)
            component_ids = record["governs"].get("components", [])
            unknown = sorted(set(component_ids) - set(components))
            if unknown:
                raise ContractError(
                    "UNKNOWN_COMPONENT",
                    f"{record['decision_id']}: {','.join(unknown)}",
                )
            governed_paths = [
                relative
                for component_id in component_ids
                for relative in components[component_id]["paths"]
            ]
            value = _scope_ref(root, governed_paths)
            if _replace_frontmatter_scalar(path, "scope_ref", value):
                changed.append(f"{path.relative_to(root)}#scope_ref")

        old_manifest = originals[root / "decisions" / "manifest.json"]
        manifest = write_manifest(root)
        manifest_path = root / "decisions" / "manifest.json"
        if manifest_path.read_text() != old_manifest:
            changed.append("decisions/manifest.json")
        validate(root)
    except Exception:
        for path, original in originals.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(original)
        raise
    return {
        "kind": "RESEALED" if changed else "NOOP",
        "verdict": "READY",
        "changed": changed,
        "decision_manifest_hash": manifest["manifest_hash"],
    }


def init_backbone(root: Path) -> dict[str, Any]:
    root = root.resolve()
    model = validate(root, require_manifest=False)
    audit = audit_authorities(root)
    if audit["verdict"] != "READY":
        blockers = [item["code"] for item in audit["findings"] if item["blocking"]]
        raise ContractError("AUTHORITY_AUDIT_BLOCKED", ",".join(blockers))
    path = root / "decisions" / "manifest.json"
    expected = json.dumps(model["manifest"], indent=2, sort_keys=True) + "\n"
    status = "NOOP" if path.is_file() and path.read_text() == expected else "PROMOTED"
    if status == "PROMOTED":
        path.write_text(expected)
    return {
        "kind": status,
        "verdict": "READY",
        "workspace": model["workspace"],
        "repo": model["repo"],
        "authorities": [
            {"path": name, "sha256": model["source_hashes"][name]}
            for name in sorted(LIVE_DOCS)
        ],
        "authority_count": len(LIVE_DOCS),
        "decision_manifest_hash": model["manifest"]["manifest_hash"],
        "execution_source_seal": audit["execution_source_seal"],
    }


def run_init_fixture(name: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fixture(root)
        if name == "polaris-path-leak":
            path = root / "CONTEXT.md"
            record = _frontmatter(path)
            record["snapshot_scope"] = ["/absolute/example/_polaris/CLAUDE.md"]
            _write_record(path, record, "CONTEXT.md")
            expected = "PORTABILITY_LEAK"
        elif name == "foreign-decision":
            path = root / "decisions" / "DEC-1.md"
            record = _frontmatter(path)
            record["workspace"] = "foreign"
            record["repos"] = ["foreign-repo"]
            _write_record(path, record, "Decision")
            expected = "SCOPE_CONFLICT"
        else:
            raise ContractError("FIXTURE_UNKNOWN", name)
        authority_hashes = {path: _file_hash(root / path) for path in LIVE_DOCS}
        try:
            init_backbone(root)
        except ContractError as exc:
            if exc.code != expected:
                raise
            assert authority_hashes == {path: _file_hash(root / path) for path in LIVE_DOCS}
            return {
                "kind": "BLOCK",
                "cause": exc.code,
                "fixture": name,
                "authoritative_writes": 0,
                "blocking_receipts": 1,
            }
        raise AssertionError(f"{name}: expected {expected}")


def emit_context(root: Path, work_item: str | None = None) -> dict[str, Any]:
    """Alias of the production resolver (DEC in PR #153 lane): one implementation, one seal.

    Selection logic lives in scripts/contextpack.py; this delegate keeps the public
    command and its contract (foundation default, declared-work-item guard) stable.
    """
    import importlib
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    cp = importlib.import_module("contextpack")
    try:
        return cp.resolve(root.resolve(), work_item or "", [])
    except cp.cbb.ContractError as exc:  # cross-module instance: re-raise locally
        raise ContractError(exc.code, exc.detail) from exc

def _write_record(path: Path, record: dict[str, Any], title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        + json.dumps(record, indent=2, sort_keys=True)
        + "\n---\n\n# "
        + title
        + "\n"
    )


def _fixture(root: Path) -> None:
    ref = "git:" + "0" * 40
    (root / "source.txt").write_text("current source\n")
    base = {
        "schema_version": 1,
        "status": "active",
        "owner": "role:cto",
        "workspace": "polaris",
        "repo": "polaris-os",
        "snapshot_ref": _scope_ref(root, ["source.txt"]),
        "snapshot_scope": ["source.txt"],
        "review_trigger": ["fixture changes"],
    }
    for name, kind in LIVE_DOCS.items():
        record = {**base, "document_type": kind}
        if name == "DOMAIN.md":
            record.update(
                domains=[{"domain_id": "d", "name": "D"}],
                components=[
                    {
                        "component_id": "c",
                        "domains": ["d"],
                        "paths": ["CONTEXT.md"],
                    }
                ],
            )
        _write_record(root / name, record, name)
    decision = {
        "schema_version": 1,
        "decision_id": "DEC-1",
        "decision_key": "key",
        "title": "Decision",
        "kind": "architecture",
        "status": "accepted",
        "owner": "role:cto",
        "decided_at": "2026-08-19",
        "workspace": "polaris",
        "repos": ["polaris-os"],
        "governs": {"domains": ["d"], "components": ["c"], "concerns": ["x"]},
        "supersedes": [],
        "superseded_by": None,
        "source_ref": ref,
        "evidence": ["fixture", "issue:fixture#1"],
        "enforcement": ["fixture"],
        "call_sites": ["CONTEXT.md"],
        "prerequisites": [],
        "closure_check": "fixture",
        "review_trigger": ["fixture changes"],
        "scope_ref": _scope_ref(root, ["CONTEXT.md"]),
        "legacy_review": {"scope": ["c"], "sources": []},
    }
    _write_record(root / "decisions" / "DEC-1.md", decision, "Decision")
    write_manifest(root)


def self_check() -> None:
    cases: list[tuple[str, str, Any]] = []

    def run_case(name: str, code: str, mutate: Any) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fixture(root)
            mutate(root)
            try:
                validate(root, require_manifest=code == "DECISION_MANIFEST_TAMPERED")
            except ContractError as exc:
                assert exc.code == code, (name, exc.code, code)
            else:
                raise AssertionError(f"{name}: expected {code}")
            cases.append((name, code, mutate))

    run_case(
        "missing live document",
        "LIVE_DOC_MISSING",
        lambda r: (r / "DOMAIN.md").unlink(),
    )

    def invalid_ref(root: Path) -> None:
        record = _frontmatter(root / "CONTEXT.md")
        record["snapshot_ref"] = "latest"
        _write_record(root / "CONTEXT.md", record, "CONTEXT.md")

    run_case("invalid source ref", "SOURCE_REF_INVALID", invalid_ref)

    def unknown_domain(root: Path) -> None:
        path = root / "decisions" / "DEC-1.md"
        record = _frontmatter(path)
        record["governs"]["domains"] = ["missing"]
        _write_record(path, record, "Decision")

    run_case("unknown domain", "UNKNOWN_DOMAIN", unknown_domain)

    def unknown_component(root: Path) -> None:
        path = root / "decisions" / "DEC-1.md"
        record = _frontmatter(path)
        record["governs"]["components"] = ["missing"]
        _write_record(path, record, "Decision")

    run_case("unknown component", "UNKNOWN_COMPONENT", unknown_component)

    def duplicate(root: Path) -> None:
        record = _frontmatter(root / "decisions" / "DEC-1.md")
        record["decision_id"] = "DEC-2"
        _write_record(root / "decisions" / "DEC-2.md", record, "Duplicate")

    run_case("duplicate accepted key", "CONTEXT_CONFLICT", duplicate)

    def missing_landing_call_sites(root: Path) -> None:
        path = root / "decisions" / "DEC-1.md"
        record = _frontmatter(path)
        record["call_sites"] = []
        _write_record(path, record, "Decision")

    run_case(
        "accepted Decision without landing call sites",
        "DECISION_LANDING_INVALID",
        missing_landing_call_sites,
    )

    def tamper(root: Path) -> None:
        path = root / "decisions" / "manifest.json"
        record = json.loads(path.read_text())
        record["manifest_hash"] = "tampered"
        path.write_text(json.dumps(record))

    run_case("manifest tamper", "DECISION_MANIFEST_TAMPERED", tamper)

    def no_accepted_decision(root: Path) -> None:
        path = root / "decisions" / "DEC-1.md"
        record = _frontmatter(path)
        record["status"] = "superseded"
        _write_record(path, record, "Decision")

    run_case(
        "accepted decision set empty",
        "ACCEPTED_DECISION_SET_EMPTY",
        no_accepted_decision,
    )

    def escaped_component_path(root: Path) -> None:
        path = root / "DOMAIN.md"
        record = _frontmatter(path)
        record["components"][0]["paths"] = ["../"]
        _write_record(path, record, "DOMAIN.md")

    run_case("component path escape", "PATH_OUTSIDE_ROOT", escaped_component_path)

    def nested_scope_symlink_escape(root: Path) -> None:
        scope = root / "scope"
        scope.mkdir()
        (scope / "escape").symlink_to(root.parent, target_is_directory=True)
        path = root / "CONTEXT.md"
        record = _frontmatter(path)
        record["snapshot_scope"] = ["scope"]
        _write_record(path, record, "CONTEXT.md")

    run_case(
        "nested scope symlink escape",
        "PATH_OUTSIDE_ROOT",
        nested_scope_symlink_escape,
    )

    def escaped_legacy_path(root: Path) -> None:
        path = root / "decisions" / "DEC-1.md"
        record = _frontmatter(path)
        record["legacy_review"]["sources"] = ["../"]
        _write_record(path, record, "Decision")

    run_case("legacy path escape", "PATH_OUTSIDE_ROOT", escaped_legacy_path)

    def absolute_scope_path(root: Path) -> None:
        path = root / "CONTEXT.md"
        record = _frontmatter(path)
        record["snapshot_scope"] = ["/absolute/example/polaris/CLAUDE.md"]
        _write_record(path, record, "CONTEXT.md")

    run_case("absolute path portability leak", "PORTABILITY_LEAK", absolute_scope_path)

    def foreign_decision(root: Path) -> None:
        path = root / "decisions" / "DEC-1.md"
        record = _frontmatter(path)
        record["workspace"] = "foreign"
        record["repos"] = ["foreign-repo"]
        _write_record(path, record, "Decision")

    run_case("foreign decision", "SCOPE_CONFLICT", foreign_decision)

    run_case(
        "live document changed after manifest",
        "DECISION_MANIFEST_TAMPERED",
        lambda r: (r / "ARCHITECTURE.md").write_text(
            (r / "ARCHITECTURE.md").read_text() + "\nchanged\n"
        ),
    )

    run_case(
        "declared source changed after snapshot",
        "SOURCE_REF_STALE",
        lambda r: (r / "source.txt").write_text("stale source\n"),
    )

    def asymmetric_supersession(root: Path) -> None:
        old = _frontmatter(root / "decisions" / "DEC-1.md")
        old["status"] = "superseded"
        old["superseded_by"] = "DEC-2"
        _write_record(root / "decisions" / "DEC-1.md", old, "Decision")
        new = {
            **old,
            "decision_id": "DEC-2",
            "status": "accepted",
            "superseded_by": None,
        }
        _write_record(root / "decisions" / "DEC-2.md", new, "Successor")

    run_case(
        "asymmetric supersession",
        "SUPERSESSION_NOT_SYMMETRIC",
        asymmetric_supersession,
    )

    def accepted_legacy_authority(root: Path) -> None:
        legacy = root / "adr" / "legacy.md"
        legacy.parent.mkdir()
        legacy.write_text("---\nstatus: accepted\n---\n")
        context = root / "CONTEXT.md"
        context.write_text(context.read_text() + "\nAuthority: [[adr/legacy]]\n")
        decision_path = root / "decisions" / "DEC-1.md"
        decision = _frontmatter(decision_path)
        decision["scope_ref"] = _scope_ref(root, ["CONTEXT.md"])
        _write_record(decision_path, decision, "Decision")

    run_case(
        "accepted legacy authority referenced by a live call site",
        "LEGACY_AUTHORITY_REFERENCED",
        accepted_legacy_authority,
    )

    def active_legacy_authority(root: Path) -> None:
        accepted_legacy_authority(root)
        legacy = root / "adr" / "legacy.md"
        record = _frontmatter(legacy)
        record["status"] = "active"
        _write_record(legacy, record, "Legacy")

    run_case(
        "active legacy authority referenced by a live call site",
        "LEGACY_AUTHORITY_REFERENCED",
        active_legacy_authority,
    )

    def incomplete_legacy_scope(root: Path) -> None:
        path = root / "decisions" / "DEC-1.md"
        record = _frontmatter(path)
        record["legacy_review"]["scope"] = []
        _write_record(path, record, "Decision")

    run_case(
        "accepted decision legacy review misses governed component",
        "LEGACY_REVIEW_SCOPE_INCOMPLETE",
        incomplete_legacy_scope,
    )
    assert len(cases) == 19

    def module_fixture(root: Path) -> Path:
        module = root / "docs" / "modules" / "fixture"
        module.mkdir(parents=True)
        (root / "docs" / "modules" / "README.md").write_text("# Modules\n")
        (module / "README.md").write_text("# Fixture\n")
        (module / "CHANGELOG.md").write_text("# Changelog\n")
        prd = module / "fixture.md"
        _write_record(
            prd,
            {
                "document_type": "prd",
                "authority_role": "canonical-spec",
                "status": "final",
                "module_id": "fixture.module",
            },
            "PRD",
        )
        prd.write_text(prd.read_text() + "\n### FR-1 Fixture\n")
        validation = module / "validation" / "2026-08-27-fixture.md"
        validation.parent.mkdir()
        validation.write_text("# Validation\n")
        for name in LIVE_DOCS:
            (root / name).write_text(f"# {name}\n")
        decision = root / "decisions" / "DEC-fixture.md"
        decision.parent.mkdir()
        decision.write_text("# Decision\n")
        default_context = [
            "docs/modules/fixture/README.md",
            "docs/modules/fixture/fixture.md",
        ]
        manifest = {
            "schema_version": 1,
            "module_id": "fixture.module",
            "status": "active",
            "owner": "role:cto",
            "canonical_prd": "docs/modules/fixture/fixture.md",
            "active_work": ["issue:fixture#1"],
            "default_context": default_context,
            "context_seal": _scope_ref(root, default_context),
            "required_requirement_ids": ["FR-1"],
            "active_plan": None,
            "active_validation": "docs/modules/fixture/validation/2026-08-27-fixture.md",
            "external_contracts": [*LIVE_DOCS, "decisions/DEC-fixture.md"],
            "history_excluded_by_default": True,
            "review_trigger": ["fixture changes"],
        }
        (module / "module-context.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        return module

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        module_fixture(root)
        assert _validate_module_dossiers(root)[0]["module_id"] == "fixture.module"

    module_codes: list[str] = []

    def run_module_case(code: str, mutate: Any) -> None:
        module_codes.append(code)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = module_fixture(root)
            mutate(root, module)
            try:
                _validate_module_dossiers(root)
            except ContractError as exc:
                assert exc.code == code, (exc.code, code)
            else:
                raise AssertionError(f"module fixture: expected {code}")

    def module_path_escape(root: Path, module: Path) -> None:
        path = module / "module-context.json"
        record = json.loads(path.read_text())
        record["canonical_prd"] = "../fixture.md"
        path.write_text(json.dumps(record))

    run_module_case("PATH_OUTSIDE_ROOT", module_path_escape)

    def module_missing_requirement(root: Path, module: Path) -> None:
        path = module / "fixture.md"
        path.write_text(path.read_text().replace("### FR-1 Fixture", "### Missing"))

    run_module_case("MODULE_REQUIREMENT_MISSING", module_missing_requirement)

    def module_stale_context(root: Path, module: Path) -> None:
        (module / "README.md").write_text("# Changed\n")

    run_module_case("MODULE_CONTEXT_STALE", module_stale_context)

    def module_active_plan_not_loaded(root: Path, module: Path) -> None:
        plan = module / "plan.md"
        plan.write_text("# Plan\n")
        path = module / "module-context.json"
        record = json.loads(path.read_text())
        record["active_plan"] = "docs/modules/fixture/plan.md"
        path.write_text(json.dumps(record))

    run_module_case("MODULE_ACTIVE_PLAN_NOT_LOADED", module_active_plan_not_loaded)

    def module_active_plan_bad_name(root: Path, module: Path) -> None:
        plans = module / "plans"
        plans.mkdir()
        plan = plans / "plan.md"
        plan.write_text("# Plan\n")
        path = module / "module-context.json"
        record = json.loads(path.read_text())
        relative = "docs/modules/fixture/plans/plan.md"
        record["active_plan"] = relative
        record["default_context"].append(relative)
        record["context_seal"] = _scope_ref(root, record["default_context"])
        path.write_text(json.dumps(record))

    run_module_case("MODULE_ACTIVE_PLAN_NAME_INVALID", module_active_plan_bad_name)

    def module_generic_prd_name(root: Path, module: Path) -> None:
        generic = module / "PRD.md"
        generic.write_text((module / "fixture.md").read_text())
        path = module / "module-context.json"
        record = json.loads(path.read_text())
        record["canonical_prd"] = "docs/modules/fixture/PRD.md"
        path.write_text(json.dumps(record))

    run_module_case("MODULE_PRD_NAME_INVALID", module_generic_prd_name)

    def module_validation_bad_name(root: Path, module: Path) -> None:
        bad = module / "validation" / "validation.md"
        bad.write_text("# Validation\n")
        path = module / "module-context.json"
        record = json.loads(path.read_text())
        record["active_validation"] = "docs/modules/fixture/validation/validation.md"
        path.write_text(json.dumps(record))

    run_module_case(
        "MODULE_ACTIVE_VALIDATION_NAME_INVALID", module_validation_bad_name
    )

    def module_symlink_escape(root: Path, module: Path) -> None:
        outside = root / "outside-prd.md"
        outside.write_text((module / "fixture.md").read_text())
        (module / "fixture.md").unlink()
        (module / "fixture.md").symlink_to(outside)

    run_module_case("MODULE_PATH_OUTSIDE_DOSSIER", module_symlink_escape)

    def module_default_context_beyond_map(root: Path, module: Path) -> None:
        specs = module / "specs"
        specs.mkdir()
        (specs / "2026-01-01-extra.md").write_text("# Spec\n")
        path = module / "module-context.json"
        record = json.loads(path.read_text())
        record["default_context"].append("docs/modules/fixture/specs/2026-01-01-extra.md")
        record["context_seal"] = _scope_ref(root, record["default_context"])
        path.write_text(json.dumps(record))

    run_module_case(
        "MODULE_DEFAULT_CONTEXT_BEYOND_MAP", module_default_context_beyond_map
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fixture(root)
        first = emit_context(root)
        second = emit_context(root)
        assert first == second
        assert first["work_item"] != "issue:polaris-os#99"
        assert first["context_pack_id"].startswith("CTX-polaris-")
        scoped = emit_context(root, "issue:fixture#1")
        assert scoped["work_item"] == "issue:fixture#1"
        assert scoped["context_pack_id"] != first["context_pack_id"]
        try:
            emit_context(root, "issue:foreign#1")
        except ContractError as exc:
            assert exc.code == "WORK_ITEM_UNVERIFIED"
        else:
            raise AssertionError("undeclared work item: expected WORK_ITEM_UNVERIFIED")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fixture(root)
        (root / "source.txt").write_text("changed source\n")
        first = reseal_backbone(root)
        assert first["kind"] == "RESEALED"
        assert validate(root)["manifest"]["manifest_hash"] == first["decision_manifest_hash"]
        second = reseal_backbone(root)
        assert second == first | {"kind": "NOOP", "changed": []}

        decision_path = root / "decisions" / "DEC-1.md"
        decision = _frontmatter(decision_path)
        decision["governs"]["components"] = ["component:unknown"]
        _write_record(decision_path, decision, "Decision")
        targets = [root / name for name in LIVE_DOCS] + [
            decision_path,
            root / "decisions" / "manifest.json",
        ]
        before = {path: path.read_text() for path in targets}
        try:
            reseal_backbone(root)
        except ContractError as exc:
            assert exc.code == "UNKNOWN_COMPONENT"
        else:
            raise AssertionError("reseal: expected UNKNOWN_COMPONENT")
        assert before == {path: path.read_text() for path in targets}

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "source.txt").write_text("source\n")
        base = {
            "schema_version": 1,
            "status": "active",
            "owner": "role:cto",
            "workspace": "polaris",
            "repo": "polaris-os",
            "snapshot_ref": _scope_ref(root, ["source.txt"]),
            "snapshot_scope": ["source.txt"],
            "review_trigger": ["source changes"],
        }
        for name, kind in LIVE_DOCS.items():
            _write_record(root / name, {**base, "document_type": kind}, name)
        (root / "POLARIS-VISION.md").write_text("# Vision\n## Current status\n## Roadmap\n")
        (root / "POLARIS-BOARD.md").write_text("# Board\n## Backlog\n")
        (root / "POLARIS.md").write_text("# Status\n## Decisions\n")
        shadow = root / ".worktrees" / "probe" / "ARCHITECTURE.md"
        shadow.parent.mkdir(parents=True)
        shadow.write_text("# Worktree architecture\n")

        audit = audit_authorities(root)
        assert audit["coverage"]["status"] == "COMPLETE"
        assert any(item["code"] == "MIXED_DOCUMENT" for item in audit["findings"])
        assert any(item["code"] == "TYPE_MISPLACED" for item in audit["findings"])
        assert audit["execution_source_seal"] is None
        assert all(item["content_kind"] and item["target"] for item in audit["claims"])
        assert any(
            source["scope"] == "worktree" and not source["default_context_eligible"]
            for source in audit["sources"]
        )
        old_hash = audit["source_manifest_hash"]
        old_inventory = audit["inventory_hash"]
        old_execution = audit["candidate_execution_source_hash"]
        shadow.write_text("# Worktree architecture changed\n")
        worktree_changed = audit_authorities(root)
        assert worktree_changed["source_manifest_hash"] == old_hash
        assert worktree_changed["inventory_hash"] != old_inventory
        assert worktree_changed["candidate_execution_source_hash"] == old_execution

        history = root / "memo" / "history.md"
        history.parent.mkdir()
        history.write_text("# Historical evidence\n")
        history_changed = audit_authorities(root)
        assert history_changed["source_manifest_hash"] != old_hash
        assert history_changed["candidate_execution_source_hash"] == old_execution

        component = root / "hand" / "ARCHITECTURE.md"
        component.parent.mkdir()
        component.write_text("# Component architecture\n")
        shadowed = audit_authorities(root)
        component_source = "source:path:hand/ARCHITECTURE.md"
        assert any(
            item["code"] == "AUTHORITY_SHADOW" and item["source_id"] == component_source
            for item in shadowed["findings"]
        )
        projection = {
            "status": "active",
            "authority_role": "projection",
            "projection_of": "ARCHITECTURE.md",
            "component_id": "test.component",
            "default_context": True,
        }
        _write_record(component, projection, "Component architecture")
        malformed = audit_authorities(root)
        assert any(
            item["code"] == "AUTHORITY_DECLARATION_INVALID"
            and item["source_id"] == component_source
            for item in malformed["findings"]
        )
        projection["default_context"] = False
        _write_record(component, projection, "Component architecture")
        projected = audit_authorities(root)
        assert not any(
            item["code"] in {"AUTHORITY_SHADOW", "AUTHORITY_DECLARATION_INVALID"}
            and item["source_id"] == component_source
            for item in projected["findings"]
        )
        assert next(
            source for source in projected["sources"] if source["source_id"] == component_source
        )["default_context_eligible"] is False

        (root / "POLARIS.md").write_text("# Status changed\n## Decisions\n")
        assert audit_authorities(root)["source_manifest_hash"] != old_hash

        (root / "MYSTERY.md").write_text("# Unknown authority\n")
        unknown = audit_authorities(root)
        assert any(item["code"] == "UNCLASSIFIED_SOURCE" for item in unknown["findings"])
        assert unknown["verdict"] == "BLOCK"
        _write_record(
            root / "MYSTERY.md",
            {
                "status": "archived",
                "authority_role": "history",
                "superseded_by": "POLARIS-VISION.md",
                "default_context": False,
            },
            "Historical authority",
        )
        classified_history = audit_authorities(root)
        assert not any(
            item["code"] == "UNCLASSIFIED_SOURCE"
            and item["source_id"] == "source:path:MYSTERY.md"
            for item in classified_history["findings"]
        )

        (root / "BROKEN.md").symlink_to(root / "missing.md")
        unreadable = audit_authorities(root)
        assert any(item["code"] == "SOURCE_UNREADABLE" for item in unreadable["findings"])

        (root / "BROKEN.md").unlink()
        _write_record(root / "POLARIS-VISION.md", {**base, "document_type": "vision"}, "Vision")
        _write_record(root / "POLARIS-BOARD.md", {**base, "document_type": "board"}, "Board")
        _write_record(root / "POLARIS.md", {**base, "document_type": "state"}, "Status")
        ready = audit_authorities(root)
        assert ready["verdict"] == "READY", [item for item in ready["findings"] if item["blocking"]]
        assert ready["execution_source_seal"].startswith("source-sha256:")

    with tempfile.TemporaryDirectory() as tmp:
        missing = audit_authorities(Path(tmp))
        assert {
            item["source_id"]
            for item in missing["findings"]
            if item["code"] == "LIVE_DOC_MISSING"
        } == {f"source:path:{name}" for name in LIVE_DOCS}
        assert missing["verdict"] == "BLOCK"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fixture(root)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=root,
            check=True,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        decision_path = root / "decisions" / "DEC-1.md"
        decision = _frontmatter(decision_path)
        decision["source_ref"] = f"git:{head}"
        _write_record(decision_path, decision, "Decision")
        (root / "decisions" / "manifest.json").unlink()
        promoted = init_backbone(root)
        noop = init_backbone(root)
        assert promoted["kind"] == "PROMOTED"
        assert noop == promoted | {"kind": "NOOP"}

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "governed").mkdir()
        (root / "governed" / "source.txt").write_text("source\n")
        (root / ".gitignore").write_text("governed/cache.tmp\n")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        sealed = _scope_ref(root, ["governed/"])
        (root / "governed" / "cache.tmp").write_text("machine-local\n")
        assert _scope_ref(root, ["governed/"]) == sealed
        (root / "governed" / "pending.txt").write_text("untracked source\n")
        untracked = _scope_ref(root, ["governed/"])
        assert untracked != sealed
        subprocess.run(
            ["git", "add", "governed/pending.txt"], cwd=root, check=True
        )
        assert _scope_ref(root, ["governed/"]) == untracked

    assert run_init_fixture("polaris-path-leak")["cause"] == "PORTABILITY_LEAK"
    assert run_init_fixture("foreign-decision")["cause"] == "SCOPE_CONFLICT"

    print("PASS: 54 adversarial context-backbone fixtures, 0 false-green")
    print("module dossier fixtures: " + ",".join(module_codes))


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", type=Path)
    group.add_argument("--write-manifest", type=Path)
    group.add_argument("--reseal", type=Path)
    group.add_argument("--init", type=Path)
    group.add_argument("--emit-context", type=Path)
    group.add_argument("--audit-authorities", type=Path)
    group.add_argument("--selfcheck", action="store_true")
    parser.add_argument(
        "--fixture", choices=("polaris-path-leak", "foreign-decision")
    )
    parser.add_argument("--work-item")
    args = parser.parse_args()
    if args.fixture and not args.init:
        parser.error("--fixture requires --init")
    if args.work_item and not args.emit_context:
        parser.error("--work-item requires --emit-context")
    try:
        if args.selfcheck:
            self_check()
        elif args.init:
            result = (
                run_init_fixture(args.fixture)
                if args.fixture
                else init_backbone(args.init)
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            if result["kind"] == "BLOCK":
                raise SystemExit(2)
        elif args.write_manifest:
            print(
                json.dumps(
                    write_manifest(args.write_manifest), indent=2, sort_keys=True
                )
            )
        elif args.reseal:
            print(json.dumps(reseal_backbone(args.reseal), indent=2, sort_keys=True))
        elif args.emit_context:
            print(
                json.dumps(
                    emit_context(args.emit_context, args.work_item),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.audit_authorities:
            audit = audit_authorities(args.audit_authorities)
            print(json.dumps(audit, indent=2, sort_keys=True))
            if audit["verdict"] != "READY":
                raise SystemExit(2)
        else:
            model = validate(args.check)
            print(
                json.dumps(
                    {
                        "documents": len(model["documents"]),
                        "accepted_decisions": sum(
                            item["record"]["status"] == "accepted"
                            for item in model["decisions"]
                        ),
                        "unresolved_scope": 0,
                        "manifest_hash": model["manifest"]["manifest_hash"],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
    except ContractError as exc:
        print(json.dumps({"kind": "BLOCK", "cause": exc.code, "detail": exc.detail}))
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
