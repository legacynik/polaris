#!/usr/bin/env python3
"""The audit arm's mechanical leg — one AST pass, no LLM, no API key.

Four rules, all read off the same import graph, because building it twice is the
expensive part: `cycle`, `package-size`, `instability`, and `abstractness` — which
mostly REFUSES, and that refusal is the point (see `refuse_abstractness`).

    detect.py [ROOT] [--json] [--config PATH] [--selfcheck]

Ignores: `<root>/.architecture/detect.json` -> {"ignoreRules": [], "ignorePaths": []},
plus an inline `arch-detect: ignore [rule ...]` comment in a module's first 20 lines.
"""
from __future__ import annotations
import argparse
import ast
import json
import statistics
import sys
import tempfile
from pathlib import Path

RULES = ("cycle", "package-size", "instability", "abstractness")
WAIVER = "arch-detect: ignore"
# vendored trees are not your architecture, and scanning one turns a 3s pass into minutes
VENDOR = ("__pycache__", "site-packages", "node_modules", "/.venv/", "/venv/", "/.git/")


def module_name(path: Path, root: Path) -> str:
    return ".".join(p for p in path.relative_to(root).with_suffix("").parts if p != "__init__")


def waived(src: str) -> set[str] | None:
    """None = not waived. Empty set = whole file. Otherwise the named rules."""
    for line in src.splitlines()[:20]:
        if WAIVER in line:
            return {r for r in line.split(WAIVER, 1)[1].split() if r in RULES}
    return None


def scan(root: Path, ignore_paths: tuple[str, ...] = ()) -> dict:
    """One pass: imports, statement count, abstract-base count, per module."""
    mods: dict[str, dict] = {}
    for path in sorted(root.rglob("*.py")):
        rel = f"/{path.relative_to(root)}"
        if any(v in rel for v in VENDOR) or any(p in rel for p in ignore_paths):
            continue
        src = path.read_text(errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        name = module_name(path, root)
        mods[name] = _walk(tree, name) | {"waived": waived(src)}
    for m in mods.values():  # keep only edges inside the tree — externals are not ours
        m["imports"] = {i for i in m["imports"] if i in mods} - {"__self__"}
    return mods


# ponytail: duplicates tools/components_census.py (local main, a1b4ce6) — unify onto the
# census module the day it lands on origin; until then this stays behavior-aligned with it
# (relative imports RESOLVED, not skipped: a cycle hidden behind `from . import x` was
# invisible here while visible to the census — the 9-vs-5-cycles divergence of PR #77).
def _walk(tree: ast.AST, modname: str) -> dict:
    """One pass, three accumulators: imports (absolute AND relative), statements, ABCs."""
    imports: set[str] = set()
    stmts = 0
    abstract = 0
    bases = {"ABC", "Protocol", "ABCMeta"}
    pkg = modname.rsplit(".", 1)[0] if "." in modname else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            stmts += 1
        if isinstance(node, ast.Import):
            imports |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative: resolve against this module's package
                base = pkg.rsplit(".", node.level - 1)[0] if node.level > 1 and pkg else pkg
                mod = f"{base}.{node.module}" if node.module and base else (node.module or base)
                if mod:
                    imports.add(mod)
                    imports |= {f"{mod}.{a.name}" for a in node.names}
            elif node.module:
                imports.add(node.module)
                imports |= {f"{node.module}.{a.name}" for a in node.names}
        elif isinstance(node, ast.ClassDef):
            if any(getattr(b, "id", getattr(b, "attr", "")) in bases for b in node.bases):
                abstract += 1
    return {"imports": imports, "stmts": stmts, "abstract": abstract}


def cycles(mods: dict) -> list[list[str]]:
    """Tarjan, iterative — a recursive one blows the stack on a real backend."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on: set[str] = set()
    out: list[list[str]] = []
    counter = 0
    for root_node in mods:
        if root_node in index:
            continue
        work = [(root_node, iter(sorted(mods[root_node]["imports"])))]
        index[root_node] = low[root_node] = counter
        counter += 1
        stack.append(root_node)
        on.add(root_node)
        while work:
            node, it = work[-1]
            nxt = next(it, None)
            if nxt is None:
                work.pop()
                if low[node] == index[node]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on.discard(w)
                        comp.append(w)
                        if w == node:
                            break
                    if len(comp) > 1:
                        out.append(sorted(comp))
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[node])
            elif nxt not in index:
                index[nxt] = low[nxt] = counter
                counter += 1
                stack.append(nxt)
                on.add(nxt)
                work.append((nxt, iter(sorted(mods[nxt]["imports"]))))
            elif nxt in on:
                low[node] = min(low[node], index[nxt])
    return sorted(out, key=len, reverse=True)


def refuse_abstractness(mods: dict) -> dict:
    """D = |A+I-1| needs a real A. In a duck-typed tree A collapses to ~0 and D just
    restates I — a number that looks measured and is not. Refuse, name the instrument."""
    classes = sum(m["abstract"] for m in mods.values())
    if classes >= max(3, len(mods) // 20):
        return {"rule": "abstractness", "status": "measured", "abstract_declarations": classes}
    return {"rule": "abstractness", "status": "ASSUMED",
            "why": f"only {classes} explicit ABC/Protocol declarations across {len(mods)} "
                   "modules — A collapses to ~0 and D would restate instability",
            "instrument": "declare Protocol interfaces at the seams, or adopt a metrics tool "
                          "that infers abstractness; until then D is not computed"}


def findings(root: Path, cfg: dict) -> list[dict]:
    skip_rules = set(cfg.get("ignoreRules", ()))
    mods = scan(root, tuple(cfg.get("ignorePaths", ())))
    if not mods:
        return []
    # a whole-file waiver (empty set) drops the module; a named one only mutes that rule
    live = {n: m for n, m in mods.items() if m["waived"] is None or m["waived"]}
    muted = {n: (m["waived"] or set()) for n, m in live.items()}
    out: list[dict] = []

    for comp in cycles(live):
        if "cycle" not in skip_rules and not any("cycle" in muted[n] for n in comp):
            out.append({"rule": "cycle", "size": len(comp), "modules": comp})

    pkgs: dict[str, int] = {}
    for name, m in live.items():
        pkg = name.rsplit(".", 1)[0] if "." in name else name
        pkgs[pkg] = pkgs.get(pkg, 0) + m["stmts"]
    if "package-size" not in skip_rules and len(pkgs) > 2:
        vals = list(pkgs.values())
        cut = statistics.mean(vals) + 2 * statistics.pstdev(vals)
        out += [{"rule": "package-size", "package": p, "statements": v, "outlier_above": round(cut)}
                for p, v in sorted(pkgs.items(), key=lambda kv: -kv[1]) if v > cut]

    if "instability" not in skip_rules:
        ca = {n: 0 for n in live}
        for m in live.values():
            for dep in m["imports"]:
                if dep in ca:
                    ca[dep] += 1
        for name, m in live.items():
            ce, ca_n = len(m["imports"]), ca[name]
            inst = round(ce / (ce + ca_n), 2) if ce + ca_n else None
            if inst in (0.0, 1.0) and ce + ca_n >= 5 and "instability" not in muted[name]:
                out.append({"rule": "instability", "module": name, "I": inst, "Ce": ce, "Ca": ca_n,
                            "reads_as": "stable OR rigid — only A separates them, see abstractness"
                            if inst == 0.0 else "depends on everything, nothing depends on it"})

    out.append(refuse_abstractness(live))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("root", nargs="?", default=".", type=Path)
    p.add_argument("--json", action="store_true")
    p.add_argument("--config", type=Path)
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()
    cfg_path = a.config or a.root / ".architecture" / "detect.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    res = findings(a.root.resolve(), cfg)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        for f in res:
            print(json.dumps(f))
        print(f"\n{len(res)} findings — mechanical only. Nothing here is a recommendation.",
              file=sys.stderr)
    return 0


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as d:
        r = Path(d)
        (r / "a.py").write_text("import b\n" + "x = 1\n" * 5)
        (r / "b.py").write_text("import a\n")
        (r / "c.py").write_text("x = 1\n")
        got = findings(r, {})
        cyc = [f for f in got if f["rule"] == "cycle"]
        assert cyc and cyc[0]["modules"] == ["a", "b"], got
        absr = [f for f in got if f["rule"] == "abstractness"][0]
        assert absr["status"] == "ASSUMED" and "instrument" in absr, absr
        assert not findings(r, {"ignoreRules": ["cycle"], "ignorePaths": []})[0]["rule"] == "cycle"
        (r / "a.py").write_text("# arch-detect: ignore cycle\nimport b\n")
        assert not [f for f in findings(r, {}) if f["rule"] == "cycle"], "inline waiver ignored"
        assert findings(r, {"ignorePaths": ["a.py", "b.py", "c.py"]}) == [], "empty tree"
        with tempfile.TemporaryDirectory() as d2:  # no .py at all
            assert findings(Path(d2), {}) == []
        (r / "d.py").write_text("from abc import ABC\nclass X(ABC): pass\n" * 3)
        assert [f for f in findings(r, {}) if f["rule"] == "abstractness"][0]["status"] == "measured"
    print("SELFCHECK OK — cycle found, abstractness refused then measured, config ignore, "
          "inline waiver, empty tree, no-python tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
