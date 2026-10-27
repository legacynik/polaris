#!/usr/bin/env python3
"""polaris_init_docs.py — the documents `polaris init --mode minimal` writes.

Two rules hold every function here. Existing frontmatter is MERGED into, never replaced,
so nothing a repository already declared is lost. And every body line this module emits
that no path proves carries UNKNOWN, so the triad can be read without being believed.

Covered by `polaris_init.py --selfcheck`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as backbone  # noqa: E402

UNPROVEN = "UNKNOWN — not proven by this run"
REVIEW = [
    "A default execution-context authority changes",
    "A component path moves outside its declared scope",
]


def split(path: Path) -> tuple[dict, str]:
    """(frontmatter record, body). A file with no frontmatter is all body, kept whole."""
    if not path.is_file():
        return {}, ""
    text = path.read_text(errors="replace")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    return backbone._frontmatter_optional(path), text[end + 5 :].lstrip("\n")


def write(path: Path, record: dict, body: str) -> None:
    """JSON frontmatter: the contract's own parser reads it, and lists survive it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    front = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(f"---\n{front}\n---\n\n{body.rstrip()}\n")


def annotate(path: Path, additions: dict) -> None:
    """Add declaration keys to a document WITHOUT rewriting what is already there.

    The contract's parser is line-based: a nested YAML list round-trips into one bogus
    key per item. Measured on a real product repository, re-dumping a shadow copy's
    frontmatter destroyed its `changes_since_last_sync` list. So foreign YAML is appended
    to in place, and only a block that is already JSON is merged and rewritten.
    """
    text = path.read_text(errors="replace") if path.is_file() else ""
    end = text.find("\n---\n", 4) if text.startswith("---\n") else -1
    if end < 0:
        return write(path, additions, text)
    block = text[4:end]
    if block.lstrip().startswith("{"):
        return write(path, json.loads(block) | additions, text[end + 5 :].lstrip("\n"))
    added = "".join(
        f"{key}: {value if isinstance(value, str) else json.dumps(value)}\n"
        for key, value in additions.items()
    )
    path.write_text(text[: end + 1] + added + text[end + 1 :])


def header(who: dict[str, str], kind: str, scope: list[str]) -> dict:
    """The live-document contract: `snapshot_scope` is the paths it cites, checked at read time."""
    return {
        "schema_version": 1, "document_type": kind, "status": "active",
        "owner": "role:founder", "workspace": who["workspace"], "repo": who["repo"],
        "snapshot_scope": scope,
        "review_trigger": REVIEW,
    }


def _body(title: str, sections: list[tuple[str, list[str]]]) -> str:
    lines = [f"# {title}", ""]
    for heading, items in sections:
        lines += [f"## {heading}", "", *items, ""]
    return "\n".join(lines)


def context_body(who: dict) -> str:
    return _body(f"Context — {who['repo']}", [
        ("Purpose", [f"- {UNPROVEN}: no purpose statement found to keep"]),
    ])


def architecture_body(who: dict, listed: list[dict]) -> str:
    """Each component line names a path that exists; what it DOES stays UNKNOWN."""
    paths = [f"- `{item['paths'][0]}` — {UNPROVEN}: responsibility" for item in listed]
    return _body(f"Architecture — {who['repo']}", [
        ("Components", paths or [f"- {UNPROVEN}: no source root found"]),
        ("Boundaries", [f"- {UNPROVEN}: no boundary measured"]),
        ("Dependencies", [f"- {UNPROVEN}: no dependency measured"]),
        ("Deployment", [f"- {UNPROVEN}: no pipeline measured"]),
        ("Versioning", [f"- {UNPROVEN}: no release contract measured"]),
    ])


def domain_body(who: dict) -> str:
    return _body(f"Domain — {who['repo']}", [
        ("Domains", [f"- `{who['repo']}.unclassified` — {UNPROVEN}: boundaries"]),
        ("Ubiquitous language", [f"- {UNPROVEN}: no term promoted from the prose yet"]),
    ])


def declare_derived(root: Path, component_id: str) -> list[str]:
    """Every shadow of a live document says what it is a copy OF, and leaves the context."""
    touched = []
    for finding in backbone.audit_authorities(root)["findings"]:
        path = _shadow_path(root, finding)
        if path is None:
            continue
        target = path.name if path.name in backbone.LIVE_DOCS else "CONTEXT.md"
        role = backbone._primary_role(path.relative_to(root))[0]
        field = "superseded_by" if role == "history" else "projection_of"
        kind = "history" if role == "history" else "projection"
        annotate(path, {"authority_role": kind, "default_context": False,
                        field: target, "component_id": component_id})
        touched.append(str(path.relative_to(root)))
    return touched


def _shadow_path(root: Path, finding: dict) -> Path | None:
    if finding["code"] != "AUTHORITY_SHADOW":
        return None
    relative = finding["source_id"].removeprefix("source:path:")
    path = root / relative
    return path if path.is_file() else None
