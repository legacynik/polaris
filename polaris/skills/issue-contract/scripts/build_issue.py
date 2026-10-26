#!/usr/bin/env python3
"""Build a repo-template-compliant issue body, or refuse to (the gate: meccanismo,
non prosa). Blocks on non-measurable acceptance criteria, unfilled repo-required
fields, whitespace-only overrides, an override that tries to silently replace the
validated AC content, and (for epics) a live duplicate found on GitHub.
Dry-run by default; --apply is the only path that touches `gh` — never in
--selfcheck (no network, ever, in this script).

Gate lives in one place per shape (compile_form / compile_legacy / compile_local_brief):
fill + validate + render happen in the SAME function, so importing and calling it
directly (skipping main()/build()/the CLI entirely) is exactly as gated as running
the script — there is no separate un-gated render primitive left to call instead
(EVAL-issue-contract-bypass.md Laterale C).

    build_issue.py --repo-path P --type bug|feature|task|epic --title T --ac "..." \
        --adv-test "..." --adv-test "..." --exec "..." --dedup "Searched: ... Found: ..." \
        --domain <area> --priority p0|p1|p2|p3 --afk yes|no \
        [--ac ...] [--scope-out "..."] [--field id=value ...] [--repo-slug o/r] \
        [--ack-existing] [--apply]
    build_issue.py --selfcheck
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import parse_template as pt  # noqa: E402

# Four independent signal categories, not one blob: a single stray digit/backtick/
# keyword used to be enough (EVAL-issue-contract-copertura.md Bypass A — "entro il
# 2026, ci penso io" has a digit, "faccio un test" has the keyword, "`quella cosa`"
# has a backtick — none of them state a verifiable criterion). Requiring >=2
# independent categories keeps every AC already in SKILL.md/selfcheck passing
# (they all carry a code span + a number) while blocking a single cosmetic token.
# ponytail: still a heuristic, not semantic understanding — "test 1" (keyword+number)
# would pass despite being vague. Upgrade path: wire a real NL check if this proves
# gameable in practice; not worth the weight for a sub-second offline CLI gate today.
MEASURABLE_SIGNALS = {
    "number": re.compile(r"\d"),
    "percent": re.compile(r"%"),
    "code": re.compile(r"`[^`]+`"),
    # "exit code" alone missed the real-world forms "exit 1" / "esce 1" / "exit=0"
    # (taratura 2026-08-16, final gate on polaris-os#64 — a genuinely measurable DoD
    # written as "rifiuta con exit 1" scored 1 signal and was wrongly refused)
    "keyword": re.compile(r"\b(test|pytest|assert|endpoint|status|returns?|curl|http"
                          r"|exit(\s+code|\s*=?\s*\d)|esce\s+\d)\b", re.I),
}
FIELD_ALIASES = {"acceptance": "ac", "criteria": "ac", "out.of.scope": "scope_out",
                  "out-of-scope": "scope_out", "scope": "scope_out",
                  "motivation": "summary", "summary": "summary", "context": "summary",
                  "description": "summary", "user.story": "summary",
                  "executive": "exec_summary", "category": "category", "impact": "impact",
                  "cost": "cost",
                  # A template may ask for the contract's own fields (field report 2026-10-09):
                  # the flags that already carry them fill them, never a second --field.
                  "duplicate": "dedup", "adversarial": "adv_tests", r"\bdomain\b": "domain",
                  r"\bpriority\b": "priority", r"\bafk\b": "afk"}
# The contract's own fields: validated from their flags, so a template field asking for one is
# filled from the flag and an override that says something else is refused (breaker 2026-10-09).
CONTRACT_FLAGS = {"dedup": "--dedup", "adv_tests": "--adv-test", "domain": "--domain",
                  "priority": "--priority", "afk": "--afk"}
PRIORITIES = ("p0", "p1", "p2", "p3")
# #482 (founder 2026-09-26): an issue is born with WHAT it is and HOW MUCH it is worth,
# so the backlog can be ordered and experiments/ideas can expire instead of piling up.
CATEGORIES = ("blocca", "bug", "miglioria", "esperimento", "idea")
IMPACTS = ("1", "2", "3")
COSTS = ("S", "M", "L")
# Founder contract 2026-08-16 (B9-B13): every issue carries adversarial tests written
# BEFORE the work, a plain executive summary, a domain label from the repo glossary,
# and a priority. Optional glossary file: .github/DOMAINS.yml (one domain per line).
GLOSSARY_FILE = Path(".github") / "DOMAINS.yml"

# F1/G7#6: nessuna delle 4 repo misurate ha un .github/ISSUE_TEMPLATE/epic.*, ma
# _polaris HA gia' una convenzione epic (#38) mai formalizzata come template — questo
# e' quella convenzione, adattata come fallback quando la repo non ne ha una propria
# (mai al posto di una reale: pick_template preferisce sempre un match vero).
EPIC_FALLBACK = {
    "kind": "legacy",
    "file": "<convenzione _polaris epic#38, nessun template epic reale nella repo>",
    "name": "Epic (convenzione _polaris — nessun .github/ISSUE_TEMPLATE/epic.* qui)",
    "labels": ["epic"],
    "sections": [{"header": h} for h in
                 ("Executive", "Context", "Technical", "Acceptance criteria",
                  "Out of scope", "Domain")],
}


def _signal_count(text: str) -> int:
    return sum(1 for pat in MEASURABLE_SIGNALS.values() if pat.search(text))


def validate_acs(acs: list[str]) -> list[str]:
    if not acs:
        return ["serve almeno 1 acceptance criterion misurabile (--ac)"]
    return [f"AC non misurabile (servono >=2 segnali indipendenti fra numero/%/`codice`/"
            f"keyword-test, trovati {_signal_count(a)}): {a!r}"
            for a in acs if _signal_count(a) < 2]


def load_domain_vocab(repo_path: Path) -> list[str] | None:
    """None = repo declares no glossary (any non-empty domain accepted, warned).
    An existing-but-empty glossary returns [] and blocks everything: that is a repo
    bug to surface, not a pass (fail-closed)."""
    p = repo_path / GLOSSARY_FILE
    if not p.exists():
        return None
    return re.findall(r"^\s*-?\s*([a-z0-9][a-z0-9_-]*)\s*$", p.read_text(errors="replace"), re.M)


def validate_contract(brief: dict) -> list[str]:
    """B9-B13 in one surface, called by every compile_* path — a direct import is
    exactly as gated as the CLI, same rule as the AC gate (Laterale C)."""
    errs = []
    advs = brief.get("adv_tests") or []
    if len(advs) < 2:
        errs.append("adversarial tests (B9): >=2 required, written BEFORE the work starts "
                    "(--adv-test \"...\") — they run right after implementation, before merge/deploy")
    errs += [f"adversarial test not executable (needs >=2 signals like `command`/number/keyword, "
             f"found {_signal_count(t)}): {t!r}" for t in advs if _signal_count(t) < 2]
    ex = (brief.get("exec_summary") or "").strip()
    if len(ex) < 20:
        errs.append("executive summary (B10): --exec with a plain-language explanation "
                    "(italiano semplice, >=20 chars) the founder reads without the tech part")
    elif "`" in ex:
        errs.append("executive summary (B10) must stay plain — no code spans/backticks in --exec")
    dom = (brief.get("domain") or "").strip()
    vocab = brief.get("domains_vocab")
    if not dom:
        errs.append("domain label (B12): --domain <area> from the repo's architectural glossary")
    elif vocab is not None and dom not in vocab:
        errs.append(f"domain {dom!r} (B12) not in the repo glossary {GLOSSARY_FILE}: {vocab}")
    if brief.get("priority") not in PRIORITIES:
        errs.append("priority (B13): --priority p0|p1|p2|p3")
    dd = (brief.get("dedup") or "").strip()
    # Sibling check: transition_gate.check_redundancy validates the same Searched/Found
    # shape on a FILE (10-char floor there, 20 here) — if you touch one, look at the other.
    # Same honest limit as triage's check_redundancy: this proves the FORM of a
    # search happened and makes it visible in the issue, never that it was truthful.
    if len(dd) < 20 or "searched" not in dd.lower() or "found" not in dd.lower():
        errs.append("dedup evidence (B14): --dedup \"Searched: <where/query>. Found: <none|#N>\" "
                    "— the search must be visible in the issue, not just performed")
    afk = (brief.get("afk") or "").strip().lower()
    # B16 (founder 2026-08-16): a separate afk-labeling skill = the field everyone
    # forgets. Declared at birth, always: can this run unattended? Feeds multi-poll.
    if afk not in ("yes", "no"):
        errs.append("AFK eligibility (B16): --afk yes|no — declare at birth whether an "
                    "unattended agent may claim this (yes -> label afk:eligible)")
    return errs + check_weight(brief) + check_refs(brief)


def check_weight(brief: dict) -> list[str]:
    """B17/B18 (#482): category and weight are declared at birth, never guessed later."""
    errs = []
    if (brief.get("category") or "").strip() not in CATEGORIES:
        errs.append(f"category (B17): --category {'|'.join(CATEGORIES)}")
    if (brief.get("impact") or "").strip() not in IMPACTS:
        errs.append("impact (B18): --impact 1|2|3 — how much time it saves or risk it removes")
    if (brief.get("cost") or "").strip() not in COSTS:
        errs.append("cost (B18): --cost S|M|L — one session, a few sessions, a week")
    return errs


PATHLIKE = re.compile(r"\b[\w./-]+/[\w.-]+\.\w{1,4}\b|\b[\w-]+\.(?:py|ts|tsx|js|jsx|go|rs|sql|sh|ya?ml|json|md)\b")


def check_refs(brief: dict) -> list[str]:
    """B15 anti-fabrication (blind-judge 2026-08-16): every file/path cited in an AC
    or adversarial test either exists in the repo or the item declares '(new)'.
    No repo_root (direct import) = cannot verify = fail closed, not open.
    ponytail: per-item '(new)' excuses ALL refs in that item — including a mixed
    item citing one real and one fabricated path ('a.py exists, b.py (new)'); per-token
    adjacency would fight pytest's file::test syntax. Tighten if this proves gamed."""
    root = brief.get("repo_root")
    errs = []
    for txt in list(brief.get("acs") or []) + list(brief.get("adv_tests") or []):
        if "(new)" in txt:
            continue
        for m in PATHLIKE.finditer(txt):
            tok = m.group(0)
            if root and (Path(root) / tok).exists():
                continue
            errs.append(f"unverified reference (B15): {tok!r} not found in the repo — "
                        f"verify it against the code (Serena) or mark the item '(new)' if it will be created")
    return errs


def _declares_exec(template: dict) -> bool:
    items = template.get("fields") or [(s["header"], s["header"]) for s in template.get("sections", [])]
    pairs = [(f["id"], f["label"]) if isinstance(f, dict) else f for f in items]
    return any(_alias_for(a, b) == "exec_summary" for a, b in pairs)


def contract_sections(brief: dict, carried: frozenset = frozenset()) -> tuple[str, str]:
    """The contract blocks the template does not already carry (`carried` = their aliases)."""
    tests = "\n".join(f"- [ ] {t}" for t in brief["adv_tests"])
    tail = ([] if "dedup" in carried else [f"## Not a duplicate because\n\n{brief['dedup'].strip()}\n"]) \
        + ([] if "adv_tests" in carried else
           [f"## Adversarial verification (run before merge/deploy)\n\n{tests}\n"])
    return f"## Executive\n\n{brief['exec_summary'].strip()}\n", "\n".join(tail)


def contract_labels(brief: dict) -> list[str]:
    afk = "afk:eligible" if brief["afk"].strip().lower() == "yes" else "afk:human"
    weight = f"peso:{brief['impact'].strip()}{brief['cost'].strip()}"
    return [f"domain:{brief['domain'].strip()}", brief["priority"], afk,
            f"cat:{brief['category'].strip()}", weight]


def pick_template(manifest: dict, type_: str, override: str | None) -> tuple[dict | None, str | None]:
    if override:
        hit = next((t for t in manifest["templates"] if t["file"] == override), None)
        return hit, None
    matches = [t for t in manifest["templates"]
               if type_.lower() in (t["name"] + t["file"]).lower()]
    if matches:
        warn = None
        if len(matches) > 1:
            warn = f"{len(matches)} template combaciano con '{type_}' ({[t['file'] for t in matches]}), preso {matches[0]['file']} — passa --template per scegliere"
        return matches[0], warn
    if "epic" in type_.lower():
        return EPIC_FALLBACK, ("nessun template epic nella repo — uso la convenzione "
                                "_polaris epic#38 (Executive/Context/Technical/Acceptance "
                                "criteria/Out of scope/Domain), non un bug/feature/task a caso")
    return None, None


def _alias_for(field_id: str, label: str) -> str | None:
    key = f"{field_id} {label}".lower()
    for pat, alias in FIELD_ALIASES.items():
        if re.search(pat, key):
            return alias
    return None


def compile_form(template: dict, brief: dict, overrides: dict) -> tuple[str | None, list[str]]:
    """Fill + validate + render a form template in one call — no separate render
    primitive exists to call around this, so a direct import is gated too (Laterale C)."""
    filled, missing = {}, validate_contract(brief)
    for f in template["fields"]:
        alias = _alias_for(f["id"], f["label"])
        if alias == "ac":
            if f["id"] in overrides:
                missing.append(f"{f['id']} — l'Acceptance Criteria si passa con --ac, non "
                                f"--field (ignorato di proposito, non sovrascritto in silenzio)")
                continue
            problems = validate_acs(brief["acs"])
            if problems:
                missing.append("AC: " + "; ".join(problems))
                continue
            filled[f["id"]] = "\n".join(f"- [ ] {a}" for a in brief["acs"])
            continue
        if alias in CONTRACT_FLAGS:
            v = brief.get(alias) or ""
            v = "\n".join(f"- [ ] {t}" for t in v) if isinstance(v, list) else v.strip()
            if f["id"] in overrides and overrides[f["id"]].strip() != v:
                missing.append(f"{f['id']} — si passa con {CONTRACT_FLAGS[alias]}, non --field: il "
                               f"corpo non puo' dire altro dal valore validato (e dalle label)")
                continue
            if v:
                filled[f["id"]] = v
            elif f["required"]:
                missing.append(f"{f['id']} ({f['label']}) — passa {CONTRACT_FLAGS[alias]}")
            continue
        val = overrides.get(f["id"], "").strip()
        if val:
            filled[f["id"]] = val
        elif alias and brief.get(alias):
            filled[f["id"]] = brief[alias]
        elif f["required"]:
            missing.append(f"{f['id']} ({f['label']}) — passa --field {f['id']}=\"...\"")
    if missing:
        return None, missing
    carried = frozenset(_alias_for(f["id"], f["label"]) for f in template["fields"] if f["id"] in filled)
    head, tail = contract_sections(brief, carried)
    if _declares_exec(template):
        head = ""  # the template's own Executive field already carries it
    body = "\n".join(f"### {f['label']}\n\n{filled[f['id']]}\n"
                      for f in template["fields"] if f["id"] in filled)
    return f"{head}\n{body}\n{tail}".strip("\n") + "\n", []


def compile_legacy(template: dict, brief: dict, overrides: dict) -> tuple[str | None, list[str]]:
    """Same contract as compile_form for legacy .md sections (headers instead of
    field ids) — including the epic fallback shape, so an Epic gets the exact same
    AC-override-block + measurability gate as a real repo template."""
    filled, missing = {}, validate_contract(brief)
    known = {"scope_out": brief.get("scope_out", ""), "summary": brief.get("summary", ""),
             "exec_summary": brief.get("exec_summary", "")}
    for s in template["sections"]:
        header = s["header"]
        key = header.lower()
        alias = _alias_for(key, key)
        if alias == "ac":
            if key in overrides:
                missing.append(f"## {header} — l'Acceptance Criteria si passa con --ac, non "
                                f"--field (ignorato di proposito, non sovrascritto in silenzio)")
                continue
            problems = validate_acs(brief["acs"])
            if problems:
                missing.append(f"## {header}: " + "; ".join(problems))
                continue
            filled[header] = "\n".join(f"- [ ] {a}" for a in brief["acs"])
            continue
        val = overrides.get(key, "").strip()
        if val:
            filled[header] = val
        elif alias and known.get(alias):
            filled[header] = known[alias]
        else:
            missing.append(f"## {header} — passa --field \"{key}\"=\"...\"")
    if missing:
        return None, missing
    head, tail = contract_sections(brief)
    if _declares_exec(template):
        head = ""  # the template's own Executive section already carries it
    return (f"{head}\n" + "\n\n".join(f"## {h}\n\n{v}" for h, v in filled.items())
            + f"\n\n{tail}").strip("\n") + "\n", []


def compile_local_brief(title: str, type_: str, brief: dict) -> tuple[str | None, list[str]]:
    """Repo without .github/ISSUE_TEMPLATE — same AC + contract gate, gated here (not
    only by build()'s caller) so a direct import can't skip the no-template path either."""
    problems = validate_acs(brief["acs"]) + validate_contract(brief)
    if problems:
        return None, problems
    ac_block = "\n".join(f"- [ ] {a}" for a in brief["acs"])
    head, tail = contract_sections(brief)
    return (f"---\ntitle: {title}\ntype: {type_}\nstatus: open\n"
            f"domain: {brief['domain'].strip()}\npriority: {brief['priority']}\n---\n\n"
            f"# {title}\n\n{head}\n## Acceptance criteria\n{ac_block}\n\n"
            f"## Out of scope\n{brief['scope_out'] or '(none declared)'}\n\n{tail}"), []


def slugify(title: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", title.lower())).strip("-") or "issue"


def local_brief_path(repo_path: Path, title: str) -> Path:
    base = repo_path / "_polaris" / "issues" if (repo_path / "_polaris").is_dir() else repo_path / ".issue-contract"
    return base / f"{slugify(title)}.md"


def gh_command(repo_slug: str, title: str, body_file: Path, labels: list[str]) -> list[str]:
    cmd = ["gh", "issue", "create", "--repo", repo_slug, "--title", title, "--body-file", str(body_file)]
    if labels:
        cmd += ["--label", ",".join(labels)]
    return cmd


def real_gh_list(args: list[str]) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else "[]"


def find_existing(slug: str, title: str, runner=real_gh_list) -> list[dict]:
    raw = runner(["issue", "list", "--repo", slug, "--search", title,
                  "--state", "all", "--limit", "5", "--json", "number,title,state,url"])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def apply_gate(args, runner=real_gh_list) -> str | None:
    """F10/G7#6 + B11 (founder contract 2026-08-16): ANY issue whose title collides
    with one already open must refuse at apply-time (the only moment this needs a
    real `gh` read) unless the caller explicitly acknowledges it with --ack-existing.
    Was epic-only in v1.0.0; the founder's dedup rule covers every type. Reuses the
    shape proven in wayfinder/scripts/redundancy_check.py (F10); kept self-contained
    per SKILL-STANDARD.
    ponytail: fails OPEN if `gh` itself is unreachable (real_gh_list swallows the
    error to "[]") — a hard network requirement to create ANY issue would break the
    tool for a founder who is non-dev on infra; upgrade when this proves exploited.
    """
    if args.ack_existing:
        return None
    dups = find_existing(args.slug, args.title, runner)
    if not dups:
        return None
    lines = "\n".join(f"  #{d.get('number')} {d.get('title')} ({d.get('state')}) {d.get('url')}"
                       for d in dups)
    return (f"BLOCKED — F10/G7#6/B11: possible duplicate issue(s):\n{lines}\n\n"
            f"Three routes: EXTEND the existing issue (transition_gate.py / update arm), "
            f"GROUP under its epic, or pass --ack-existing only if genuinely new.")


def build(args, manifest: dict) -> tuple[int, str]:
    brief = {"acs": args.ac, "scope_out": args.scope_out, "summary": args.summary,
             "adv_tests": args.adv_test, "exec_summary": args.exec_summary,
             "domain": args.domain, "priority": args.priority, "dedup": args.dedup,
             "repo_root": str(args.repo_path), "afk": args.afk,
             "category": getattr(args, "category", ""), "impact": getattr(args, "impact", ""),
             "cost": getattr(args, "cost", ""),
             "domains_vocab": load_domain_vocab(args.repo_path)}
    overrides = dict(f.split("=", 1) for f in args.field)
    vocab_warn = ("⚠ no .github/DOMAINS.yml in repo — --domain accepted unvalidated; add the "
                  "glossary to enforce it\n" if brief["domains_vocab"] is None else "")

    if not manifest["templates"]:
        body, problems = compile_local_brief(args.title, args.type, brief)
        if problems:
            return 2, "BLOCKED — issue contract:\n" + "\n".join(f"  - {p}" for p in problems)
        path = local_brief_path(args.repo_path, args.title)
        if args.apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        return 0, f"{vocab_warn}repo senza .github/ISSUE_TEMPLATE — brief locale a {path}\n{'(scritto)' if args.apply else '(dry-run, passa --apply per scrivere)'}\n\n{body}"

    template, warn = pick_template(manifest, args.type, args.template)
    if template is None:
        if not manifest["blank_issues_enabled"]:
            names = [t["file"] for t in manifest["templates"]]
            return 2, f"BLOCCATO — nessun template combacia con '{args.type}' e blank_issues_enabled: false. Template disponibili: {names}. Passa --template <file>."
        template, warn = manifest["templates"][0], f"nessun match per '{args.type}', repo permette blank issue: preso {manifest['templates'][0]['file']} comunque"

    compile_fn = compile_form if template["kind"] == "form" else compile_legacy
    body, missing = compile_fn(template, brief, overrides)
    if missing:
        return 2, "BLOCKED — issue contract / template fields:\n" + "\n".join(f"  - {m}" for m in missing)

    labels = template.get("labels", []) + contract_labels(brief)
    cmd = gh_command(args.slug, args.title, Path("<body-file>"), labels)
    out = (f"{vocab_warn}{'⚠ ' + warn + chr(10) if warn else ''}template: {template['file']}\ncomando: {' '.join(cmd)}\n\n{body}")
    if args.apply:
        gate_msg = apply_gate(args)
        if gate_msg:
            return 2, gate_msg
        tmp = args.repo_path / ".issue-contract-body.tmp.md"
        tmp.write_text(body)
        real_cmd = gh_command(args.slug, args.title, tmp, labels)
        r = subprocess.run(real_cmd, cwd=args.repo_path)
        tmp.unlink(missing_ok=True)
        return r.returncode, out
    return 0, "DRY-RUN (passa --apply per creare davvero)\n" + out


def selfcheck() -> int:
    from argparse import Namespace
    manifest = {"blank_issues_enabled": False, "templates": [{
        "kind": "form", "file": "bug.yml", "name": "Bug", "labels": ["bug"],
        "fields": [{"id": "acceptance-criteria", "label": "Acceptance criteria", "required": True},
                   {"id": "repro", "label": "Repro steps", "required": True}]}]}
    base = dict(repo_path=Path("/tmp/x"), slug="acme/api", title="t", type="bug",
                scope_out="", summary="", field=[], template=None, apply=False,
                ack_existing=False, ac=["`GET /x` returns 201"],
                adv_test=["`pytest tests/test_x.py` (new) red before the fix, green after",
                          "`curl /x` with empty body returns 400, not 500"],
                exec_summary="Sistema l'endpoint che oggi risponde con un errore sbagliato.",
                domain="auth", priority="p1",
                dedup="Searched: gh issue list --search + Serena find_symbol. Found: none.", afk="yes",
                category="bug", impact="2", cost="S")

    def run(m, **over):
        return build(Namespace(**{**base, **over}), m)

    code, msg = run(manifest, ac=["fixes it"])
    assert code == 2 and "non misurabile" in msg, "non-measurable AC must block"
    code, msg = run(manifest)
    assert code == 2 and "repro" in msg, "unfilled required field must block"
    code, msg = run(manifest, field=["repro=steps here"])
    assert code == 0 and "### Repro steps" in msg, "filled field must pass and render"
    assert "## Executive" in msg and "## Not a duplicate because" in msg and "## Adversarial verification" in msg, \
        "contract sections must render (B9/B10)"
    assert "domain:auth" in msg and "p1" in msg and "afk:eligible" in msg, "domain+priority+afk labels must reach the gh command (B12/B13/B16)"

    # B9-B13 (founder contract 2026-08-16) — each missing piece must block on its own
    code, msg = run(manifest, field=["repro=x"], adv_test=[])
    assert code == 2 and "adversarial" in msg, "B9: no adversarial tests must block"
    code, msg = run(manifest, field=["repro=x"], adv_test=["`pytest` red then green 1"])
    assert code == 2 and "adversarial" in msg, "B9: a single adversarial test is not a list"
    code, msg = run(manifest, field=["repro=x"],
                     adv_test=["check it works fine", "`pytest tests` red before, green after 1"])
    assert code == 2 and "not executable" in msg, "B9: a vague adversarial test must block"
    code, msg = run(manifest, field=["repro=x"], exec_summary="")
    assert code == 2 and "executive" in msg.lower(), "B10: missing executive must block"
    code, msg = run(manifest, field=["repro=x"], exec_summary="Vedi `fix_gate.py` e il resto della PR")
    assert code == 2 and "plain" in msg, "B10: executive with code spans is not plain language"
    code, msg = run(manifest, field=["repro=x"], domain="")
    assert code == 2 and "domain" in msg, "B12: missing domain must block"
    code, msg = run(manifest, field=["repro=x"], priority="high")
    assert code == 2 and "p0|p1|p2|p3" in msg, "B13: priority outside p0-p3 must block"
    code, msg = run(manifest, field=["repro=x"], priority="")
    assert code == 2 and "p0|p1|p2|p3" in msg, "B13: missing priority must block"
    code, msg = run(manifest, field=["repro=x"], dedup="")
    assert code == 2 and "dedup" in msg.lower(), "B14: missing dedup evidence must block"
    code, msg = run(manifest, field=["repro=x"], dedup="ho controllato, fidati, nulla di simile")
    assert code == 2 and "dedup" in msg.lower(), "B14: dedup without Searched/Found form must block"
    code, msg = run(manifest, field=["repro=x"], ac=["`src/ghost_module.py` returns 200 on `GET /x`"])
    assert code == 2 and "B15" in msg, "B15: a cited path that does not exist must block"
    code, msg = run(manifest, field=["repro=x"], ac=["`src/ghost_module.py` (new) returns 200 on `GET /x`"])
    assert code == 0, "B15: '(new)' declares the file will be created and passes"
    VALID_BRIEF = {"acs": ["`GET /x` returns 201"], "scope_out": "", "summary": "",
                   "adv_tests": ["`python3 build_issue.py --selfcheck` exits 0"],
                   "exec_summary": "Frase semplice abbastanza lunga per il founder.",
                   "domain": "auth", "priority": "p1",
                   "dedup": "Searched: x y z. Found: none.", "afk": "yes", "category": "bug", "impact": "2", "cost": "S",
                   "repo_root": str(Path(__file__).parent)}
    ok_brief = dict(VALID_BRIEF)
    assert not check_refs(ok_brief), "B15: a path that DOES exist in the repo passes"
    assert check_refs({**ok_brief, "repo_root": None}), "B15: no repo_root = cannot verify = fail closed"
    code, msg = run(manifest, field=["repro=x"], afk="")
    assert code == 2 and "B16" in msg, "B16: missing AFK declaration must block"
    code, msg = run(manifest, field=["repro=x"], afk="boh")
    assert code == 2 and "B16" in msg, "B16: AFK outside yes|no must block"
    code, msg = run(manifest, field=["repro=x"], afk="no")
    assert code == 0 and "afk:human" in msg, "B16: afk=no renders the afk:human label"

    # B12 glossary membership — vocab present and domain outside it must block, even
    # on a direct compile_* call (single gated surface)
    bad_brief = {**VALID_BRIEF, "adv_tests": base["adv_test"], "domain": "web",
                 "domains_vocab": ["auth", "billing"]}
    body, missing = compile_form(manifest["templates"][0], bad_brief, {"repro": "x"})
    assert body is None and any("glossary" in m for m in missing), \
        "B12: domain outside the glossary must block"
    assert not validate_contract({**bad_brief, "domain": "billing"}), \
        "a domain inside the glossary passes"
    assert validate_contract({**bad_brief, "domain": "web", "domains_vocab": []}), \
        "an existing-but-empty glossary blocks (fail-closed), never passes"
    code, msg = run(manifest, type="docs")
    assert code == 2 and "blank_issues_enabled" in msg, "no-match + blank-forbidden must block"
    code, msg = run({**manifest, "blank_issues_enabled": True}, type="docs", field=["repro=x"])
    assert code == 0 and "nessun match" in msg, "no-match + blank-allowed must fall back with warning"
    code, msg = run({"blank_issues_enabled": True, "templates": []})
    assert code == 0 and "brief locale" in msg, "no templates at all must use local brief fallback"

    legacy = {"blank_issues_enabled": True, "templates": [{
        "kind": "legacy", "file": "feature.md", "name": "Feature", "labels": [],
        "sections": [{"header": "Acceptance criteria"}, {"header": "Domain"}]}]}
    code, msg = run(legacy, type="feature")
    assert code == 2 and "## Domain" in msg, "unmapped legacy section must still block, not keep a placeholder"
    code, msg = run(legacy, type="feature", field=["domain=billing"])
    assert code == 0 and "billing" in msg, "legacy section filled via --field must pass"

    # Bypass B (EVAL-copertura §3.2) — whitespace-only override must not satisfy 'required'
    code, msg = run(manifest, field=["repro=   "])
    assert code == 2 and "repro" in msg, "whitespace-only --field must not count as filled"
    code, msg = run(legacy, type="feature", field=["domain=   "])
    assert code == 2 and "## Domain" in msg, "same bypass on the legacy shape must also block"

    # Laterale A (EVAL-bypass §3) — --field on the AC-aliased id must be an explicit
    # error, never a silent swap of validated content
    code, msg = run(manifest, field=["acceptance-criteria=va bene, ci penso, chissene"])
    assert code == 2 and "--ac, non --field" in msg, "an override on the AC field id must be rejected explicitly"
    code, msg = run(legacy, type="feature", field=["acceptance criteria=va bene, ci penso"])
    assert code == 2 and "--ac, non --field" in msg, "same on the legacy AC section"

    # Bypass A (EVAL-copertura §3.2) — single cosmetic signal must still block
    for bad in ("lo sistemiamo entro il 2026, ci penso io",
                "faccio un test e vedo come va",
                "sistemare `quella cosa` prima possibile"):
        assert validate_acs([bad]), f"single-signal cosmetic AC must still block: {bad!r}"
    assert not validate_acs(["50% coverage"]), "two real signals (number+percent) must pass"
    assert not validate_acs(["la skill rifiuta con exit 1 una issue senza DoD misurabile"]), \
        "'exit 1' is a command-verifiable criterion (taratura polaris-os#64)"
    assert not validate_acs(["`POST /login` con password vuota risponde 400, non 500"]), \
        "code span + number must pass (SKILL.md's own example)"

    # Rule 3 (orchestrator) — direct import must be exactly as gated as the CLI: no
    # ungated render primitive left to call around compile_form/compile_legacy/compile_local_brief
    body, missing = compile_form(manifest["templates"][0],
                                  {"acs": ["fixes it"], "scope_out": "", "summary": ""}, {})
    assert body is None and missing, "direct compile_form() call must refuse non-measurable AC"
    body, missing = compile_form(manifest["templates"][0],
                                  {"acs": ["`GET /x` returns 200"], "scope_out": "", "summary": ""},
                                  {"acceptance-criteria": "va bene, ci penso"})
    assert body is None and missing, "direct compile_form() call with an AC override must refuse too"
    body, missing = compile_legacy(legacy["templates"][0],
                                    {"acs": ["fixes it"], "scope_out": "x", "summary": ""}, {})
    assert body is None and missing, "direct compile_legacy() call must gate AC too"
    body, problems = compile_local_brief("t", "bug", {"acs": ["fixes it"], "scope_out": "",
                                                       "adv_tests": [], "exec_summary": "",
                                                       "domain": "", "priority": "", "dedup": "", "afk": "",
                                                       "domains_vocab": None})
    assert body is None and problems, "direct compile_local_brief() call must gate AC too (no-template repos)"

    # Epic fallback (F1/G7#6, NON-COPRE half) — no epic.* in the repo still produces
    # the real _polaris epic#38 shape, not a silent bug/feature/task degrade
    code, msg = run(manifest, type="epic", ac=["fixes it"])
    assert code == 2 and "AC" in msg, "epic fallback still gates measurability"
    code, msg = run(manifest, type="epic")
    assert code == 2 and "Technical" in msg, "epic fallback requires its own sections, not the bug template's"
    code, msg = run(manifest, type="epic",
                     field=["executive=why", "technical=how", "domain=billing"],
                     scope_out="perf work excluded", summary="what this covers")
    assert code == 0 and "## Executive" in msg and "## Domain" in msg, "epic fallback renders when filled"

    # F10/G7#6 + B11 redundancy gate — unit-tested on apply_gate() directly (never
    # through build()+--apply) so selfcheck never risks a real subprocess/gh call
    def dup(_a): return json.dumps([{"number": 5, "title": "Epic dup", "state": "OPEN", "url": "https://x/5"}])
    ns = Namespace(type="epic", slug="acme/api", title="Dup epic", ack_existing=False)
    assert apply_gate(ns, dup) is not None, "epic with a found duplicate must block without --ack-existing"
    assert apply_gate(Namespace(**{**vars(ns), "ack_existing": True}), dup) is None, \
        "--ack-existing clears the duplicate gate"
    assert apply_gate(Namespace(**{**vars(ns), "type": "bug"}), dup) is not None, \
        "B11: the duplicate gate covers EVERY type now, not just epic"
    def nodup(_a): return "[]"
    assert apply_gate(Namespace(**{**vars(ns), "type": "bug"}), nodup) is None, \
        "no duplicates found → no block"

    print("SELFCHECK OK — 47 rami provati: AC non misurabile, campo mancante, campo compilato, "
          "blank-vietato+no-match, blank-permesso+no-match, nessun template, sezione legacy non "
          "mappata, sezione legacy compilata, override vuoto (form+legacy), override sul campo AC "
          "(form+legacy), AC cosmetico x3, AC con 2 segnali x2, chiamata diretta gated x4, epic "
          "fallback x3, redundancy-gate x4 (B11 tutti i tipi), contratto founder B9-B13 x11 "
          "(adv-test assenti/singolo/vago, executive assente/non-plain, domain assente/fuori "
          "glossario/glossario-vuoto, priority assente/invalida, dedup assente/senza-forma (B14), riferimenti inventati/(new)/esistenti/no-root (B15), AFK assente/invalida/no->afk:human (B16), render+label)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-path", type=Path); ap.add_argument("--repo-slug", dest="slug")
    ap.add_argument("--type")  # free text on purpose: matched against the REPO's own template names, never a fixed enum
    ap.add_argument("--title")
    ap.add_argument("--ac", action="append", default=[]); ap.add_argument("--scope-out", dest="scope_out", default="")
    ap.add_argument("--summary", default=""); ap.add_argument("--field", action="append", default=[])
    ap.add_argument("--adv-test", dest="adv_test", action="append", default=[],
                     help="adversarial test to run before merge/deploy — >=2 required, written BEFORE the work (B9)")
    ap.add_argument("--exec", dest="exec_summary", default="",
                     help="plain-Italian executive summary for the founder (B10)")
    ap.add_argument("--domain", default="", help="architectural-domain label from the repo glossary (B12)")
    ap.add_argument("--priority", default="", help="p0|p1|p2|p3 (B13)")
    ap.add_argument("--afk", default="", help="yes|no — may an unattended agent claim this? (B16)")
    ap.add_argument("--category", default="", help="|".join(CATEGORIES) + " (B17)")
    ap.add_argument("--impact", default="", help="1|2|3 (B18)")
    ap.add_argument("--cost", default="", help="S|M|L (B18)")
    ap.add_argument("--dedup", default="",
                     help='visible dedup evidence: "Searched: <where/query>. Found: <none|#N>" (B14)')
    ap.add_argument("--template"); ap.add_argument("--apply", action="store_true")
    ap.add_argument("--ack-existing", dest="ack_existing", action="store_true",
                     help="conferma esplicita che un Epic con candidati duplicati NON lo è (F10/G7#6)")
    ap.add_argument("--refresh", action="store_true"); ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not (a.repo_path and a.type and a.title):
        ap.error("--repo-path, --type and --title are required (or --selfcheck)")
    a.repo_path = a.repo_path.resolve()
    manifest = pt.load_or_build(a.repo_path, a.refresh)
    code, msg = build(a, manifest)
    print(msg)
    return code

if __name__ == "__main__":
    sys.exit(main())
