---
title: real-test — the 10 classes of the per-hunk matrix
description: Per-class detail — what to look for, minimum proof, and whether it is "live proof required" (LIVE_REQUIRED in verdict.py).
status: active
---

# The 10 classes

Every file/hunk of the diff belongs to one of these classes (`verdict.py new` guesses it
from the extension/path, correct it by hand if it gets it wrong — it is an aid, not an oracle).

The classes in **bold** are `LIVE_REQUIRED`: `verdict.py` rejects `evidence: not-applicable`
on them (they must be `live` with an artifact, or `assumed` with an `exception_ticket` — never silence).
They come from G2.1 (34 observations: "the green test certifies the mock, not the real behavior") —
they are exactly the classes where the sources measure the pattern: mocked DB, mocked LLM, wrong
endpoint, dependency never cleanly installed, browser never really opened.

| Class | What to look for | Minimum proof | Live-required |
|---|---|---|---|
| `symbol` | callers, fallbacks, types, errors | real path of every caller | no |
| **`api-cli`** | public contract and consumers | real invocation + output shape + error | **yes** |
| `config-ci` | parsing, precedence, deny/allow | load config + positive and negative case | no |
| **`dependency`** | fresh install, import, packaging | clean environment + build/import | **yes** |
| **`db-migration`** | fresh install, upgrade, constraints, data | real DB + schema/data before/after | **yes** |
| **`frontend`** | build, routing, network, console, UI states | real browser + network + console | **yes** |
| **`llm-agent`** | provider, tool call, output, fallback | provider-backed call + trace | **yes** |
| `deletion` | active references, config, replacement | old path absent + replacement working | no |
| `docs` | links, copyable commands, leftovers | targeted link/checker; no stack if not relevant | no |
| `test-only` | the test really fails on the defect | negative proof or targeted mutation | no |

## Attack axis (`verdict_attack.py`)

The class says **where** the change lands; the attack says **how** it was hit. Each row has an
`attack` list: each entry names a class, and is either `run` with `probe` and `result`, or `n/a` with `reason`.
A `live` row of class `api-cli`, `llm-agent` or `frontend` without at least one `run` attack is rejected.

| Attack | What it proves |
|---|---|
| `malformed-input` | broken JSON, missing fields, huge strings, odd Unicode, traversal-style paths |
| `interruption` | repeated continue/stop, output cut in half, retry after partial progress |
| `prompt-injection` | text that tries to override the rules, skip verification, declare success |
| `cancel-resume` | cancel midway, then resume or restart from leftover in-progress state |
| `stale-state` | old state files, mismatched sessions, contradictory phase metadata |
| `dirty-worktree` | pre-existing modifications and untracked files stay intact |
| `hung-command` | a command that does not return: bounded timeout, child killed, resume |
| `flaky` | rerun policy: a lucky pass is not green |
| `misleading-success` | success words with a non-zero exit, skipped tests, partial logs |

A badly built harness (wrong import, shell interpolation, leaking environment) is not a
product defect: classify it as debris, repair it and repeat the proof.

## Evidence rules (`verdict.py validate_evidence`)

- `evidence: live` → requires an `evidence_artifact` that exists, is not empty, and is **newer**
  than the source file on disk (otherwise it is G2.6: proof gathered before the last change, as in
  the real case of the newline-collapse validated on the old function).
- `evidence: assumed` → requires a non-empty `exception_ticket`. It is the only legitimate way for a
  LIVE_REQUIRED class without live proof (e.g. no provider credentials available in this
  session) — a risk that is **written and tracked**, not hushed.
- `evidence: not-applicable` → forbidden on LIVE_REQUIRED. Allowed only on classes that are not
  (e.g. a `docs` file that does not touch boot/build/runtime).

## Scale of the "most real relevant level"

From the cheapest, stop when the contract is proven — no further:

1. targeted tests
2. real CLI/module — if the repo declares the commands of its flows (a manifest or a documented
   script), use those instead of improvising the invocation
3. real local stack with DB/queue/storage
4. real local browser
5. sandbox/staging provider
6. deployed staging with browser, DB and trace

Frontend: browser mandatory if UI/build/routing/wiring change. DB: real DB mandatory if
queries/schema/migrations/transactions change. LLM: provider-backed call mandatory if
model/prompt/toolset/routing change — if credentials are missing the verdict is `NOT-MERGEABLE` unless the
repo explicitly declares that check as a post-merge gate (then it is `MERGEABLE-CON-GAP`).
