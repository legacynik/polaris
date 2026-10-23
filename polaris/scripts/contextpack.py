#!/usr/bin/env python3
"""#153 — production ContextPack resolver (DB-FR-05).

Selects ALL and ONLY the accepted Decisions applicable to the requested domains, with
source_id/source_hash/freshness/reason per row; superseded Decisions are recorded in
`dropped`, never included. Freshness is read now: a path a record cites that is gone is a
STALE row by default and blocks under `--autonomous`. `resolve` prints the pack; any contract
violation exits 2 with `CODE: detail` on stderr. `test <fixture>` replays adversarial sandboxes.
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
import contextpack_declared as declared_layer  # noqa: E402
import contextpack_flight as flight_layer  # noqa: E402
import contextpack_labels as labels_layer  # noqa: E402
import contextpack_receipt as receipt  # noqa: E402
import contextpack_seal as sealer  # noqa: E402
import contextpack_unknown as unknown_layer  # noqa: E402

BUDGET = sealer.BUDGET  # one definition: the module that enforces it owns it
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
    known = labels_layer.known_domains(root)
    mapped = {k: [d for d in v if d in known] for k, v in table.items()}
    return labels_layer.derived_labels(root, known) | {k: v for k, v in mapped.items() if v}


def repo_domains_to_polaris(root: Path, labels: list[str]) -> list[str]:
    table = _repo_domain_map(root)
    out: list[str] = []
    for lab in labels:
        if lab not in table or not table[lab]:
            raise cbb.ContractError("UNKNOWN_REPO_DOMAIN", lab)
        out.extend(table[lab])
    return sorted(set(out))


def _decision_split(model: dict, selected: set[str]) -> tuple[list, list]:
    rows, dropped = [], []
    for item in model["decisions"]:
        rec = item["record"]
        hit = sorted(set(rec["governs"]["domains"]) & selected)
        if not hit:
            continue
        if rec["workspace"] != model["workspace"]:
            raise cbb.ContractError("SCOPE_CONFLICT", f"{rec['decision_id']}: workspace {rec['workspace']}")
        entry = {"source_id": rec["decision_id"], "source_hash": model["source_hashes"][item["path"]],
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


def _area_row(root: Path, module: dict, rel: str) -> dict:
    return sealer.area_row(root, module, rel)  # W3f: a gone doc is an `absent` row


def _area(root: Path, module: dict) -> dict:
    """One documentation area, disclosed as the map declares it (I19).

    `default_context` is README + canonical document + active plan — the backbone
    validator blocks anything beyond it, so the pack never carries a whole folder.
    The estimate is the CONTENT the agent opens, not the pointer rows: a ceiling over
    the rows reads ~160 tokens for an 8k area and could never bind. Committed bytes
    only, from the same tree the validator read."""
    rows = [_area_row(root, module, rel) for rel in module["default_context"]]
    estimate = sealer.area_estimate(root, rows)
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
    rows = sealer.document_rows(model)
    return rows + _module_rows(areas, work_item)


def _work_item_declared(model: dict, work_item: str) -> bool:
    """Declared by HEAD, never by the worktree: a manifest edited on disk must not
    let a work item nobody committed seal a pack."""
    accepted = (i["record"] for i in model["decisions"] if i["record"]["status"] == "accepted")
    return (any(work_item in record.get("evidence", []) for record in accepted)
            or any(work_item in module["active_work"] for module in model["modules"])
            or any(work_item in gone.get("active_work", []) for gone in model.get("stale_missing", {}).values()))


def resolve(root: Path, work_item: str, domains: list[str], *, degrade: bool = False) -> dict[str, Any]:
    model = sealer.model_or_none(root, degrade)
    if model is None:
        absent = declared_layer.attach(root, sealer.seal(
            root, unknown_layer.pack(root, work_item, domains)), receipt.areas(domains))
        return receipt.close(root, flight_layer.attach(root, absent, receipt.areas(domains)))
    if work_item and not _work_item_declared(model, work_item):
        raise cbb.ContractError("WORK_ITEM_UNVERIFIED", work_item)
    work_item = work_item or f"foundation:{model['repo']}"
    selected = set(domains) or labels_layer.known_domains(root)
    unknown = sorted(selected - labels_layer.known_domains(root))
    if unknown:
        raise cbb.ContractError("UNKNOWN_DOMAIN", ",".join(unknown))
    decisions, dropped = _decision_split(model, selected)
    areas = _areas(root, model)
    pack = {"schema_version": 1, "work_item": work_item, "workspace": model["workspace"],
            "repo": model["repo"], "domains": sorted(selected), "decisions": decisions,
            "documents": _document_rows(model, areas, work_item), "areas": areas,
            "dropped": dropped, "area_budget": AREA_BUDGET, "token_budget": BUDGET}
    return receipt.close(root, flight_layer.attach(root, declared_layer.attach(
        root, sealer.seal(root, pack), receipt.areas(domains)), receipt.areas(domains)))


def _fixture_superseded(root: Path) -> None:
    old = cbb._frontmatter(root / "decisions" / "DEC-1.md")
    new = dict(old, decision_id="DEC-2", supersedes=["DEC-1"])
    cbb._write_record(root / "decisions" / "DEC-2.md", new, "Successor")
    old.update(status="superseded", superseded_by="DEC-2")
    cbb._write_record(root / "decisions" / "DEC-1.md", old, "Old")


def _fixture_foreign(root: Path) -> None:
    rec = cbb._frontmatter(root / "decisions" / "DEC-1.md")
    rec["workspace"] = "foreign"
    cbb._write_record(root / "decisions" / "DEC-1.md", rec, "Foreign")


def _fixture_stale(root: Path) -> None:
    (root / "source.txt").unlink()  # a path every live document cites, gone


def run_fixture(name: str) -> int:
    mutate = {"superseded-decision": _fixture_superseded, "cross-workspace-collision": _fixture_foreign,
              "stale-source": _fixture_stale, "stale-source-guided": _fixture_stale}.get(name)
    if mutate is None:
        print(f"unknown fixture: {name}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cbb._fixture(root)
        mutate(root)
        print(json.dumps(resolve(root, "issue:fixture#1", sorted(labels_layer.known_domains(root)),
                                 degrade=name.endswith("-guided")), indent=2))
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
             ("stale-source", 2, "CITED_PATH_MISSING"), ("stale-source-guided", 0, '"freshness": "STALE"')]
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
    ap.add_argument("command", nargs="?", choices=["resolve", "test", "audit"])
    ap.add_argument("fixture", nargs="?")
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--work-item", default="")
    ap.add_argument("--domains", action="append", default=[])
    ap.add_argument("--repo-domain", action="append", default=[])
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--autonomous", action="store_true", help="no human reads it: a cited path that is gone blocks")
    a = receipt.parse(ap)
    if a.selfcheck or a.command == "audit":
        return _selfcheck() if a.selfcheck else receipt.audit(a.root, a.since)
    if a.command == "test":
        return _guarded(lambda: run_fixture(a.fixture or ""))
    if a.command == "resolve":
        def _run() -> int:
            domains = a.domains + receipt.selected_domains(a.root, a.area, a.repo_domain)
            print(json.dumps(resolve(a.root, a.work_item, domains, degrade=not a.autonomous), indent=2))
            return 0
        return _guarded(_run)
    ap.error("command required")


if __name__ == "__main__":
    sys.exit(main())
