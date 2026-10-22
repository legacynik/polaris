#!/usr/bin/env python3
"""Validate Polaris live documents and scoped Decisions.

Nothing is stored to be kept in sync: the one freshness check runs at read time — every path a
live document cites (`snapshot_scope`) and every path an accepted Decision governs or names must
exist now. A missing one is a STALE row for a guided pack and a refusal for `--check`.
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import subprocess
import sys
import tempfile
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
}
MODULE_REQUIRED = {
    "schema_version",
    "module_id",
    "status",
    "owner",
    "canonical_prd",
    "active_work",
    "default_context",
    "required_requirement_ids",
    "active_plan",
    "active_validation",
    "external_contracts",
    "history_excluded_by_default",
    "review_trigger",
}
SOURCE_REF = re.compile(r"git:[0-9a-f]{40}\Z")
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


def _batch_payloads(stream: bytes, expected: int) -> list[bytes | None]:
    """Each payload of a `git cat-file --batch` response, in order; None for `missing`."""
    payloads: list[bytes | None] = []
    cursor = 0
    for _ in range(expected):
        end = stream.index(b"\n", cursor)
        header = stream[cursor:end].split(b" ")
        if header[-1] == b"missing":
            payloads.append(None)
            cursor = end + 1
            continue
        if len(header) != 3:
            raise ContractError(
                "HEAD_UNREADABLE", stream[cursor:end].decode("utf-8", "replace")[:80]
            )
        start = end + 1
        size = int(header[2])
        payloads.append(stream[start:start + size])
        cursor = start + size + 1
    return payloads


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
    if path in {"POLARIS-VISION.md", "POLARIS-BOARD.md", "POLARIS.md", "AGENTS.md", "CLAUDE.md"}:
        return "company-os-authority", path, False
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
    if first in {"audit", "references"} or path in {"README.md", "PROJECT.md", "PRODUCT.md", "DESIGN.md",
                                                          "ROADMAP.md", "CAPABILITIES.md"}:
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


def _freshness(root: Path, path: Path, record: dict[str, Any], role: str) -> tuple[str, str | None]:
    if path.name in {"AGENTS.md", "CLAUDE.md"} and role == "company-os-authority":
        return "CURRENT", None
    if role == "company-os-authority" and record.get("freshness_model"):
        required = record.get("status") == "active" and record.get("owner") and record.get("review_trigger")
        return ("CURRENT", None) if required else ("UNKNOWN", "NORMATIVE_CONTRACT_INCOMPLETE")
    if "snapshot_scope" in record:
        try:
            missing = _cited_missing(root, record["snapshot_scope"], False)
        except ContractError as exc:
            return "UNKNOWN", exc.code
        return ("STALE", "CITED_PATH_MISSING") if missing else ("CURRENT", None)
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
        # `.wiki/` and `wiki/` are projections by PATH (`_primary_role`); demanding the in-file
        # declaration there forced init to write a .wiki page on a branch (2026-09-26).
        if relative.name in AUTHORITY_BASENAMES and relative.parts[0] not in {".worktrees", ".wiki", "wiki"} and role in {"derived", "history"} and not (
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


def _cited_missing(root: Path, paths: Any, at_head: bool) -> list[str]:
    """The cited paths that are not there now: the whole freshness check, computed at read time."""
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p for p in paths):
        raise ContractError("SCOPE_PATHS_INVALID", repr(paths))
    return sorted(p for p in set(paths) if not _present(root, p, at_head))


def _frontmatter(path: Path) -> dict[str, Any]:
    return _parse_frontmatter(path.read_text(), path)


def _frontmatter_at(root: Path, path: Path, at_head: bool = False) -> dict[str, Any]:
    return _parse_frontmatter(_source_bytes(root, path, at_head).decode(), path)


def _parse_frontmatter(text: str, path: Path) -> dict[str, Any]:
    text = text.replace("\r\n", "\n")
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


def _validate_module_dossiers(
    root: Path, at_head: bool = False, *, missing: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Every module dossier, validated. A path it names that is gone refuses, unless `missing`
    is given (a guided pack): then it is collected and becomes a STALE row."""
    modules_root = root / "docs" / "modules"
    if _is_link(root, "docs/modules", at_head):  # W3f: every module would vanish in silence
        raise ContractError("MODULE_DEFAULT_CONTEXT_SYMLINK", "docs/modules")
    if not _present(root, "docs/modules", at_head):
        return []
    if not _present(root, "docs/modules/README.md", at_head, file_only=True):
        if missing is None:
            raise ContractError("MODULE_GUIDE_MISSING", "docs/modules/README.md")
        missing["docs/modules/README.md"] = {"code": "MODULE_GUIDE_MISSING", "detail": "docs/modules"}

    modules: list[dict[str, Any]] = []
    ids: set[str] = set()
    relatives = [
        path.relative_to(modules_root)
        for path in _sources_at(root, "docs/modules", at_head)
    ]
    for module_root in sorted(
        {modules_root / item.parts[0] for item in relatives if len(item.parts) > 1}
    ):
        dossier = module_root.relative_to(root).as_posix()
        if not _present(root, f"{dossier}/CHANGELOG.md", at_head, file_only=True):
            if missing is None:
                raise ContractError("MODULE_CHANGELOG_MISSING", dossier)
            missing[f"{dossier}/CHANGELOG.md"] = {"code": "MODULE_CHANGELOG_MISSING", "detail": dossier}
        manifest_path = module_root / "module-context.json"
        if not _present(root, f"{dossier}/module-context.json", at_head, file_only=True):
            if missing is None:
                raise ContractError("MODULE_MANIFEST_MISSING", dossier)
            missing[f"{dossier}/module-context.json"] = {
                "code": "MODULE_MANIFEST_MISSING", "detail": dossier,
                "active_work": _last_active_work(root, f"{dossier}/module-context.json")}
            continue  # no manifest, nothing of this dossier can be sealed: its absent row says so
        try:
            record = json.loads(_source_bytes(root, manifest_path, at_head).decode())
        except json.JSONDecodeError as exc:
            raise ContractError("MODULE_MANIFEST_INVALID", f"{manifest_path}: {exc}") from exc
        if not isinstance(record, dict):
            raise ContractError("MODULE_MANIFEST_INVALID", f"{manifest_path}: not an object")
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
            if not _present(root, value, at_head, file_only=True):
                if missing is None:
                    raise ContractError("MODULE_PATH_MISSING", f"{module_id}: {value}")
                if field == "active_validation":  # a default_context doc shows as the area's row
                    missing[value] = {"code": "MODULE_PATH_MISSING", "detail": f"{module_id}: {value}"}
            return target

        prd_path = module_path(record["canonical_prd"], "canonical_prd")
        assert prd_path is not None
        expected_prd_name = f"{module_root.name}.md"
        if prd_path.name != expected_prd_name:
            raise ContractError(
                "MODULE_PRD_NAME_INVALID",
                f"{module_id}: {prd_path.name}!={expected_prd_name}",
            )
        prd = _frontmatter_at(root, prd_path, at_head) if _present(root, record["canonical_prd"], at_head, file_only=True) else {
            "document_type": "prd", "authority_role": "canonical-spec", "status": "final",
            "module_id": module_id}  # W3f: a deleted PRD is the area's absent row, judged below
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
            if not _present(root, relative, at_head, file_only=True):
                if missing is None:
                    raise ContractError("MODULE_PATH_MISSING", f"{module_id}: {relative}")
                missing[relative] = {"code": "MODULE_PATH_MISSING", "detail": f"{module_id}: {relative}"}

        expected_ids = record["required_requirement_ids"]
        if (
            not isinstance(expected_ids, list)
            or not expected_ids
            or not all(isinstance(item, str) and item for item in expected_ids)
            or len(expected_ids) != len(set(expected_ids))
        ):
            raise ContractError("MODULE_REQUIREMENT_SET_INVALID", module_id)
        text = _source_bytes(root, prd_path, at_head).decode() if _present(root, record["canonical_prd"], at_head, file_only=True) else ""
        for requirement_id in expected_ids if _present(root, record["canonical_prd"], at_head, file_only=True) else []:
            if len(re.findall(rf"(?m)^### {re.escape(requirement_id)}(?:\s|$)", text)) != 1:
                raise ContractError("MODULE_REQUIREMENT_MISSING", f"{module_id}: {requirement_id}")

        gone = [rel for rel in default_context if not _present(root, rel, at_head, file_only=True)]
        modules.append(
            {
                "module_id": module_id,
                "path": relative_module.as_posix(),
                "stale_docs": {rel: {"freshness": "STALE", "current_hash": "absent",
                                     "stale": "MODULE_PATH_MISSING: in default_context, gone"}
                               for rel in gone},
                # The resolver consumes these instead of re-reading the manifest from the worktree.
                "default_context": list(default_context),
                "active_work": list(record["active_work"]),
            }
        )
    return modules


def _is_link(root: Path, relative: str, at_head: bool) -> bool:
    """A symlink ANYWHERE on the path — the leaf or any directory above it — on disk, or
    committed as one (mode 120000) in the tree `at_head` reads. Round 1 on #498: checking
    only the leaf let a doc under a linked `plans/` directory through."""
    parts = Path(relative).parts
    prefixes = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
    if any((root / prefix).is_symlink() for prefix in prefixes):
        return True
    if not at_head or not (root / ".git").exists():
        return False
    listing = subprocess.run(["git", "ls-tree", "-z", "HEAD", "--", *prefixes], cwd=root,
                             capture_output=True, check=False)
    if listing.returncode:
        raise ContractError("HEAD_UNREADABLE", listing.stderr.decode("utf-8", "replace")[:200] or relative)
    wanted = set(prefixes)  # ls-tree also lists a directory's CHILDREN: judge the prefixes only
    rows = [row.decode("utf-8", "surrogateescape") for row in listing.stdout.split(b"\0") if row]
    return any(row.startswith("120000 ") and row.split("\t", 1)[-1] in wanted for row in rows)


_HEAD_TREE: dict[str, tuple[frozenset[str], frozenset[str], dict[str, str]]] = {}
_HEAD_LINKS: dict[str, dict[str, str | None]] = {}


def _head_tree(root: Path) -> tuple[frozenset[str], frozenset[str], dict[str, str]]:
    """(files, directories, links -> blob oid) committed at HEAD, listed once per `validate`."""
    key = str(root)
    if key not in _HEAD_TREE and _head_commit(root) is None:
        _HEAD_TREE[key] = (frozenset(), frozenset(), {})  # no commit yet: nothing at HEAD
    if key not in _HEAD_TREE:
        listing = subprocess.run(["git", "ls-tree", "-r", "-z", "HEAD"], cwd=root,
                                 capture_output=True, check=False)
        if listing.returncode:
            raise ContractError("HEAD_UNREADABLE", listing.stderr.decode("utf-8", "replace")[:200])
        rows = [r.decode("utf-8", "surrogateescape").split("\t", 1)
                for r in listing.stdout.split(b"\0") if r]
        files = frozenset(name for _, name in rows)
        links = {name: meta.split(" ")[2] for meta, name in rows if meta.startswith("120000 ")}
        dirs = frozenset("/".join(f.split("/")[:i]) for f in files for i in range(1, f.count("/") + 1))
        _HEAD_TREE[key] = (files, dirs, links)
    return _HEAD_TREE[key]


def _present(root: Path, relative: str, at_head: bool, file_only: bool = False) -> bool:
    """Is `relative` there, in the tree the caller reads? HEAD for a pack, the working tree for
    `--check` — one rule for every source a record names (W3f round 2, critic C1)."""
    if not at_head or not (root / ".git").exists():
        target = _safe_path(root, relative)
        return target.is_file() if file_only else target.exists()
    files, dirs, links = _head_tree(root)
    name = posixpath.normpath(relative.rstrip("/"))
    for _ in range(8):  # W3g: a committed link is present only through its target
        if name not in links:
            return name in files or (not file_only and name in dirs)
        target = _link_targets(root).get(name)
        if target is None or target.startswith("/"):
            return False
        name = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
        if name == ".." or name.startswith("../"):
            return False
    return False  # a cycle of links resolves to nothing


def _link_targets(root: Path) -> dict[str, str | None]:
    """Every committed link's target string at HEAD, read in ONE batch per `validate`."""
    key = str(root)
    if key not in _HEAD_LINKS:
        links = _head_tree(root)[2]
        names = sorted(links)
        payloads = _batch_payloads(subprocess.run(
            ["git", "cat-file", "--batch"], cwd=root, check=False, capture_output=True,
            input="".join(f"{links[n]}\n" for n in names).encode()).stdout, len(names)) if names else []
        _HEAD_LINKS[key] = {n: (b.decode("utf-8", "surrogateescape").strip() if b is not None else None)
                            for n, b in zip(names, payloads)}
    return _HEAD_LINKS[key]


def _last_active_work(root: Path, relative: str) -> list[str]:
    """The `active_work` a deleted module manifest declared in its last committed version, so
    its own lane pack still finds its work item in a guided pack (W3g F1); [] when unprovable."""
    if not (root / ".git").exists():
        return []
    log = subprocess.run(["git", "log", "-1", "--format=%H", "--", relative], cwd=root,
                         capture_output=True, text=True, check=False).stdout.strip()
    shown = subprocess.run(["git", "show", f"{log}^:{relative}"], cwd=root, capture_output=True,
                           check=False) if log else None
    try:
        record = json.loads(shown.stdout) if shown is not None and shown.returncode == 0 else {}
    except ValueError:
        return []
    work = record.get("active_work") if isinstance(record, dict) else None
    return [w for w in work if isinstance(w, str)] if isinstance(work, list) else []


def _validate_landing(
    record: dict[str, Any], path: Path, root: Path, governed_paths: list[str],
    *, at_head: bool = False,
) -> list[str]:
    """Check a Decision's landing; the call sites that no longer exist are RETURNED (W3f) so
    `validate` refuses them strictly and collects them for a guided pack."""
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
    gone = [relative for relative in call_sites if not _present(root, relative, at_head)]
    for relative in call_sites:
        target = _safe_path(root, relative)
        if relative in gone:
            continue
        resolved = target.resolve()
        if record["status"] == "accepted" and not any(
            resolved == scope or scope in resolved.parents for scope in governed
        ):
            raise ContractError(
                "DECISION_CALL_SITE_OUTSIDE_SCOPE",
                f"{record['decision_id']}: {relative}",
            )
    return gone


def validate(root: Path, at_head: bool = False, *, degrade: bool = False) -> dict[str, Any]:
    """The backbone as it is now. ``at_head`` reads the committed tree (a pack), else the
    working tree (``--check``).

    A cited or governed path that is not there is collected in ``model["stale_missing"]``,
    never raised where it is found, so every structural check runs first. Then ``degrade``
    (a pack for a human or a guided lane) keeps them as STALE rows; without it the first
    one refuses, as ``--check`` must: a document citing a path that does not exist is a
    false claim.
    """
    root = root.resolve()
    _HEAD_TREE.pop(str(root), None)  # one HEAD listing per validate: never a stale commit's
    _HEAD_LINKS.pop(str(root), None)
    docs: dict[str, dict[str, Any]] = {}
    source_hashes: dict[str, str] = {}
    stale_missing: dict[str, dict[str, str]] = {}
    for name, expected_type in LIVE_DOCS.items():
        path = root / name
        if not _present(root, name, at_head, file_only=True):
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
        for gone in _cited_missing(root, record["snapshot_scope"], at_head):
            stale_missing.setdefault(gone, {"code": "CITED_PATH_MISSING", "detail": f"{name}: {gone}"})
        docs[name] = record
        source_hashes[name] = _source_hash(root, path, at_head)

    identities = {(record["workspace"], record["repo"]) for record in docs.values()}
    if len(identities) != 1 or not all(
        isinstance(value, str) and value for identity in identities for value in identity
    ):
        raise ContractError("SCOPE_CONFLICT", f"live documents: {sorted(identities)}")
    workspace, repo = identities.pop()
    modules = _validate_module_dossiers(root, at_head, missing=stale_missing if degrade else None)

    domain = docs["DOMAIN.md"]
    domains = {item["domain_id"] for item in domain.get("domains", [])}
    reserved = sorted(d for d in domains if isinstance(d, str) and d.split(".")[-1] == "all")
    if reserved:  # `all` is every declared domain (W3c): a domain may not take the name
        raise ContractError("DOMAIN_SLUG_RESERVED", ",".join(reserved))
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
            path for path in component["paths"] if not _present(root, path, at_head)
        )
        if missing_paths and not degrade:
            raise ContractError(
                "COMPONENT_PATH_MISSING", f"{component_id}: {','.join(missing_paths)}"
            )
        for gone in missing_paths:
            stale_missing[gone] = {"code": "COMPONENT_PATH_MISSING", "detail": f"{component_id}: {gone}"}

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
        gone = _validate_landing(record, path, root, governed_paths, at_head=at_head)
        if record["status"] != "accepted":
            gone = []  # a superseded record's call sites are history, not a claim about now
        if gone and not degrade:
            raise ContractError("DECISION_CALL_SITE_MISSING", gone[0])
        for relative in gone:
            stale_missing.setdefault(relative, {"code": "DECISION_CALL_SITE_MISSING",
                                                "detail": f"{decision_id}: {relative}"})
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
            if not _present(root, legacy_path, at_head, file_only=True):
                if not degrade:
                    raise ContractError("LEGACY_SOURCE_MISSING", legacy_path)
                stale_missing[legacy_path] = {"code": "LEGACY_SOURCE_MISSING",
                                              "detail": f"{decision_id} legacy_review"}
                continue
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
            if not _present(root, call_site, at_head, file_only=True) or target.suffix != ".md":
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
        "stale_missing": stale_missing,
    }
    if not degrade:
        for drift in stale_missing.values():
            raise ContractError(drift["code"], drift["detail"])
    return model


def init_backbone(root: Path) -> dict[str, Any]:
    root = root.resolve()
    model = validate(root)
    audit = audit_authorities(root)
    if audit["verdict"] != "READY":
        blockers = [item["code"] for item in audit["findings"] if item["blocking"]]
        raise ContractError("AUTHORITY_AUDIT_BLOCKED", ",".join(blockers))
    return {
        "kind": "READY",
        "verdict": "READY",
        "workspace": model["workspace"],
        "repo": model["repo"],
        "authorities": [
            {"path": name, "sha256": model["source_hashes"][name]}
            for name in sorted(LIVE_DOCS)
        ],
        "authority_count": len(LIVE_DOCS),
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


def _contextpack_dir() -> Path | None:
    """Where the resolver sits: beside this file, or in the shared `scripts/` of the vault or
    package that holds this skill (`<root>/scripts/`, recognised by its checker shim)."""
    here = Path(__file__).resolve().parent
    shared = here.parents[2] / "scripts"
    for base in (here, shared):
        if (base / "contextpack.py").is_file() and (base / "check_context_backbone.py").is_file():
            return base
    return None


def emit_context(root: Path, work_item: str | None = None) -> dict[str, Any]:
    """Alias of the production resolver (DEC in PR #153 lane): one implementation, one seal.

    Selection logic lives in scripts/contextpack.py; this delegate keeps the public
    command and its contract (foundation default, declared-work-item guard) stable.
    """
    import importlib

    cp_dir = _contextpack_dir()
    if cp_dir is None:
        raise ContractError("CONTEXTPACK_UNAVAILABLE",
                            "emit-context needs the Polaris resolver scripts/contextpack.py, "
                            "which this installation does not carry")
    sys.path.insert(0, str(cp_dir))
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
        "legacy_review": {"scope": ["c"], "sources": []},
    }
    _write_record(root / "decisions" / "DEC-1.md", decision, "Decision")


def self_check() -> None:
    cases: list[tuple[str, str, Any]] = []

    def run_case(name: str, code: str, mutate: Any) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fixture(root)
            mutate(root)
            try:
                validate(root)
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
        "cited path deleted",
        "CITED_PATH_MISSING",
        lambda r: (r / "source.txt").unlink(),
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
    assert len(cases) == 15, len(cases)

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
        path.write_text(json.dumps(record))

    run_module_case(
        "MODULE_DEFAULT_CONTEXT_BEYOND_MAP", module_default_context_beyond_map
    )

    if _contextpack_dir() is None:
        # Installed alone: no resolver beside the checker, so emit-context refuses by name.
        try:
            emit_context(Path(tempfile.gettempdir()))
        except ContractError as exc:
            assert exc.code == "CONTEXTPACK_UNAVAILABLE", exc.code
        else:
            raise AssertionError("standalone emit-context: expected CONTEXTPACK_UNAVAILABLE")
    else:
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
        (root / "source.txt").write_text("source\n")
        base = {
            "schema_version": 1,
            "status": "active",
            "owner": "role:cto",
            "workspace": "polaris",
            "repo": "polaris-os",
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
        assert init_backbone(root)["kind"] == "READY"

    assert run_init_fixture("polaris-path-leak")["cause"] == "PORTABILITY_LEAK"
    assert run_init_fixture("foreign-decision")["cause"] == "SCOPE_CONFLICT"

    print("PASS: 47 adversarial context-backbone fixtures, 0 false-green")
    print("module dossier fixtures: " + ",".join(module_codes))


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", type=Path)
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
