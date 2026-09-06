#!/usr/bin/env python3
"""The modification gate — which tiers a change to an existing SKILL.md owes.

Creation is the rare case; every skill is edited many times after it lands. Before this
script the two runnable tiers went green on an edit that rewrote the description itself
(references/bypass-test.md B5): T1 validates structure, T2a compares text, neither knows
anything changed. So a trigger edit shipped carrying a rank-1 rate that had been measured
against a description no longer on disk.

Three deterministic jobs — no judgement, no model call:
  1. classify the change (trigger vs contract vs mechanism vs prose) and name the tiers
     it owes;
  2. validate the stored prompt set and check list those tiers need, refusing a corpus
     that is thin, all-positive, or full of placeholders;
  3. verify the ratchet receipt still belongs to THIS description, by hash recorded at
     measurement time. A green measured on the old wording is not a green.

    change_gate.py --skill DIR [--base REF | --baseline FILE] [--state FILE]
    change_gate.py --selfcheck

Exit: 0 PASS · 1 FAIL · 2 usage / not verifiable here · 3 CONCERNS (declare it).
Stdlib only, no network, no pip — the bundle travels across four harnesses.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import body, desc_sha, frontmatter, load_eval_cases  # noqa: E402 — one implementation each

# `version` is excluded on purpose: every change bumps it, so it carries no signal.
TRIGGER_FIELDS = ("description", "name", "auto", "user-invocable")
CONTRACT_FIELDS = ("io", "lifecycle", "invokes", "invoked-by")
# A body line carrying a command, a path, a table row or a hard rule changes what the
# agent DOES; a line carrying none of those changes only how it reads.
MECHANISM = re.compile(
    r"(```|\bpython3\b|\bbash\b|scripts/|--[a-z]|exit \d|\|.*\||"
    r"\b(MUST|NEVER|ALWAYS|blocca|blocking|mandatory|refuse)\b)", re.I)
PLACEHOLDER = re.compile(r"^\s*(todo|tbd|\.{1,3}|xxx|fixme)?\s*$", re.I)
CATEGORIES = ("outcome", "process", "style", "efficiency")
POSITIVE_KINDS = ("explicit", "implicit", "contextual")
MIN_CASES, MAX_CASES, MIN_NEGATIVES, MAX_CHECKS = 10, 20, 3, 8


def band(arms: int) -> tuple[int, int]:
    """The band's job is 'enough that the rate means something, few enough that it still gets
    re-run', and both halves scale with how many routing arms the door has — not with a
    constant. A nine-arm door measured on 16 cases put the only case of two arms in the test
    split and read 50%: the number moved on which arm the shuffle happened to hold, not on the
    description (`architettura`, PR #69). Two cases per arm is the floor under that; three per
    arm is where re-running stops being cheap. A corpus that declares no `dimensions.arm` is a
    one-job door and keeps the original 10-20."""
    return max(MIN_CASES, 2 * arms), max(MAX_CASES, 3 * arms)




def changed_lines(old: str, new: str) -> list[str]:
    """Lines on exactly one side. Order-insensitive on purpose: a moved block is not a
    behaviour change, and treating it as one is how a gate turns into noise."""
    return [ln for ln in set(old.splitlines()) ^ set(new.splitlines()) if ln.strip()]



def mark_only(old_desc: str, new_desc: str) -> bool:
    """A ◇ -> ✦ promotion changes the description without moving the trigger text."""
    return old_desc != new_desc and old_desc.lstrip("◇✦ ") == new_desc.lstrip("◇✦ ")


def trigger_text(description: str) -> str:
    """The status badge is not trigger text, including when another behaviour change shares
    the same diff. Promotion must not manufacture a fresh routing measurement."""
    return description.lstrip("◇✦ ")


def classify(old: str | None, new: str,
             bundle_changes: tuple[str, ...] = ()) -> tuple[str, set[str], list[str]]:
    """(class, owed tiers, reasons). Fail-closed: only whitespace is provably cosmetic."""
    if old is None:
        return "NEW", {"T1", "T2a", "T2b", "T3"}, ["no baseline version — treated as new"]
    fo, fn = frontmatter(old), frontmatter(new)
    if mark_only(fo.get("description", ""), fn.get("description", "")) and body(old) == body(new):
        return "MARK", {"T1", "RECEIPT"}, [
            "promotion mark changed and nothing else — the trigger text is identical, so the "
            "measurement still holds; what this owes is the receipt (SKILL-STANDARD.md step 3)"]
    tiers, why = {"T1"}, []
    for f in TRIGGER_FIELDS:
        if f == "description" and trigger_text(fo.get(f, "")) == trigger_text(fn.get(f, "")):
            continue
        if fo.get(f) != fn.get(f):
            tiers |= {"T2a", "T2b"}
            why.append(f"{f} changed — the trigger moved, rank-1 must be re-measured")
    for f in CONTRACT_FIELDS:
        if fo.get(f) != fn.get(f):
            tiers.add("T3")
            why.append(f"{f} changed — the declared contract moved")
    diff = changed_lines(body(old), body(new))
    if diff and any(MECHANISM.search(ln) for ln in diff):
        tiers.add("T3")
        why.append(f"{len(diff)} body line(s) changed, at least one carries a mechanism")
    elif diff:
        why.append(f"{len(diff)} body line(s) changed, prose only — declare whether "
                   "behaviour moved")
    runtime_changes = [p for p in bundle_changes if p.split("/", 1)[0] in {
        "scripts", "references", "assets", "templates"
    } and p != "references/ratchet-state.json"]
    if runtime_changes:
        tiers.add("T3")
        why.append("runtime bundle changed: " + ", ".join(runtime_changes))
    if not why:
        return "COSMETIC", tiers, ["whitespace or reordering only"]
    kind = "TRIGGER" if "T2b" in tiers else "BEHAVIOUR" if "T3" in tiers else "PROSE"
    return kind, tiers, why


def load(path: Path, key: str | None = None) -> tuple[list | None, str]:
    """Absent or unreadable is FAIL, never an empty pass — SKILL-STANDARD rule 1."""
    if not path.exists():
        return None, f"FAIL: {path.name} missing at {path.parent}"
    try:
        data = json.loads(path.read_text())
        return (data.get(key, []) if key else data), ""
    except (json.JSONDecodeError, AttributeError) as e:
        return None, f"FAIL: {path.name} is not readable as JSON ({e})"


def check_prompts(cases: list[dict], arms: int = 1) -> list[str]:
    """The T2b/T3 corpus: a band scaled to the arms, every invocation style, real negatives."""
    errs: list[str] = []
    lo, hi = band(arms)
    if not lo <= len(cases) <= hi:
        errs.append(f"FAIL: {len(cases)} cases — the set must hold {lo}-{hi}"
                    + (f" ({arms} arms declared, two cases per arm minimum)" if arms > 1 else ""))
    ids = [c.get("id", "") for c in cases]
    if len(set(ids)) != len(ids) or not all(ids):
        errs.append("FAIL: case ids must be present and unique")
    prompts = [c.get("prompt", "") for c in cases]
    if any(PLACEHOLDER.match(p) for p in prompts):
        errs.append("FAIL: a placeholder prompt satisfies nothing (TODO/empty/...)")
    if len(set(prompts)) != len(prompts):
        errs.append("FAIL: duplicate prompts inflate the rate without adding evidence")
    negatives = [c for c in cases if c.get("should_trigger") is False]
    if len(negatives) < MIN_NEGATIVES:
        errs.append(f"FAIL: {len(negatives)} negative controls — at least {MIN_NEGATIVES} "
                    "are needed to catch trigger theft")
    if any(c.get("kind") != "negative" for c in negatives):
        errs.append("FAIL: every should_trigger=false case must declare kind: negative")
    kinds = {c.get("kind") for c in cases if c.get("should_trigger") is True}
    missing = [k for k in POSITIVE_KINDS if k not in kinds]
    if missing:
        errs.append(f"FAIL: no positive case of kind {', '.join(missing)} — one invocation "
                    "style untested is one routing failure unseen")
    return errs


def check_checks(checks: list[dict]) -> list[str]:
    """The T3 rubric. Every entry is must-pass, so the list stays small on purpose."""
    errs: list[str] = []
    if not checks or len(checks) > MAX_CHECKS:
        errs.append(f"FAIL: {len(checks)} checks — keep 1-{MAX_CHECKS}, all must-pass")
    bad = [c.get("category") for c in checks if c.get("category") not in CATEGORIES]
    if bad:
        errs.append(f"FAIL: category {bad} not in {CATEGORIES}")
    if not any(c.get("category") == "outcome" for c in checks):
        errs.append("FAIL: no outcome check — process without outcome grades ceremony")
    if checks and not any(c.get("cmd") for c in checks):
        errs.append("CONCERNS: no check carries a cmd — the whole rubric rides on a model "
                    "grader where a command could decide it")
    return errs


def check_receipt(entry: dict | None, slug: str, current: str) -> list[str]:
    """The receipt must belong to THIS description. Hash, not mtime: no clock to fool."""
    if not entry:
        return [f"FAIL: ratchet state has no entry for {slug!r} — T2b was never recorded"]
    recorded = entry.get("desc_sha256")
    if not recorded:
        return [f"CONCERNS: the {slug!r} receipt predates description pinning — re-run T2b "
                "once so the rate is bound to a description"]
    if recorded != current:
        return [f"FAIL: the recorded rank-1 {entry.get('last_rate')} was measured on "
                f"description {recorded}, the file now holds {current} — re-measure; "
                "a green does not travel across a trigger edit"]
    return []


def check_receipt_row(changelog: Path, slug: str) -> list[str]:
    """A mark flip with no receipt is reverted on sight (SKILL-STANDARD.md). The receipt is a
    row in the suite CHANGELOG naming the slug — the numbers behind it are the founder's to
    write, but its absence is mechanically detectable."""
    if not changelog.exists():
        return [f"FAIL: no CHANGELOG at {changelog} — a mark flip without a receipt is "
                "reverted on sight"]
    # Word-bounded: a plain substring test let the slug "d" match inside "door" and passed a
    # changelog that said nothing about the skill at all.
    if not re.search(rf"\b{re.escape(slug)}\b", changelog.read_text()):
        return [f"FAIL: {changelog.name} has no row naming {slug!r} — the mark moved with no "
                "receipt (invocation count, which repos, date: SKILL-STANDARD.md step 3)"]
    return []



def _entry_for(state: dict, slug: str, sha: str) -> dict | None:
    """Slug first; on miss, fall back to the pin. The slug is a display label — the
    description hash is what proves the measurement (rename `architettura` ->
    `architecture` orphaned a slug key while the measured trigger text never moved)."""
    if slug in state:
        return state[slug]
    for entry in state.values():
        if isinstance(entry, dict) and entry.get("desc_sha256") == sha:
            return entry
    return None


def prerequisites(skill: Path, tiers: set[str], new_text: str, state: Path) -> list[str]:
    errs: list[str] = []
    if "RECEIPT" in tiers:
        slug = frontmatter(new_text).get("name", skill.name)
        errs += check_receipt_row(skill.parent / "CHANGELOG.md", slug)
    if tiers & {"T2b", "T3"}:
        cases, meta, err = load_eval_cases(skill / "eval" / "prompts.json")
        if err:
            errs.append(f"FAIL: {err}")
        else:
            slug = frontmatter(new_text).get("name", skill.name)
            declared = meta.get("skill")
            if declared and declared != slug:
                errs.append(f"FAIL: prompts.json declares skill: {declared!r} but gates "
                            f"{slug!r} — stale identity field (rename debt), fix it")
            errs += check_prompts(cases,
                                  len(meta.get("dimensions", {}).get("arm", [])) or 1)
    if "T3" in tiers:
        checks, err = load(skill / "eval" / "checks.json")
        errs += [err] if err else check_checks(checks or [])
    if "T2b" in tiers:
        slug = frontmatter(new_text).get("name", skill.name)
        st, err = load(state)
        if err:
            errs.append(f"{err} — T2b was never recorded")
        else:
            errs += check_receipt(_entry_for(st, slug, desc_sha(new_text)) if isinstance(st, dict) else None,
                                  slug, desc_sha(new_text))
    return errs


def report(skill: Path, old: str | None, new: str, state: Path,
           bundle_changes: tuple[str, ...] = ()) -> tuple[int, list[str]]:
    kind, tiers, why = classify(old, new, bundle_changes)
    errs = prerequisites(skill, tiers, new, state)
    lines = [f"class: {kind}", f"owes:  {' '.join(sorted(tiers))}"]
    lines += [f"  - {w}" for w in why] + (errs or ["all owed prerequisites present"])
    if any(e.startswith("FAIL") for e in errs):
        return 1, lines
    return (3, lines) if any(e.startswith("CONCERNS") for e in errs) or kind == "PROSE" \
        else (0, lines)


def read_baseline(skill: Path, base: str | None, baseline: Path | None) -> tuple[str | None, str]:
    """(old text | None, note). Cannot resolve -> raise: 'not verifiable here' is exit 2."""
    if baseline:
        if not baseline.exists():
            raise FileNotFoundError(f"--baseline {baseline} does not exist")
        return baseline.read_text(), f"baseline file {baseline}"
    top = subprocess.run(["git", "-C", str(skill), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if top.returncode != 0:
        raise RuntimeError(f"{skill} is not in a git checkout and no --baseline was given")
    rel = (skill / "SKILL.md").resolve().relative_to(Path(top.stdout.strip()).resolve())
    ref = f"{base or 'HEAD'}:{rel}"
    show = subprocess.run(["git", "-C", str(skill), "show", ref],
                          capture_output=True, text=True)
    return (None, f"{ref} not in history — new file") if show.returncode else \
        (show.stdout, f"git {ref}")


def changed_bundle_paths(skill: Path, base: str | None, baseline: Path | None) -> tuple[str, ...]:
    """Runtime files changed against a git ref. A standalone SKILL.md baseline cannot prove it."""
    if baseline:
        return ()
    top = subprocess.run(["git", "-C", str(skill), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, check=True).stdout.strip()
    root = Path(top).resolve()
    rel = skill.resolve().relative_to(root)
    changed = subprocess.run(
        ["git", "-C", top, "diff", "--name-only", base or "HEAD", "--", str(rel)],
        capture_output=True, text=True, check=True).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "-C", top, "ls-files", "--others", "--exclude-standard", "--", str(rel)],
        capture_output=True, text=True, check=True).stdout.splitlines()
    prefix = str(rel) + "/"
    return tuple(sorted({p.removeprefix(prefix) for p in changed + untracked if p != str(rel)}))


def default_state(skill: Path) -> Path:
    """Use the suite-wide ratchet. A per-skill fallback keeps standalone bundles diagnosable."""
    shared = skill.parent / "skill-meta" / "references" / "ratchet-state.json"
    return shared if shared.exists() else skill / "references" / "ratchet-state.json"


SKILL_BASE = ('---\nname: d\ndescription: "old trigger"\nversion: 0.1.0\n'
              'io: "a -> b"\nlifecycle: "x"\n---\n\n# d\n\nRun `python3 scripts/x.py`.\n')
CASES_OK = [{"id": f"p{i:02d}", "should_trigger": True, "kind": POSITIVE_KINDS[i % 3],
             "prompt": f"positive case {i}"} for i in range(7)] + \
           [{"id": f"n{i:02d}", "should_trigger": False, "kind": "negative",
             "prompt": f"negative control {i}"} for i in range(3)]


def selfcheck() -> int:
    assert classify(SKILL_BASE, SKILL_BASE + "\n\n")[:2] == ("COSMETIC", {"T1"})
    edited = SKILL_BASE.replace('"old trigger"', '"a brand new trigger"')
    kind, tiers, _ = classify(SKILL_BASE, edited)
    assert kind == "TRIGGER" and {"T2a", "T2b"} <= tiers, (kind, tiers)
    assert "T3" in classify(SKILL_BASE, SKILL_BASE + "\nRun `python3 scripts/y.py`.\n")[1]
    assert classify(SKILL_BASE, SKILL_BASE, ("scripts/y.py",))[:2] == \
        ("BEHAVIOUR", {"T1", "T3"})
    assert classify(SKILL_BASE, SKILL_BASE, ("references/ratchet-state.json",))[:2] == \
        ("COSMETIC", {"T1"}), "a generated receipt cannot recursively create T3 debt"
    kind, tiers, _ = classify(SKILL_BASE, SKILL_BASE + "\nThis door is old.\n")
    assert kind == "PROSE" and "T3" not in tiers, (kind, tiers)
    assert classify(None, SKILL_BASE)[:2] == ("NEW", {"T1", "T2a", "T2b", "T3"})
    # the mark flip: classified apart, keeps the measurement, owes the receipt
    marked = SKILL_BASE.replace('"old trigger"', '"◇ old trigger"')
    flipped = SKILL_BASE.replace('"old trigger"', '"✦ old trigger"')
    assert classify(marked, flipped)[:2] == ("MARK", {"T1", "RECEIPT"}), classify(marked, flipped)
    assert desc_sha(marked) == desc_sha(flipped), "the mark must not move the pin"
    assert mark_only("◇ a", "✦ a") and not mark_only("◇ a", "◇ b") and not mark_only("a", "a")
    marked_with_body_change = marked + "\nRun `python3 scripts/y.py`.\n"
    assert classify(SKILL_BASE, marked_with_body_change)[:2] == ("BEHAVIOUR", {"T1", "T3"})
    with tempfile.TemporaryDirectory() as td:
        cl = Path(td) / "CHANGELOG.md"
        assert any("no CHANGELOG" in e for e in check_receipt_row(cl, "ship"))
        # the near-miss that broke a plain substring test: the slug appears inside a word
        cl.write_text("# CHANGELOG\n\nnothing here yet, shipping notes elsewhere\n")
        assert any("no row naming" in e for e in check_receipt_row(cl, "ship")), \
            "a slug matching inside another word is not a receipt"
        cl.write_text("# CHANGELOG\n\n## ship v1.0.0 — flip, 12 invocations across 2 repos\n")
        assert not check_receipt_row(cl, "ship")
    # the ignorance branches: absent, unreadable, empty, all-positive, placeholder
    assert load(Path("/nonexistent/prompts.json"))[1].startswith("FAIL")
    assert any("10-20" in e for e in check_prompts([]))
    # the band scales with the arms: a nine-arm door needs 18 and is allowed 27, and the
    # 16-case corpus that read 50% on a shuffle is refused as thin rather than passed as legal
    assert band(1) == (MIN_CASES, MAX_CASES) and band(9) == (18, 27), band(9)
    assert any("18-27" in e for e in check_prompts(CASES_OK, arms=9))
    wide = CASES_OK + [dict(c, id=c["id"] + "b", prompt=c["prompt"] + " bis") for c in CASES_OK]
    assert not check_prompts(wide, arms=9), check_prompts(wide, arms=9)
    assert any("negative control" in e for e in
               check_prompts([dict(c, should_trigger=True, kind="explicit") for c in CASES_OK]))
    assert any("placeholder" in e for e in check_prompts([dict(c, prompt="TODO")
                                                          for c in CASES_OK]))
    assert not check_prompts(CASES_OK), check_prompts(CASES_OK)
    assert any("no outcome" in e for e in check_checks([{"category": "style", "cmd": "true"}]))
    assert any("CONCERNS" in e for e in check_checks([{"category": "outcome"}]))
    # the receipt does not travel across a trigger edit
    assert any("never recorded" in e for e in check_receipt(None, "d", desc_sha(edited)))
    stale = {"last_rate": 0.9, "desc_sha256": desc_sha(SKILL_BASE)}
    assert any("does not travel" in e for e in check_receipt(stale, "d", desc_sha(edited)))
    assert not check_receipt({"desc_sha256": desc_sha(edited)}, "d", desc_sha(edited))
    print("SELFCHECK OK — 14 branches: cosmetic, trigger, mark-flip, mechanism, bundle, receipt, prose, no-baseline, "
          "absent/thin/all-positive/placeholder corpus, band scaled to the arms, "
          "missing+stale+matching pin, missing+absent+present receipt row")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--skill", type=Path)
    p.add_argument("--base", help="git ref holding the previous version (default HEAD)")
    p.add_argument("--baseline", type=Path, help="previous SKILL.md, for non-git bundles")
    p.add_argument("--state", type=Path, help="ratchet state (default <skill>/references/"
                                              "ratchet-state.json)")
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not a.skill or not (a.skill / "SKILL.md").exists():
        p.error("--skill DIR must contain a SKILL.md (or use --selfcheck)")
    try:
        old, note = read_baseline(a.skill, a.base, a.baseline)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(f"not verifiable here: {e} — a gate that cannot read the previous version "
              "reports exit 2, never a green")
        return 2
    state = a.state or default_state(a.skill)
    try:
        bundle_changes = changed_bundle_paths(a.skill, a.base, a.baseline)
    except subprocess.CalledProcessError as e:
        print(f"not verifiable here: git could not enumerate bundle changes ({e}) — "
              "a gate that cannot inspect the bundle reports exit 2, never a green")
        return 2
    rc, lines = report(a.skill, old, (a.skill / "SKILL.md").read_text(), state,
                       bundle_changes)
    print(f"baseline: {note}")
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main())
