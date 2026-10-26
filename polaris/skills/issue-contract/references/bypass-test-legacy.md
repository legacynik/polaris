---
title: bypass-test — issue-contract
description: The tests that MUST fail (exit != 0) if someone bypasses the build_issue.py gate.
status: active
---

# Bypass-test

The gate is `scripts/build_issue.py`. It is hardened only if **there is no way to obtain a
`gh issue create` command (or a local brief) without having satisfied a measurable DoD + the fields
required by the real template**. The tests below cover the measured ways in which the founder's 4 repos
bypass a template that does exist today (acme-api 91.8% freeform, acme-web 0/708 with the default
label).

## Test 1 — a non-measurable acceptance criterion must block

```bash
cd skills-suite/issue-contract
D=$(mktemp -d) && mkdir -p "$D/.github/ISSUE_TEMPLATE"
cat > "$D/.github/ISSUE_TEMPLATE/config.yml" <<'EOF'
blank_issues_enabled: false
EOF
cat > "$D/.github/ISSUE_TEMPLATE/bug.yml" <<'EOF'
name: Bug report
labels: ["bug"]
body:
  - type: textarea
    id: acceptance-criteria
    attributes: {label: Acceptance criteria}
    validations: {required: true}
EOF
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" --ac "va bene, ci penso"
echo "exit=$?"   # DEVE essere 2, non 0
```

**What a bypass would prove**: if this exits `0`, the gate accepts a non-verifiable criterion
("va bene" — the failure class the PRD names explicitly, "plans/issues without a
backbone") and the gate is decorative.

## Test 2 — an unfilled `required: true` field of the real template must block

Same `$D` as above:

```bash
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" --ac "\`GET /x\` returns 200"
echo "exit=$?"   # DEVE essere 2 — manca il campo acceptance-criteria compilato via --field
```

`build_issue.py` maps `--ac` onto the `acceptance`/`criteria` alias (see `FIELD_ALIASES`), so
this test actually PASSES (`--ac` fills the field by itself). To really force the hole, use a
template with a field that has NO known alias (e.g. `id: security-gate-triage`, measured on a real
acme-web `feat-medium.yml`):

```bash
cat > "$D/.github/ISSUE_TEMPLATE/bug.yml" <<'EOF'
name: Bug report
labels: ["bug"]
body:
  - type: textarea
    id: acceptance-criteria
    attributes: {label: Acceptance criteria}
    validations: {required: true}
  - type: textarea
    id: security-gate-triage
    attributes: {label: Security-gate triage}
    validations: {required: true}
EOF
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" --ac "\`GET /x\` returns 200"
echo "exit=$?"   # DEVE essere 2 — security-gate-triage non ha alias e non è stato passato
```

**What a bypass would prove**: if this exits `0`, the gate generates an issue that lacks a field that
the repo's template declares mandatory — the same shape as G2 (a `required` gate that is only
structural), which the registry measures on the 4 repos, reproduced here.

## Test 3 — a type with no match + `blank_issues_enabled: false` must not fall back to freeform

```bash
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type nonexistent-type --title "x" --ac "\`GET /x\` returns 200"
echo "exit=$?"   # DEVE essere 2, mai 0 con un gh-command silenzioso senza template
```

**What a bypass would prove**: if this exits `0` and still produces a `gh issue
create` command, the script ignored the repo's explicit declaration ("no blank issues") — it is
exactly the measured fact that GitHub itself applies that flag ONLY to the web UI, never to `gh`/API:
if we do not apply it here, nobody ever does.

## Test 4 — an empty/whitespace-only `--field` on a required field must not pass

Test 2 covers only "field not passed". Found for real in an adversarial audit
(Bypass B): a `--field id=` that was present but empty was accepted as "filled" because the
check was "the key is in the dict", not "the value has content".

```bash
cd skills-suite/issue-contract
D=$(mktemp -d) && mkdir -p "$D/.github/ISSUE_TEMPLATE"
cat > "$D/.github/ISSUE_TEMPLATE/config.yml" <<'EOF'
blank_issues_enabled: false
EOF
cat > "$D/.github/ISSUE_TEMPLATE/bug.yml" <<'EOF'
name: Bug report
labels: ["bug"]
body:
  - type: textarea
    id: acceptance-criteria
    attributes: {label: Acceptance criteria}
    validations: {required: true}
  - type: textarea
    id: repro
    attributes: {label: Repro steps}
    validations: {required: true}
EOF
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" --ac "\`GET /x\` returns 200" --field "repro="
echo "exit=$?"   # DEVE essere 2, non 0
```

**What a bypass would prove**: if this exits `0`, the issue is born with an empty "Repro steps"
section that the template declares mandatory — exactly what Test 2 should already prevent,
only with a slightly different input (empty instead of absent).

## Test 5 — a single cosmetic signal in the AC must not be enough

Found for real in an adversarial audit (Bypass A): the original regex accepted
any isolated digit/backtick/keyword, even inside vague prose identical to "va bene, ci penso"
(Test 1, which blocks).

```bash
for ac in "lo sistemiamo entro il 2026, ci penso io" \
          "faccio un test e vedo come va" \
          'sistemare `quella cosa` prima possibile'; do
  python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
    --type bug --title "Fix it" --ac "$ac" --refresh
  echo "exit=$?"   # DEVE essere 2 per tutte e tre — 0 segnali di sostanza, solo cosmesi
done
```

**What a bypass would prove**: if any of the three exits `0`, the measurability gate tells
"contains a random digit/word" apart from "contains a verifiable criterion" only on paper.

## Test 6 — `--field` must not be able to overwrite the already-validated Acceptance Criteria field

Found for real in a lateral adversarial audit A (high severity): if the id of the AC field
in the template also matches a `--field`, the value written into the issue was the one from
`--field`, never passed through `validate_acs()` — a measurable `--ac` passed the gate, but the final
body contained a different text, never validated.

```bash
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" \
  --ac "\`GET /x\` returns 200" \
  --field acceptance-criteria="va bene, ci penso, chissene" --refresh
echo "exit=$?"   # DEVE essere 2 — non deve MAI scrivere "va bene, ci penso" nel corpo
```

**What a bypass would prove**: if this exits `0`, the issue body literally contains a
non-measurable string while `validate_acs()` approved something else entirely — the validated value and the
shipped value are two different things; the gate protects data that is not what comes out.

## Test 7 — a direct call to the function must be gated as much as the CLI

Found in the corpus (a general hole, a lateral adversarial audit C): a script with a gated
`main()`/`build()` but public module functions with no guard leaves a direct import
free to produce the same forbidden output, without ever going through `validate_acs()`.

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import build_issue as bi
template = {'file':'bug.yml','fields':[{'id':'acceptance-criteria','label':'Acceptance criteria','required':True}],'labels':['bug']}
body, missing = bi.compile_form(template, {'acs': ['va bene, ci penso'], 'scope_out':'', 'summary':''}, {})
assert body is None and missing, 'BYPASS: import diretto ha prodotto un body senza passare dal gate'
print('PASS: compile_form() rifiuta esattamente come la CLI')
"
```

**What a bypass would prove**: if `body` is not `None`, there is a way to obtain the issue body
without ever validating the AC — the CLI becomes an optional pass-through, not the only way.

## Test 8 — an Epic with a duplicate title must block without `--ack-existing`

F10/G7#6: an Epic whose DoD/title mirrors one already open must be rejected until it is
explicitly confirmed. Verified at the `apply_gate()` level (unit, not through a real
`--apply` — no network in this test):

```bash
python3 -c "
import sys, json; sys.path.insert(0, 'scripts')
import build_issue as bi
from argparse import Namespace
def dup(_a): return json.dumps([{'number': 5, 'title': 'Epic dup', 'state': 'OPEN', 'url': 'https://x/5'}])
ns = Namespace(type='epic', slug='acme/api', title='Dup epic', ack_existing=False)
msg = bi.apply_gate(ns, dup)
assert msg is not None, 'BYPASS: Epic duplicato creato senza --ack-existing'
print('PASS:', msg.splitlines()[0])
"
```

**What a bypass would prove**: if `apply_gate` returns `None` with a duplicate found, the Epic
is created anyway — exactly the hole G7#6 names ("a DoD that overlaps with capabilities that
already exist").

## B9 — an issue without a list of adversarial tests must block

fails_before: issue-contract v1.0.0 (founder contract 2026-08-16: the list of adversarial checks
is written BEFORE the implementation and run before merge/deploy)

```bash
cd skills-suite/issue-contract
D=$(mktemp -d) && mkdir -p "$D/.github/ISSUE_TEMPLATE"
cat > "$D/.github/ISSUE_TEMPLATE/bug.yml" <<'EOF'
name: Bug report
labels: ["bug"]
body:
  - type: textarea
    id: acceptance-criteria
    attributes: {label: Acceptance criteria}
    validations: {required: true}
EOF
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api --type bug \
  --title "Login 500s on empty password" \
  --ac '`POST /login` with empty password returns 400, not 500' --refresh
echo "exit=$?"
```

**Expected BEFORE (v1.0.0)**: exit `0` — the bypass SUCCEEDS. Output observed 2026-08-16:
`DRY-RUN ... template: bug.yml ... exit=0`.
**Expected AFTER**: exit `2` with a message that names the missing adversarial tests
(`--adv-test`, at least 2, each measurable).
**Observed AFTER (v1.1.0, 2026-08-16)**: exit `2` — `BLOCKED — issue contract / template fields: adversarial tests (B9): >=2 required, written BEFORE the work starts (--adv-test ...)`.

## B10 — an issue without an executive summary (plain Italian) must block

fails_before: issue-contract v1.0.0. Same command as B9.

**Expected BEFORE (v1.0.0)**: exit `0` — observed 2026-08-16 (same run as B9).
**Expected AFTER**: exit `2` with a message that asks for `--exec` (a plain explanation for the
founder, without technical jargon).
**Observed AFTER (v1.1.0, 2026-08-16)**: exit `2` — `executive summary (B10): --exec with a plain-language explanation (italiano semplice, >=20 chars)`.

## B11 — a NON-epic duplicate must block at --apply without --ack-existing

fails_before: issue-contract v1.0.0 (apply_gate was scoped to epics only).

```bash
python3 -c "
import sys, json; sys.path.insert(0, 'scripts')
import build_issue as bi
from argparse import Namespace
def dup(_a): return json.dumps([{'number': 7, 'title': 'Login 500s on empty password', 'state': 'OPEN', 'url': 'https://x/7'}])
ns = Namespace(type='bug', slug='acme/api', title='Login 500s on empty password', ack_existing=False)
print('apply_gate =', bi.apply_gate(ns, dup))
"
```

**Expected BEFORE (v1.0.0)**: `apply_gate = None` — the duplicate bug passes. Observed 2026-08-16.
**Expected AFTER**: `apply_gate` returns the BLOCKED message with the list of candidates, for
EVERY type, not only epic.
**Observed AFTER (v1.1.0, 2026-08-16)**: `apply_gate = BLOCKED — F10/G7#6/B11: possible duplicate issue(s): #7 ...` on type=bug.

## B12 — an issue without an architectural domain label must block

fails_before: issue-contract v1.0.0. Same command as B9.

**Expected BEFORE (v1.0.0)**: exit `0` — observed 2026-08-16 (same run as B9); the produced
`gh` command carries only `--label bug`, no `domain:*`.
**Expected AFTER**: exit `2` without `--domain`; with `--domain` the `gh` command carries
`domain:<value>`; if the repo has a glossary (`.github/DOMAINS.yml` or `CONTEXT.md`, the
contract of the `domain` gate), a domain outside the glossary blocks with the list of valid ones.
**Observed AFTER (v1.1.0, 2026-08-16)**: exit `2` without `--domain`; with the full contract the gh command carries `--label bug,domain:auth,p1`.

## B13 — an issue without a priority must block

fails_before: issue-contract v1.0.0. Same command as B9.

**Expected BEFORE (v1.0.0)**: exit `0` — observed 2026-08-16 (same run as B9).
**Expected AFTER**: exit `2` without `--priority`; only `p0|p1|p2|p3` is accepted, rendered as a label.
**Observed AFTER (v1.1.0, 2026-08-16)**: exit `2` — `priority (B13): --priority p0|p1|p2|p3`.

## B14 — the dedup must be VISIBLE in the issue, not just executed

fails_before: issue-contract v1.1.0 (blind judge 2026-08-16: R4 dedup 0/6 — even the runs WITH the
skill did the search but the issue carried no trace of it).

Command: the same as B9 with the full contract (adv-test, exec, domain, priority) but without
`--dedup`.

**Expected BEFORE (v1.1.0)**: exit `0` — observed 2026-08-16.
**Observed AFTER (v1.2.0, 2026-08-16)**: exit `2` — `dedup evidence (B14): --dedup "Searched:
<where/query>. Found: <none|#N>"`. Even the form without Searched/Found ("ho controllato,
fidati") blocks. An honest limit inherited from triage/check_redundancy: it proves the FORM of the
search and makes it visible, never its truth.

## B15 — an invented reference must block (anti-fabrication)

fails_before: issue-contract v1.2.0 (blind judge 2026-08-16: an epic with numbers and paths never
verified against the code, "a template filled in with fake numbers is worse than a messy document
that tells the truth").

Command: full contract with `--ac '\`compute_margin()\` in src/billing/margin_engine.py
returns 48.00, not 42.00'` on a repo where that file does NOT exist.

**Expected BEFORE (v1.2.0)**: exit `0` — observed 2026-08-16.
**Observed AFTER (v2.0.0)**: exit `2` — `unverified reference (B15): 'src/billing/margin_engine.py'
not found in the repo — verify it against the code (Serena) or mark the item '(new)'`.
The `(new)` marker in the item declares a file that will be created (TDD: the test is red first) and passes.
Without repo_root (direct import) the check is fail-closed, not skipped.

## B16 — AFK eligibility must be declared at creation, always

fails_before: issue-contract v1.2.0 (founder 2026-08-16: "I generate 200 issues, 60% are
AFK but nobody remembers to mark it because there is another, separate skill that gets forgotten").

Command: full contract without `--afk`.

**Expected BEFORE (v1.2.0)**: exit `0` — observed 2026-08-16.
**Observed AFTER (v2.0.0)**: exit `2` — `AFK eligibility (B16): --afk yes|no`. With `--afk yes`
the gh command carries the label `afk:eligible` (what the autonomous poller picks up); with `--afk no`
it carries `afk:human`. Out-of-vocabulary (`--afk boh`) blocks.

## Plan case B1 (narrative DoD) — NONEXISTENT defect, reported

The plan 2026-08-16-skill-issue-unica assumed B1 "a narrative DoD passes today". False already in
v1.0.0: Test 1 + Test 5 above block it (`validate_acs`, >=2 independent signals). Per the
GATE 2 rule of the SPEC-MADRE the case is not "cured": it is already covered, and that is declared.

## Automatic execution

The branches above (Tests 1-8 + B9-B16) are also inside `scripts/build_issue.py --selfcheck` (in-memory fixtures,
zero network, zero real mutation, redundancy gate tested via a direct `apply_gate()` — never
through a real `--apply`) — runs in <1s, no `gh` invoked:

```bash
python3 scripts/build_issue.py --selfcheck
python3 scripts/parse_template.py --selfcheck
```

If either exits non-zero, the gate itself is broken — not merely bypassable.

## Known limit, not closable by this script

None of the tests above covers — because it cannot — a freeform `gh issue create`, a direct API call
or the GitHub web UI: they bypass this script entirely, without touching it. See
"Cosa questo gate NON può impedire" in `SKILL.md`. It is not a bypass of THIS gate (it does not
go through here); it is the structural limit of every gate that lives in a script instead of a hook —
declared here because a bypass-test that stayed silent about this would imply broader coverage
than the real one.

## Feature refinement routing (2.2.0)

A feature whose outcome, scope or DoD is unclear goes to `plan` (2.4.1; `ambitious-goal`
was absorbed there on 2026-10-24), and the issue links the plan file. A clear feature contract
passes through directly. A routine bug or mechanical ticket skips refinement. Neither
route activates a goal runtime or changes ownership. Behavioural checks:
[plan bypass-test](../../plan-area/references/bypass-test.md).
Legacy script tests above do not prove this conversational routing.
