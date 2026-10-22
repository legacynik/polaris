---
name: issue-contract
description: ◇ The ONE door to the GitHub tracker, for creating, updating, deduping or grouping issues and epics. Triggers on apri una issue, file an issue or a bug, track this, triage this, accorpa sotto epic, or a handoff of an already-decomposed plan. Searches first, then enforces the founder contract on the repo's own template — never a freeform gh issue create. Not for decomposing nebulous efforts.
version: 2.0.3
user-invocable: true
auto: true
job: route any tracker request (new / extend / group) and enforce the full issue contract on whichever arm wins
when_not: nebulous efforts not yet decomposed (decompose them first); question/discussion items (repo's light form, no full contract); non-GitHub trackers (Linear); 2-minute micro-fixes nobody wants tracked; backlog surveillance on a schedule (routine lane); judging code on an approved PR (review)
lifecycle: issue GitHub reale o label di stato via gh (drenate da `ship`) o brief locale in `<repo>/.issue-contract/` o `_polaris/issues/` (drenato al primo template reale) — adapter cache in `~/.cache/issue-contract/` auto-invalidante · redundancy/dedup artifacts drenati da transition_gate.py alla scrittura · `.out-of-scope/<concept>.md` si auto-drena a ogni passata.
invokes: [bugfix, git-power]
invoked-by: [start, crasher, ambitious-goal, human]
io: riceve una richiesta tracker (nuovo item, update di #N, accorpamento) + repo-path -> dopo ricerca obbligatoria produce UNA di - issue nuova contract-complete con numero - transizione di stato gated su issue esistente - epic con figlie collegate - o un rifiuto con il pezzo mancante nominato.
status: active
---

# issue-contract

One door to the tracker. Whatever the request — new issue, update, grouping — the flow is the
same: **search first, route with the data in front of you, then act through a gate**. Nothing
reaches `gh` by hand.

## STEP 0 — Search (mandatory, before any writing)

- Code touched: Serena graph (`find_symbol`, `search_for_pattern`, `find_referencing_symbols`).
- Tracker: `gh issue list --repo <o/r> --search "<concept>" --state all --json number,title,state`.

Every path/symbol you will cite must come from this step (B15 blocks unverified references —
mark genuinely-new files `(new)`).

## STEP 1 — Route (three outcomes, decided here, never by the trigger)

| Found | Route | Mechanism |
|---|---|---|
| Nothing similar | **NEW** issue/epic | `scripts/build_issue.py` (below) |
| A partial match | **EXTEND** it — comment, add ACs, change state | `scripts/transition_gate.py` — state machine in [references/update-gate.md](references/update-gate.md) |
| Scattered pieces | **GROUP** — epic + typed children | `build_issue.py --type epic`, then `transition_gate.py` on the pieces |

If you can't say why the item deserves to exist on its own, you already have the answer: extend.

## The eight contracts (NEW arm — all enforced by `build_issue.py`, exit 2 with the missing piece)

1. **Measurable DoD** — every `--ac` needs >=2 independent signals (number / % / `code` /
   test-keyword / exit-code).
2. **Adversarial tests upfront** (`--adv-test`, >=2 executable) — run right after
   implementation, before merge/deploy.
3. **Executive** (`--exec`) — plain Italian, no backticks: the founder reads what the issue
   does without the tech part.
4. **Existence justified** (`--dedup "Searched: ... Found: ..."`) — renders as
   `## Not a duplicate because`: the STEP 0 receipt, visible in the issue. At `--apply` the
   script re-checks live and blocks on collision (extend / group / `--ack-existing`).
5. **Verified references** (B15) — every cited path exists in the repo or the item says
   `(new)`. Fabricated targets are worse than none.
6. **Domain label** (`--domain`, from `.github/DOMAINS.yml`) — renders `domain:<x>`,
   filterable. Empty glossary blocks; absent glossary warns.
7. **Priority** (`--priority p0|p1|p2|p3`).
8. **AFK eligibility** (`--afk yes|no`) — declared at birth, always: may an unattended agent
   claim this? `yes` → label `afk:eligible` (what multi-poll picks up), `no` → `afk:human`.

## NEW arm — usage

```bash
python3 scripts/parse_template.py --repo-path <repo> --json   # repo's real template (cached)
python3 scripts/build_issue.py --repo-path <repo> --repo-slug <owner/repo> \
  --type bug --title "Login 500s on empty password" \
  --ac '`POST /login` with empty password returns 400, not 500' \
  --adv-test '`pytest tests/test_login.py` (new) red before the fix, green after' \
  --adv-test '`curl -X POST /login -d "{}"` returns 400, not 500' \
  --exec "Oggi il login esplode con un errore da server quando la password è vuota." \
  --dedup "Searched: gh --search login 500; Serena find_symbol login. Found: none." \
  --domain auth --priority p1 --afk yes
# dry-run by default; --apply creates for real (autonomous chain uses --apply directly,
# human invocation confirms the dry-run first)
```

`--type` matches the repo's OWN template names (free text, never an enum). No template in the
repo → local brief with the same eight gates. No epic template → `_polaris` epic#38 shape,
declared. Details unchanged from v1.x — see [references/bypass-test.md](references/bypass-test.md).

## UPDATE arm — state, promotion, wontfix (the former `triage`)

States: `needs-triage · needs-info · ready-for-agent · ready-for-human · wontfix`. Every
promotion runs through `decide()` — a direct import is gated exactly like the CLI, and
`--apply` fuses decision + `gh issue edit` in one process:

```bash
python3 scripts/transition_gate.py --to <state> --apply --issue-number <n> --repo <o/r> \
  [--issue-json snap.json] --redundancy-file red.md [--reason ...] [--out-of-scope-file ...]
```

`ready-for-agent` and `wontfix rejected-*` REQUIRE `--issue-json` (unverifiable = blocked).
Promotion to `ready-for-agent` posts the brief ([references/agent-brief.md](references/agent-brief.md))
and dispatches `bugfix`. Prior rejections live in `.out-of-scope/`
([references/out-of-scope.md](references/out-of-scope.md)). Full shape and bypass proof:
[references/update-gate.md](references/update-gate.md), [references/bypass-test-update.md](references/bypass-test-update.md).

## When NOT to use

- **Nebulous efforts** not yet decomposed ("sistemare l'auth") → decompose first: name the
  outcome (`ambitious-goal`), split it into issues that each carry a measurable DoD, then return here.
- **Question/discussion items** (grilling) → the repo's light form; the full contract would
  push people back to freeform.
- **Non-GitHub trackers** (Linear) → that tracker's native tool.
- **2-minute micro-fixes** nobody wants tracked — process for its own sake is the opposite defect.
- **Scheduled backlog surveillance** (alarms, stale scans) → routine lane, not
  this skill's lifecycle.
- **Judging code on an approved PR** → `review`.

## What this gate cannot stop

A freeform `gh issue create`, direct API calls or the web UI bypass these scripts entirely.
Closing that needs the repo layer: contract-aligned issue forms (required fields + dropdowns
generated from `DOMAINS.yml`) and a retroactive CI check flagging non-conforming issues
(nag, never a block) — tracked in the seeding package, not faked here.

## Bypass-test

`references/bypass-test.md` — Tests 1–8 (v1.0.0) + B9–B16 (founder contract 2026-08-16),
each with before/after output and version. `references/bypass-test-update.md` — the update
arm's 14 fail-closed proofs. `--selfcheck` on both scripts replays everything offline in <1s.
