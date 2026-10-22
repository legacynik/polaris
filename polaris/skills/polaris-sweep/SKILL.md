---
name: polaris-sweep
description: ◇ Polaris Sweep — review a single PR end-to-end and post a durable comment. Used by autonomous trigger (cron polling new PRs), or invoked as `claude -p "/polaris-sweep <PR_N>"` in a fresh session.
version: 1.5.0
user-invocable: true
status: active
effort: medium
job: revisionare una PR con tre lenti + ledger + attestazione runtime, e decidere con un exit code se può fondersi da sola
when_not: non usarla per issue (solo PR), per PR non Hand-authored (skip silenzioso), per deployare o mettere codice su staging, né per bocciare una PR perché non è su staging — «nessuno l'ha deployata» non è prova di regressione
io: riceve un numero di PR aperto → produce un commento di review idempotente sulla PR + run-state in _polaris/sweep/runs/ + verdetto auto-merge via scripts/sweep_gate.py (exit code)
lifecycle: il commento vive sulla PR (upsert per marker, mai duplicato); il run-state lo drena la sweep successiva sulla stessa PR; .tmp/sweep/ si pulisce a raccolta avvenuta
invokes: [real-testing]
invoked-by: [cron, human]
---

# Polaris Sweep — review a single PR

## Bundled resources

| File | Purpose |
|---|---|
| `scripts/sweep_gate.py` | **The auto-merge decision** (Phase 4.5): exit 0 consente, 1 nega, 2 errore d'uso. Fail-closed. `--selfcheck`: 13 controlli |
| `references/BUG-HISTORY.md` | **Read first when modifying this skill.** 3 bugs from 2026-04-28 (sweep-pending jq filter, claude binary path, auto-merge trigger gap) in adjacent layers, plus the 2026-07-26 entry — 4 stacked failures in Phase 3c's own Codex invocation, a clamped tool timeout mistaken for a hang, and a truncated-diff prompt. Phase 3c's flags all come from that entry; read it before touching them. |
| `references/quality-review.md` | The Phase 3a checks and output shape — read before every quality review |
| `references/codex-flags.md` | The why-per-flag table of the Phase 3c invocation — read before changing ANY flag |
| `references/comment-template.md` | The exact Phase 4 comment template + Verified-clean rules (marker and Verdict line are load-bearing) |
| `references/conflict-resolution.md` | **Load lazily** — only when Phase 1.5 reports `mergeable=CONFLICTING`. Decision tree for auto-rebase vs escalate. Keeps the default tick cheap (no extra context tokens) for the common case of mergeable PRs. |
| `references/bypass-test.md` | B1–B3 (verdetto su codice mai eseguito · PR che tocca la pipeline · verdetto su SHA stale) con output prima/dopo |

The verdict-format eval is load-bearing: auto-merge GHA's gate regex (`Verdict.*✅[[:space:]]+approve`) depends on it. Don't change the verdict format without updating the gate regex (lives in `.github/workflows/auto-merge-trivial.yml` of each repo using Sweep).

## Pre-conditions
1. Cwd is the target repo (or `gh repo set-default` is configured).
2. `gh auth status` is clean.
3. Argument `<PR_N>` is a numeric PR number that's open and Hand-authored.

## Phase 1 — Gather

```bash
PR_DATA=$(gh pr view "$PR_N" --json url,title,body,headRefName,additions,deletions,changedFiles,labels,author,mergeable)
PR_DIFF=$(gh pr diff "$PR_N")
```

## Phase 1.5 — Conflict gate (NEW)

Inspect `.mergeable`. If `CONFLICTING`, the diff that Phase 3 would review is against a stale base — Phase 3a/3b/3c are partially meaningless until the rebase succeeds.

```bash
MERGEABLE=$(echo "$PR_DATA" | jq -r '.mergeable')
if [ "$MERGEABLE" = "CONFLICTING" ]; then
    echo "PR #$PR_N is CONFLICTING — loading conflict resolution playbook"
    # Read references/conflict-resolution.md and follow the decision tree:
    # - trivial behind → auto-rebase + push
    # - auto-resolvable → -X theirs + flag
    # - real conflict  → label needs-human-rebase + Telegram alert
    # Then EXIT this tick. On the next sweep tick, the PR will either be
    # mergeable (rebase succeeded → flow continues to Phase 2) or still
    # CONFLICTING with `needs-human-rebase` label (skip to avoid loop).
    exit 0
fi
```

Skip the conflict gate entirely (do not load the reference) when `MERGEABLE` is `MERGEABLE` or `UNKNOWN` — keeps the common-case tick fast.

## Phase 1.7 — Real-test receipt check (nag, never a block)

If the repo opted in to the real-testing gate (`.real-test/enabled` exists in the local
checkout), check whether a verdict exists for THIS PR's head:

```bash
HASH=$(python3 "<polaris>/real-testing/scripts/perimeter.py" --repo <checkout> --head <pr-head-sha> --hash-only)
test -f "<checkout>/.real-test/verdicts/$HASH.json" || echo "no receipt"
```

No receipt (or a verdict that fails `verdict.py validate`) → add ONE line to the review
comment: *"⚠ Nessuna ricevuta real-test per l'hash di questa PR (`<hash8>`) — il diff non
risulta provato dal gate."* This is a NAG by design (lessons 2026-08-13: mandatory CI gates
on existing repos kill adoption): it makes the missing receipt visible on the PR, it never
blocks. Repos without the marker: skip silently — they never opted in.

## Phase 2 — Read repo profile

```bash
PROFILE_FILE="_polaris/sweep/repos/<repo-slug>.md"
# Read severity_threshold from frontmatter (default: high)
```

The profile is **optional**. Most repos have never been onboarded to Sweep —
`_polaris/sweep/` is often absent. A missing
profile means `severity_threshold=high` and nothing else; note it in one line and
continue. Never create a profile implicitly, and never stall waiting for one.

## Phase 3 — Run review

### Phase 3a — Quality review

Review `git diff <merge-base>..<head>` against the PR's stated intent, in a fresh-context
subagent if your harness supports one, otherwise inline, read-only on the checkout. Apply every
check in `references/quality-review.md` and return its output: strengths, findings by severity
(each with `file:line`, what is wrong, why it matters) and approve / approve-with-minor /
request-changes. Done when every check has a verdict and the verdict line is written.

### Phase 3a-bis — Over-engineering lens (threshold-gated, NEVER blocking alone)

Only when the diff is large enough for over-engineering to hide in — **additions > 100 lines**
(from Phase 1's `additions`) — read the diff once for over-engineering only: reinvented stdlib, speculative abstraction, duplicated shapes,
oversized functions. Field precedent (2026-08-17): three real findings of exactly
this class — duplicated helper, 26-line function, 4 params — that the correctness lenses had
no reason to catch.

Rules: findings land in the comment as **judgement calls** under `## Findings`, they NEVER
flip the verdict by themselves, and they never run on small diffs (a 5-line fix gets zero
friction). If simplification fixes are applied after green, the receipts re-open by
construction: real-testing receipts are content-hashed and `sweep_gate` denies on a changed
SHA — green and mutation re-run, mechanically, not by discipline.

### Phase 3b — Security review

Review the diff for security. Check each of:
1. Secrets/credentials hardcoded or logged
2. Input validation missing at API boundaries
3. SQL/command injection vectors
4. Auth/authorization gaps
5. Error messages leaking sensitive info
6. PII in logs or responses

If any finding is Critical or High severity → override final verdict to `request-changes` regardless of Phase 3a result.

### Phase 3b-bis — Decision-conformance check (highest-yield lens, do not skip)

Grep the repo's own ledger for decisions the diff touches, and read the ones that match:

```bash
grep -niE "<domain words from the diff: logging|retention|auth|region|PII|…>" \
  _polaris/decisions.md | head
```

A diff can be clean code and still be a **regression against a ratified decision** —
which no generic quality or security lens will catch, because the rule lives in the
ledger, not the code. This is the single highest-value finding class Sweep produces.

Concrete precedent (2026-07-26): the code was well-written and well-tested,
but logged merchant legal names, UBO names and screening outcomes to CloudWatch, against
`decisions.md` 2026-07-14 §3 *"no personal data in operational logs by design"* — a rule
agreed with the client and load-bearing for a GDPR-erasure claim. Both external lenses
missed it; only reading the ledger surfaced it. When you find one, quote the decision
verbatim with its date, and say what the decision's own stated rationale loses.

Treat a decision regression as **High minimum**, and name the three ways out:
comply, amend the decision deliberately, or narrow it (often the rule is stricter than
the underlying requirement — e.g. an outcome logged without a name is pseudonymous).

### Phase 3s — Spec-conformance: does the diff implement the ORIGINATING ISSUE? (do not skip)

The lens no other phase covers: 3a judges quality, 3b security, 3b-bis the decision ledger —
none of them asks whether the PR does **what the issue asked**. An unattended agent can produce
a clean, secure, well-tested PR that implements the wrong thing; without this lens it
self-merges.

1. Resolve the originating issue: `Closes #N`/`Fixes #N` in the PR body, issue refs in commit
   messages, or the branch name. Loop PRs always carry one — `issue-contract` (B9) guarantees
   every `afk:eligible` issue is born with a measurable DoD, so for the AFK class the spec
   source ALWAYS exists.
2. Read the issue's DoD checkboxes / acceptance criteria. Verify each against the diff and the
   evidence (receipts, run logs), and report per item: **met / partial / missing / creep**
   (behaviour nobody asked for), quoting the issue line.
3. Verdict rules: a REQUIRED DoD item missing → **request-changes** (the work is literally not
   done — this is not a judgement call) · partial-but-declared (the record says so, e.g.
   `MERGEABLE-CON-GAP`) → High finding, blocks auto-merge, human decides · scope creep →
   judgement call, never blocking alone. No issue found and the PR is not a chore/docs class →
   say so in the comment: an unattended PR without an originating issue is itself a finding.
4. Field precedent (2026-08-17): the spec lens is what caught an issue closed riding another
   fix's evidence without its own gate, and the honestly-open DoD item —
   findings no quality or security lens had a reason to see.

For manual pre-PR use in a session, the `review` skill covers this same axis
(plus Standards) — this phase absorbs its Spec axis into the unattended pipeline; it does not
replace the manual tool.

### Phase 3c — Codex adversarial review

The invocation below needs only the `codex` CLI. Model truth: `gpt-5.6-sol` —
every `-codex` id 400s on ChatGPT accounts.

**The invocation below is load-bearing. The previous version of this phase failed
every one of four separate ways in a single real run (2026-07-26 —
see `references/BUG-HISTORY.md`, which stays here: it is this phase's incident history).
Do not "simplify" it back.**

Write the diff to a file **inside the repo** and point Codex at the path. Do NOT
paste the diff into the prompt, and never `head -500` it — that silently discarded
87% of a 4k-line diff while still reading like a completed review.

```bash
mkdir -p .tmp/sweep
gh pr diff "$PR_N" > .tmp/sweep/pr-$PR_N.diff

cat > .tmp/sweep/schema.json <<'EOF'
{"type":"object","additionalProperties":false,
 "properties":{
   "findings":{"type":"array","items":{"type":"object","additionalProperties":false,
     "properties":{"severity":{"type":"string","enum":["critical","high","medium","low"]},
       "title":{"type":"string"},"file":{"type":"string"},"line":{"type":"integer"},
       "description":{"type":"string"},"suggestion":{"type":"string"}},
     "required":["severity","title","file","line","description","suggestion"]}},
   "summary":{"type":"string"},"approved":{"type":"boolean"}},
 "required":["findings","summary","approved"]}
EOF
```

Prompt requirements — the last block is not optional:

```
Adversarial pre-merge review of PR #<N>. The diff is at .tmp/sweep/pr-<N>.diff.
Read it, then read the source files it touches plus their direct callers/guards —
the diff alone is not enough to judge correctness.
CUSTOM RULES (OpenAI custom-code-review-rules pattern): read the repo's AGENTS.md
files whose directory covers the touched files (root AGENTS.md + any nested one),
apply every rule under their "Code Review Rules" sections, and CITE the rule
verbatim in any finding it motivates. A rule violation is High minimum — these
encode invariants reviewers repeatedly had to explain.
Be skeptical: assume the code is wrong until proven otherwise. For each finding give
the concrete failure scenario (inputs/state -> wrong outcome), not a generic concern.
No style preferences. Set approved=false if any critical/high finding stands.

HARD CONSTRAINTS — violating these wastes the run:
- Do NOT run tests, pytest, vitest, npm, python, or any build/execution command.
  This is READ-ONLY: read files, nothing else.
- Do NOT attempt network access.
- Read only the touched files and their direct callers, not the whole tree.
- Emit the JSON result as your FINAL message and stop. Do not keep exploring
  after you have findings.
```

Then run it **detached, with stdin closed, under a hard timeout**:

```bash
nohup timeout 900 codex exec \
  --json \
  --sandbox read-only \
  --skip-git-repo-check \
  --output-schema .tmp/sweep/schema.json \
  --output-last-message .tmp/sweep/codex-$PR_N.json \
  "$(cat .tmp/sweep/prompt-$PR_N.md)" \
  < /dev/null > .tmp/sweep/run-$PR_N.log 2>&1 &
```

`--json` makes the run log a JSONL event trace (OpenAI eval-skills pattern): after collection,
one deterministic process-check earns its keep — did Codex actually READ the touched files?

```bash
jq -rs '[.[] | select(.item.type=="command_execution") | .item.command] | join("\n")' \
  .tmp/sweep/run-$PR_N.log | grep -cF -f <(gh pr diff "$PR_N" --name-only) \
  || echo "⚠ Codex never opened the touched files — treat its findings as diff-only"
```

A review whose trace never opened the source is a diff-skim wearing a review's clothes — say so
in the comment instead of trusting it. Token usage lives in the trace's `turn.completed` events.

Each flag earns its place — the why-per-flag table (all four failures observed live) is in
`references/codex-flags.md`: read it before changing ANY flag of this invocation.

Then collect, with a log fallback:

```bash
# Preferred: the schema-validated file
jq -r '.findings[] | "[\(.severity|ascii_upcase)] \(.title) (\(.file):\(.line))"' \
  .tmp/sweep/codex-$PR_N.json 2>/dev/null

# Fallback: findings sometimes exist only in the run log, which is ANSI-encoded —
# plain grep matches nothing, `grep -a` does.
grep -a -oE '"severity":\s*"[a-z]+"|\[(CRITICAL|HIGH|MEDIUM|LOW)\][^"]{0,160}' \
  .tmp/sweep/run-$PR_N.log
```

If Codex finds Critical/High → override verdict to `request-changes`.
**Verify each Codex finding against the source before reporting it** — it mixes real
bugs with false alarms, and the value is in the reproduction, not the claim.

Clean up `.tmp/sweep/` only after the run is collected (Codex reads from it).

### Phase 3c-fallback — when Codex does not run: a Standards + Spec pass takes the lens

If Codex times out, is killed, or returns nothing, **do not stall the sweep, do not
promise a later update, and do not degrade to two lenses**: run the two passes of the
`review` skill (`review/references/protocol.md`) on the changes since the merge-base with
main as the replacement adversarial lens — Standards (repo's documented coding standards)
and Spec (does the diff match the originating issue), each in its own fresh-context
subagent if your harness supports one, otherwise one after the other, inline. That keeps
the independence Codex was providing: a reviewer that did not write the code.

Map its findings into the same severity buckets, verify them against source like any
Codex finding, and mark provenance in the comment:

```
## Codex adversarial

- ⚠️ **Codex not-run** — <one line: timed out after N min / zero output / CLI unavailable>.
  Lens replaced by the Standards + Spec fallback:
- 🔴 [High] <finding from the fallback> …
```

Record `codex: not-run (<reason>) · fallback: standards-spec` in the Phase 6 run state.
Only if the fallback ALSO fails, post the two-lenses banner: *"This review is
therefore two lenses, not three. Treat the finding list as unverified-complete, not
exhaustive"* — a degraded review that says so is useful; one that silently looks
complete is worse than none.

### Phase 3e — Attestazione runtime (l'unica lente che ESEGUE il codice)

3a, 3b, 3b-bis e 3c **leggono**. Nessuna di loro fa girare una riga. Una PR può uscire da qui con
`approve` senza che nessuno abbia visto il codice funzionare — ed è la ragione per cui esistono PR
dichiarate real-testate che non lo sono: la revisione era ottima, e riguardava un testo.

Questa fase non prova che il codice sia bello: prova che **è successo qualcosa nel mondo**.

**Non deploya e non confronta SHA.** Chi fa il real test lo dice: **cerca il suo commento sulla PR.**
Inseguire lo SHA servito da staging è fragile e non serve — staging cambia sotto i piedi, e un
commit che coincide non prova che qualcuno abbia guardato qualcosa.

```bash
gh pr view "$PR_N" --json comments -q '.comments[] | select(.body | test("(?i)real.?test|attestazione")) | .body' | head -c 3000
```

Due domande, in quest'ordine:

**1. Questa PR va deployata?** Il repo lo dichiara già, e la lista **non si scrive qui**: sta nel
`paths:` del suo workflow di post-deploy, oppure in `deployabili:` del suo `.fix/contract.yml`. Ogni
repo ha i suoi. Se il diff non tocca nessuno di quei path — doc, spec, contratto di sessione,
githooks — **l'attestazione non serve**: dillo e chiudi la fase.

Se il repo non dichiara né l'uno né l'altro, non indovinare: scrivi che il perimetro deployabile non
è dichiarato, e trattala come da attestare. Un elenco di path inventato qui varrebbe per una repo
sola e mentirebbe su tutte le altre.

**2. Esiste il commento del real test?** Cioè un commento che dichiara **cosa è stato provato e
dove**, non «testato ok».

| | Cosa scrivi |
|---|---|
| non serve | **non deployabile** — nessun path di runtime toccato |
| c'è | **attestata** — riporta in una riga cosa dice: dove è girata, cosa si è osservato, cosa è caduto |
| non c'è | **non attestata** — questo codice non è mai stato eseguito da nessuna parte |

**Il verdetto della sweep non cambia per questa fase.** Non essere attestata non è un difetto del
codice: è un lavoro che manca. Cambia solo l'auto-merge, in Phase 4.5.

### Phase 3d — Merge all verdicts

Final verdict = worst-of(3a quality, 3s spec-conformance, 3b security, 3c Codex adversarial).
Priority: security Critical/High > Codex Critical/High > quality.

3e **non entra nel verdetto** — non essere su staging non è un difetto del codice. Entra nella
Phase 4.5, dove decide se la PR può fondersi da sola.

All findings appear in their own sections in the comment (see Phase 4).

## Phase 4 — Render comment

Compose the markdown body from the exact template in `references/comment-template.md` —
read it now if you haven't. Two things are load-bearing:

- The hidden marker `<!-- polaris-sweep-id:<repo-slug>:<PR_N> -->` on the first line is
  what makes Phase 5's upsert idempotent, and the `**Verdict**: ✅ approve` line feeds the
  auto-merge GHA regex — don't restyle either.
- The **Verified clean** section is not padding: every finding is verified against the
  source before it is reported, and suspicions that DIE during verification are reported
  too, with the evidence that killed them. Without it a reviewer cannot tell "not
  mentioned" from "checked and fine". Verification rules (source on the PR branch, not
  diff hunks; library source cited `file:line`; `file:symbol` over drifting line numbers)
  are in the template file, with the precedents.

## Phase 4.5 — Auto-mergeable check (exit code, non prosa)

**The review text does not make the decision: `scripts/sweep_gate.py` does.** Judgment stays
with the model; auto-merge is a fail-closed script — a verdict without a SHA, on a stale SHA,
unattested, or on a PR touching the pipeline NEVER self-merges
(`references/bypass-test.md`, B1–B3).

```bash
gh pr diff "$PR_N" --name-only > .tmp/sweep/files-$PR_N.txt
HEAD_SHA=$(gh pr view "$PR_N" --json headRefOid -q .headRefOid)
python3 scripts/sweep_gate.py automerge \
  --run "_polaris/sweep/runs/<repo>/pr-$PR_N.md" \
  --pr-head "$HEAD_SHA" --files ".tmp/sweep/files-$PR_N.txt" --repo <checkout>
```

Exit `0` → append the Auto-mergeable block · `1` → omit the block and report the reason (on
stderr) in the comment · `2` → usage error, the sweep fails loudly. The Phase 6 run state MUST
therefore carry `head_sha`, `attestazione` and `risk`, or the gate denies on its own.

**The policy is perimeter-based** (founder 2026-08-17, B4): a PR **outside the repo's declared
prod perimeter** (`deployabili:` in `.fix/contract.yml` — the same declaration Phase 3e uses)
merges **always**, with just approve + a fresh SHA: docs, tests, tooling wait for no one. The
strict path (`risk:trivial` + attestation) applies only to diffs touching `deployabili`, or when
the perimeter is **not declared** — the gate does not guess what prod is. Pipeline beats
everything: whoever touches it never self-merges.

**Dentro il perimetro `deployabili`, l'auto-merge richiede anche l'attestazione runtime della
Phase 3e.** Una PR che mette in prod codice mai visto girare è esattamente il difetto che questo
sistema esiste per chiudere: la revisione statica è passata, e riguardava un testo. `risk:trivial`
dice che il rischio è basso, non che il codice funziona. Fuori dal perimetro non c'è runtime da
provare — lì l'attestazione non è richiesta, per costruzione.

Se 3e ha dato **non attestata** (il gate esce 1), ometti il blocco di auto-merge e scrivi al suo posto:

```
---

⏸️ **Non auto-mergeable** — la revisione è pulita, ma questo codice non è mai stato eseguito da
nessuna parte. Fai il real test, commenta qui cosa hai provato e dove, e rilancia la sweep.
```

Se 3e ha dato **non deployabile**, l'attestazione non è richiesta: l'auto-merge segue le regole
normali.

Non è una bocciatura della PR: è la differenza fra «il codice sembra giusto» e «il codice ha
funzionato». Solo la seconda giustifica un merge che nessun umano guarda.

If `sweep_gate.py automerge` exits `0` (approve/approve-with-minor · head_sha == PR HEAD ·
nessun file di pipeline · e, SOLO dentro il perimetro `deployabili` o senza perimetro dichiarato,
`risk:trivial` + attestazione), append the following block to the rendered body (just above the
`---` footer):

```
---

✅ **Auto-mergeable** — `risk:trivial` + Sweep approve + CI green will auto-merge via `.github/workflows/auto-merge-trivial.yml`. No human action required.
```

A `request-changes` verdict never auto-merges. Other risk levels (`risk:low/medium/high`) block
only diffs inside `deployabili` (or with no declared perimeter): there the PR stays in
`afk:done-pending-merge` awaiting human merge.

## Phase 5 — Upsert comment

```bash
/usr/local/bin/sweep-comment-upsert.sh "$PR_N" "$BODY"
```

**That script does not exist outside the HolyClaude container** (confirmed absent on
the founder's Mac, 2026-07-26). Check for it, and fall back to `gh api` inline — the
marker is what makes it idempotent, not the script:

```bash
R="<owner/repo>"; B=<path-to-rendered-body.md>
ID=$(gh api "repos/$R/issues/$PR_N/comments" --paginate \
       --jq ".[] | select(.body | contains(\"polaris-sweep-id:<repo-slug>:$PR_N\")) | .id" | head -1)
if [ -n "$ID" ]; then
  gh api -X PATCH "repos/$R/issues/comments/$ID" -F body=@"$B" --jq '.html_url'
else
  gh api -X POST  "repos/$R/issues/$PR_N/comments" -F body=@"$B" --jq '.html_url'
fi
```

Write the body to a file and pass it as `-F body=@file`. Do NOT inline a multi-KB
markdown body as a shell argument — quoting breaks on backticks and `$` in code spans.

## Phase 6 — Persist run state

Write `_polaris/sweep/runs/<repo>/pr-<PR_N>.md` with frontmatter:
`verdict, severity, head_sha, risk, attestazione, comment_id, ran_at` (+ `codex: not-run (<reason>)
· fallback: standards-spec` when Phase 3c degraded). `head_sha`, `risk` and `attestazione` are not
optional: they are what `sweep_gate.py` decides on — a run state without them (like the pre-v1
ones) gets denied by the gate, it does not slip past it.

## Failure modes
- API failure: retry once, then fail loud.
- Diff too large (>50k lines): summarize files-changed only, mark "diff too large for full review".
- Hand-non-authored PR: skip silently (not Sweep's territory).

## Quando NON usarla — what this skill does NOT do
- Approve/merge PRs (apply lane is GitHub Action / human).
- Close PRs.
- Comment on issues (only PRs).
- **Deploy anything.** La Phase 3e osserva se qualcuno ha messo la PR su staging; non ce la mette.
  Staging è condiviso e cambia solo quando lo dice un umano — automatizzare quel passo qui
  significherebbe cambiare la versione sotto i piedi di chi ci sta testando sopra.
- **Bocciare una PR perché non è su staging.** «Nessuno l'ha deployata» non è prova di una
  regressione: trattarla come tale ha già aperto tre PR di revert contro codice sano. Blocca solo
  l'auto-merge, che è un'altra cosa.
