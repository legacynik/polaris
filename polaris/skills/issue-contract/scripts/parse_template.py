#!/usr/bin/env python3
"""Read a repo's .github/ISSUE_TEMPLATE/ into a machine-readable manifest.

Zero dependencies (no pyyaml — the suite runs on 4 harnesses, some without it).
Deliberately covers the GitHub issue-form subset actually observed on the 4
repos audited 2026-08-09 (acme-api bug/feature/task.yml, acme-web feat-medium/bug-S1/
bug-S2.yml), not general YAML.
# ponytail: line-scanner, not a real YAML parser — deeply nested `body:` blocks
# (multi-select options, nested `if`) are not modeled. Upgrade: swap in
# `yaml.safe_load` behind a `try: import yaml` if a form ever needs it.

Usage:
    parse_template.py --repo-path <path> [--json] [--refresh]
    parse_template.py --selfcheck
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "issue-contract"
FIELD_BLOCK = re.compile(r"^\s*-\s*type:\s*\S", re.M)


def fingerprint(tpl_dir: Path) -> str:
    files = sorted(p for p in tpl_dir.glob("*") if p.is_file())
    h = hashlib.sha256()
    for p in files:
        h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()[:16]


def read_config(tpl_dir: Path) -> dict:
    cfg = tpl_dir / "config.yml"
    if not cfg.exists():
        return {"blank_issues_enabled": True}
    text = cfg.read_text(errors="replace")
    m = re.search(r"^blank_issues_enabled:\s*(true|false)", text, re.M | re.I)
    return {"blank_issues_enabled": m.group(1).lower() == "true" if m else True}


def _scalar(text: str, key: str) -> str | None:
    m = re.search(rf"^\s*{key}:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip("'\"") if m else None


def _list_field(text: str, key: str) -> list[str]:
    m = re.search(rf"^\s*{key}:\s*\[(.*)\]\s*$", text, re.M)
    if m:
        return [x.strip(" '\"") for x in m.group(1).split(",") if x.strip(" '\"")]
    m = re.search(rf"^\s*{key}:\s*\n((?:^\s+-\s*.+\n?)+)", text, re.M)
    if not m:
        return []
    return [ln.split("-", 1)[1].strip(" '\"") for ln in m.group(1).splitlines() if ln.strip()]


def parse_yaml_form(text: str) -> dict:
    """GitHub issue-form subset: name/description/labels + body[].{id,label,required}."""
    fields = []
    starts = [m.start() for m in FIELD_BLOCK.finditer(text)] + [len(text)]
    for i in range(len(starts) - 1):
        block = text[starts[i]:starts[i + 1]]
        fid = _scalar(block, "id")
        label = _scalar(block, "label")
        required = bool(re.search(r"required:\s*true", block, re.I))
        if fid or label:
            fields.append({"id": fid or label, "label": label or fid, "required": required})
    return {
        "kind": "form",
        "name": _scalar(text, "name") or "",
        "labels": _list_field(text, "labels"),
        "fields": fields,
    }


def parse_md_template(text: str) -> dict:
    """Legacy .md template: optional --- frontmatter --- + ## sections as placeholders."""
    name, labels, body = "", [], text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            fm, body = text[3:end], text[end + 4:]
            name = _scalar(fm, "name") or ""
            labels = _list_field(fm, "labels") or (
                [x.strip() for x in (_scalar(fm, "labels") or "").split(",") if x.strip()]
            )
    sections = []
    for m in re.finditer(r"^##\s+(.+?)\s*\n(.*?)(?=^##\s|\Z)", body, re.M | re.S):
        sections.append({"header": m.group(1).strip(), "placeholder": m.group(2).strip()})
    return {"kind": "legacy", "name": name, "labels": labels, "sections": sections}


def build_manifest(tpl_dir: Path) -> dict:
    templates = []
    for p in sorted(tpl_dir.glob("*")):
        if not p.is_file() or p.name == "config.yml":
            continue
        text = p.read_text(errors="replace")
        if p.suffix in (".yml", ".yaml"):
            parsed = parse_yaml_form(text)
        elif p.suffix == ".md":
            parsed = parse_md_template(text)
        else:
            continue
        parsed["file"] = p.name
        templates.append(parsed)
    return {**read_config(tpl_dir), "templates": templates}


def load_or_build(repo_path: Path, refresh: bool = False) -> dict:
    tpl_dir = repo_path / ".github" / "ISSUE_TEMPLATE"
    if not tpl_dir.is_dir():
        return {"blank_issues_enabled": True, "templates": [], "source": "absent"}
    fp = fingerprint(tpl_dir)
    cache_file = CACHE_DIR / f"{hashlib.sha256(str(repo_path).encode()).hexdigest()[:16]}.json"
    if not refresh and cache_file.exists():
        cached = json.loads(cache_file.read_text())
        if cached.get("_fingerprint") == fp:
            return cached
    manifest = build_manifest(tpl_dir)
    manifest["_fingerprint"] = fp
    manifest["source"] = str(tpl_dir)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(manifest, indent=2))
    return manifest


def selfcheck() -> int:
    import tempfile
    bug_yml = (
        "name: Bug report\nlabels: [\"bug\"]\n"
        "body:\n  - type: textarea\n    id: acceptance-criteria\n"
        "    attributes:\n      label: Acceptance criteria\n"
        "    validations:\n      required: true\n"
        "  - type: textarea\n    id: repro\n    attributes:\n      label: Repro steps\n"
    )
    legacy_md = "---\nname: Feature\nlabels: feature, needs-triage\n---\n" \
                "## Motivation\nwhy\n\n## Acceptance criteria\n- [ ] ...\n"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tpl = root / ".github" / "ISSUE_TEMPLATE"; tpl.mkdir(parents=True)
        (tpl / "bug.yml").write_text(bug_yml)
        (tpl / "feature.md").write_text(legacy_md)
        (tpl / "config.yml").write_text("blank_issues_enabled: false\n")

        m = load_or_build(root)
        assert m["blank_issues_enabled"] is False, "config.yml not honored"
        assert len(m["templates"]) == 2, f"expected 2 templates, got {len(m['templates'])}"
        form = next(t for t in m["templates"] if t["file"] == "bug.yml")
        assert form["kind"] == "form" and len(form["fields"]) == 2, "form fields not parsed"
        req = next(f for f in form["fields"] if f["id"] == "acceptance-criteria")
        assert req["required"] is True, "required:true not detected"
        legacy = next(t for t in m["templates"] if t["file"] == "feature.md")
        assert legacy["kind"] == "legacy" and len(legacy["sections"]) == 2, "sections not parsed"
        assert "feature" in legacy["labels"], "frontmatter labels not parsed"

        global CACHE_DIR
        CACHE_DIR = root / "cache"
        m1 = load_or_build(root)
        cache_file = next(CACHE_DIR.glob("*.json"))
        mtime1 = cache_file.stat().st_mtime
        m2 = load_or_build(root)
        assert cache_file.stat().st_mtime == mtime1, "cache hit should not rewrite the file"
        (tpl / "bug.yml").write_text(bug_yml + "\n")  # content changes -> fingerprint changes
        m3 = load_or_build(root)
        assert m3["_fingerprint"] != m1["_fingerprint"], "fingerprint must change on edit"

        empty = load_or_build(root / "no-templates-here")
        assert empty["templates"] == [] and empty["source"] == "absent", "absent case wrong"
    print("SELFCHECK OK — 6 rami provati: form, legacy, config, cache-hit, cache-invalidate, absent")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-path", type=Path)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not a.repo_path:
        ap.error("--repo-path is required (or --selfcheck)")
    manifest = load_or_build(a.repo_path.resolve(), a.refresh)
    print(json.dumps(manifest, indent=2) if a.json else json.dumps(manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
