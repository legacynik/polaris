#!/usr/bin/env python3
"""#153 — production ContextPack resolver (DB-FR-05).

Selects ALL and ONLY the accepted Decisions applicable to the requested domains, with
source_id/source_hash/freshness/reason per row; superseded Decisions are recorded in
`dropped`, never included. Freshness is proven by the backbone validator (stale seals
block before any selection). `resolve` prints a sealed pack; any contract violation
exits 2 with `CODE: detail` on stderr. `test <fixture>` replays adversarial sandboxes.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as cbb  # noqa: E402

BUDGET = 4000
# ponytail: the two canonical PRDs are 8.1k and 6.4k of content; 4k lands once they
# are split (#325 follow-up). 10k binds today — documentary-backbone sits at 81% of it.
AREA_BUDGET = 10_000


def _repo_domain_map(root: Path) -> dict[str, list[str]]:
    """Deterministic join: repo-level issue labels (.github/DOMAINS.yml) -> polaris.* domain ids.
    Convention: `skills`->polaris.skills; explicit table for the rest; unmapped -> block."""
    table = {"skills": ["polaris.skills"], "memoria": ["polaris.memory"],
             "gates": ["polaris.execution", "polaris.skills"], "docs": ["polaris.documentation"],
             "wiki": ["polaris.memory"], "team": ["polaris.company-os"],
             "infra": ["polaris.execution"], "tooling": ["polaris.execution"]}
    known = _known_domains(root)
    return {k: [d for d in v if d in known] for k, v in table.items()}


def repo_domains_to_polaris(root: Path, labels: list[str]) -> list[str]:
    table = _repo_domain_map(root)
    out: list[str] = []
    for lab in labels:
        if lab not in table or not table[lab]:
            raise cbb.ContractError("UNKNOWN_REPO_DOMAIN", lab)
        out.extend(table[lab])
    return sorted(set(out))


def _known_domains(root: Path) -> set[str]:
    dom = cbb._frontmatter(root / "DOMAIN.md")
    return {d["domain_id"] for d in dom.get("domains", [])}


def _decision_split(model: dict, selected: set[str]) -> tuple[list, list]:
    shas = {d["decision_id"]: d["sha256"] for d in model["manifest"]["decisions"]}
    rows, dropped = [], []
    for item in model["decisions"]:
        rec = item["record"]
        hit = sorted(set(rec["governs"]["domains"]) & selected)
        if not hit:
            continue
        if rec["workspace"] != model["workspace"]:
            raise cbb.ContractError("SCOPE_CONFLICT", f"{rec['decision_id']}: workspace {rec['workspace']}")
        entry = {"source_id": rec["decision_id"], "source_hash": shas.get(rec["decision_id"], ""),
                 "freshness": "CURRENT", "reason": f"accepted Decision governs {','.join(hit)}"}
        if rec["status"] == "accepted":
            rows.append(entry)
        elif rec["status"] == "superseded":
            entry["reason"] = f"SUPERSEDED by {rec.get('superseded_by') or 'a later Decision'}"
            dropped.append(entry)
        else:
            entry["reason"] = f"NOT_ACCEPTED (status: {rec['status']})"
            dropped.append(entry)
    return rows, dropped


def _area_row(root: Path, module_id: str, rel: str) -> dict:
    return {"source_id": rel, "source_hash": cbb._source_hash(root, root / rel, at_head=True),
            "freshness": "CURRENT",
            "reason": f"active set of {module_id} via module-context.json (work item in active_work)"}


def _area(root: Path, module: dict) -> dict:
    """One documentation area, disclosed as the map declares it (I19).

    `default_context` is README + canonical document + active plan — the backbone
    validator blocks anything beyond it, so the pack never carries a whole folder.
    The estimate is the CONTENT the agent opens, not the pointer rows: a ceiling over
    the rows reads ~160 tokens for an 8k area and could never bind. Committed bytes
    only, from the same tree the validator read."""
    rows = [_area_row(root, module["module_id"], rel) for rel in module["default_context"]]
    estimate = sum((len(cbb._source_bytes(root, root / row["source_id"], at_head=True)) + 3) // 4
                   for row in rows)
    area = {"module_id": module["module_id"], "active_work": module["active_work"],
            "documents": rows, "token_estimate": estimate, "budget": AREA_BUDGET,
            "over_budget": estimate > AREA_BUDGET}
    if area["over_budget"]:
        raise cbb.ContractError("AREA_OVERFLOW", f"{module['module_id']}: {estimate} tokens > {AREA_BUDGET}")
    return area


def _areas(root: Path, model: dict) -> list[dict]:
    """The validated manifests, never a second read of the worktree."""
    return [_area(root, module) for module in model["modules"]]


def _module_rows(areas: list[dict], work_item: str) -> list[dict]:
    return [row for area in areas if work_item in area["active_work"] for row in area["documents"]]


def _document_rows(model: dict, areas: list[dict], work_item: str) -> list[dict]:
    rows = [{"source_id": name, "source_hash": model["source_hashes"][name], "freshness": "CURRENT",
             "reason": "live technical authority (always in scope)"}
            for name in sorted(cbb.LIVE_DOCS)]
    return rows + _module_rows(areas, work_item)


def _work_item_declared(model: dict, work_item: str) -> bool:
    """Declared by HEAD, never by the worktree: a manifest edited on disk must not
    let a work item nobody committed seal a pack."""
    accepted = (i["record"] for i in model["decisions"] if i["record"]["status"] == "accepted")
    return (any(work_item in record.get("evidence", []) for record in accepted)
            or any(work_item in module["active_work"] for module in model["modules"]))


def resolve(root: Path, work_item: str, domains: list[str]) -> dict[str, Any]:
    model = cbb.validate(root, at_head=True)
    if work_item and not _work_item_declared(model, work_item):
        raise cbb.ContractError("WORK_ITEM_UNVERIFIED", work_item)
    work_item = work_item or f"foundation:{model['repo']}"
    selected = set(domains) or _known_domains(root)
    unknown = sorted(selected - _known_domains(root))
    if unknown:
        raise cbb.ContractError("UNKNOWN_DOMAIN", ",".join(unknown))
    decisions, dropped = _decision_split(model, selected)
    areas = _areas(root, model)
    pack = {"schema_version": 1, "work_item": work_item, "workspace": model["workspace"],
            "repo": model["repo"], "domains": sorted(selected), "decisions": decisions,
            "documents": _document_rows(model, areas, work_item), "areas": areas,
            "dropped": dropped, "area_budget": AREA_BUDGET,
            "decision_manifest_hash": model["manifest"]["manifest_hash"], "token_budget": BUDGET}
    pack["sealed_commit"] = cbb._head_commit(root)
    pack["token_estimate"] = (len(json.dumps(pack, ensure_ascii=False)) + 3) // 4
    if pack["token_estimate"] > BUDGET:
        raise cbb.ContractError("CONTEXT_OVERFLOW", f"{pack['token_estimate']}>{BUDGET}")
    pack["pack_seal"] = cbb._json_hash(pack)
    pack["context_pack_id"] = f"CTX-{model['workspace']}-{pack['pack_seal'][:12]}"
    return pack


def _fixture_superseded(root: Path) -> None:
    old = cbb._frontmatter(root / "decisions" / "DEC-1.md")
    new = dict(old, decision_id="DEC-2", supersedes=["DEC-1"])
    cbb._write_record(root / "decisions" / "DEC-2.md", new, "Successor")
    old.update(status="superseded", superseded_by="DEC-2")
    cbb._write_record(root / "decisions" / "DEC-1.md", old, "Old")
    cbb.reseal_backbone(root)


def _fixture_foreign(root: Path) -> None:
    rec = cbb._frontmatter(root / "decisions" / "DEC-1.md")
    rec["workspace"] = "foreign"
    cbb._write_record(root / "decisions" / "DEC-1.md", rec, "Foreign")
    cbb.reseal_backbone(root)


def _fixture_stale(root: Path) -> None:
    (root / "source.txt").write_text("mutated without reseal\n")


def run_fixture(name: str) -> int:
    mutate = {"superseded-decision": _fixture_superseded, "cross-workspace-collision": _fixture_foreign,
              "stale-source": _fixture_stale}.get(name)
    if mutate is None:
        print(f"unknown fixture: {name}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cbb._fixture(root)
        mutate(root)
        domains = sorted(_known_domains(root))
        pack = resolve(root, "issue:fixture#1", domains)
        print(json.dumps(pack, indent=2))
        return 0


def _run_case(name: str) -> tuple[int, str]:
    import io
    from contextlib import redirect_stderr, redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        code = _guarded(lambda: run_fixture(name))
    return code, buf.getvalue()


def _selfcheck() -> int:
    cases = [("superseded-decision", 0, "SUPERSEDED"), ("cross-workspace-collision", 2, "SCOPE_CONFLICT"),
             ("stale-source", 2, "SOURCE_REF_STALE")]
    for name, want, marker in cases:
        code, out = _run_case(name)
        assert code == want and marker in out, f"{name}: exit={code}, marker={marker!r} missing"
    print(f"SELFCHECK OK — {len(cases)} adversarial fixtures")
    return 0


def _guarded(fn) -> int:
    try:
        return fn()
    except cbb.ContractError as exc:
        print(f"{exc.code}: {exc.detail}", file=sys.stderr)
        return 2


def main() -> int:
    ap = argparse.ArgumentParser(description="#153 ContextPack resolver")
    ap.add_argument("command", nargs="?", choices=["resolve", "test"])
    ap.add_argument("fixture", nargs="?")
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--work-item", default="")
    ap.add_argument("--domains", action="append", default=[])
    ap.add_argument("--repo-domain", action="append", default=[])
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    if a.command == "test":
        return _guarded(lambda: run_fixture(a.fixture or ""))
    if a.command == "resolve":
        def _run() -> int:
            domains = a.domains + (repo_domains_to_polaris(a.root, a.repo_domain) if a.repo_domain else [])
            print(json.dumps(resolve(a.root, a.work_item, domains), indent=2))
            return 0
        return _guarded(_run)
    ap.error("command required")


if __name__ == "__main__":
    sys.exit(main())
