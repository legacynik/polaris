---
name: codex-review
description: ◇ Get an independent adversarial code review from the OpenAI Codex CLI on a diff, a branch or a PR — a second opinion from another model family. Use when you have Codex installed and want a third opinion before merge, when a risky diff needs a cross-model pass, or when a PR review asks for one. Not a merge decision.
version: 1.0.0
user-invocable: true
status: active
job: run one hardened, read-only Codex review on a diff file and return findings that were checked against the source
when_not: no Codex CLI on PATH · the two-axis Standards/Spec review of a diff (polaris-review) · executing the code (real-testing) · deciding a merge (the merge workflow)
io: takes a diff (staged, branch against its base, or a PR number) -> produces a findings list (severity, file, line, failure scenario) from a schema-validated Codex run, each finding marked verified or dropped after reading the source
lifecycle: run files under .tmp/codex-review/<id>/ inside the repository, deleted after the findings are collected; findings go to the caller's review or comment, never to a new file
invokes: []
invoked-by: [human, polaris-review, polaris-sweep]
---

# codex-review

One job: hand a diff to the Codex CLI as an adversarial, read-only reviewer from another model
family, and bring back findings that survive a check against the source. This skill owns the
invocation; every caller (a person, `polaris-review` tier 3, `polaris-sweep`'s Codex lens) runs
the steps below unchanged.

## When NOT to use

- **No `codex` on PATH** (`command -v codex` fails): this skill cannot run. The caller falls back
  to its own second reviewer; do not install tools on someone's machine unasked.
- **The Standards/Spec review of a diff** → `polaris-review`. This is one extra lens, not that gate.
- **Running the code** → `real-testing`. Codex here is read-only by construction.
- **Deciding a merge.** Findings inform the merge workflow; they never merge or block by themselves.

## Model

Use `gpt-5.6-sol` (the flagship; right for the adversarial pre-merge pass); `gpt-5.6-terra` is the
cheaper option for routine diffs. On a ChatGPT-account login every `-codex`-suffixed id and every
bare id (`gpt-5.6`) returns **400 "not supported when using Codex with a ChatGPT account"**. If
`~/.codex/config.toml` already pins `model = "gpt-5.6-sol"`, omit `-m`; otherwise pass
`-m gpt-5.6-sol`.

## Steps

1. **Write the diff to a file inside the repository.** Codex reads it from the path; never paste
   the diff into the prompt and never truncate it (`head -500` once dropped 87% of a 4k-line diff
   while still reading like a complete review).

   ```bash
   ID=<pr-number-or-branch-slug>; D=.tmp/codex-review/$ID; mkdir -p "$D"
   gh pr diff "$ID" > "$D/diff"                  # a PR
   git diff --staged > "$D/diff"                 # or: the staged change
   git diff "$(git merge-base HEAD origin/main)" > "$D/diff"   # or: the branch
   ```

   Done when `$D/diff` is non-empty.
2. **Write the output schema** (strict structured output: every key in `properties` is also in
   `required`, at every level, with `additionalProperties: false`, or the run dies with a 400
   after its reasoning):

   ```bash
   cat > "$D/schema.json" <<'EOF'
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

3. **Write the prompt to `$D/prompt.md`.** The last block is not optional:

   ```
   Adversarial pre-merge review. The diff is at .tmp/codex-review/<ID>/diff.
   Read it, then read the source files it touches plus their direct callers and guards —
   the diff alone is not enough to judge correctness.
   CUSTOM RULES: read the AGENTS.md files whose directory covers the touched files (root and
   nested), apply every rule under their "Code Review Rules" sections, and cite the rule
   verbatim in any finding it motivates. A rule violation is High minimum.
   Be skeptical: assume the code is wrong until proven otherwise. For each finding give the
   concrete failure scenario (inputs/state -> wrong outcome), not a generic concern.
   No style preferences. Set approved=false if any critical/high finding stands.

   HARD CONSTRAINTS — violating these wastes the run:
   - Do NOT run tests, pytest, vitest, npm, python, or any build/execution command.
     This is READ-ONLY: read files, nothing else.
   - Do NOT attempt network access.
   - Read only the touched files and their direct callers, not the whole tree.
   - Emit the JSON result as your FINAL message and stop. Do not keep exploring
     after you have findings.
   ```

4. **Run it detached, stdin closed, under a hard timeout.** Every flag has a reason, and all of
   them were observed failing live: read [codex-flags.md](references/codex-flags.md) before
   changing any.

   ```bash
   nohup timeout 900 codex exec \
     --json \
     --sandbox read-only \
     --skip-git-repo-check \
     --output-schema "$D/schema.json" \
     --output-last-message "$D/findings.json" \
     "$(cat "$D/prompt.md")" \
     < /dev/null > "$D/run.log" 2>&1 &
   ```

   Poll for the process to exit (a foreground call capped by the harness at ten minutes looks
   exactly like a hang). Done when the process has exited.
5. **Check Codex actually read the source.** `--json` makes the log a JSONL event trace:

   ```bash
   jq -rs '[.[] | select(.item.type=="command_execution") | .item.command] | join("\n")' "$D/run.log" \
     | grep -cF -f <(sed -n 's#^+++ b/##p' "$D/diff") \
     || echo "Codex never opened the touched files — treat its findings as diff-only"
   ```

   A review whose trace never opened the source is a diff skim; say so beside its findings.
6. **Collect, with the log as fallback.**

   ```bash
   jq -r '.findings[] | "[\(.severity|ascii_upcase)] \(.title) (\(.file):\(.line))"' "$D/findings.json"
   # --output-last-message is not guaranteed (Codex can end on a tool block); the log is
   # ANSI-encoded, so plain grep matches nothing and grep -a does:
   grep -a -oE '"severity":\s*"[a-z]+"|\[(CRITICAL|HIGH|MEDIUM|LOW)\][^"]{0,160}' "$D/run.log"
   ```

7. **Verify every finding against the source before reporting it.** Codex mixes real defects with
   false alarms; the value is in the reproduction. Open the cited file and line, reproduce the
   failure scenario by reading (or hand it to the caller's test step), and mark each finding
   `verified` or `dropped: <why>`. Done when every finding carries one of the two marks.
8. **Clean up** `$D` once the findings are collected (Codex reads from it while running).

## Output

```text
CODEX: ran | not-run (<reason: no CLI / timed out after N min / zero output>)
TRACE: opened touched files | diff-only
FINDINGS: <n verified> verified · <n dropped> dropped
- [HIGH] <title> (<file>:<line>) — verified: <failure scenario>
```

`not-run` is an honest result the caller handles (`polaris-review` runs a second fresh reviewer
instead); never stall waiting for a run that produced nothing.

## Code Review Rules in the repository

Codex applies `## Code Review Rules` sections of `AGENTS.md` files that cover the changed paths.
Each rule states an invariant and its safe path, not implementation details ("keep the
`completed` event name: cloud consumers listen for it; rename only with a backward-compatible
alias"). Start with the checks reviewers keep explaining, describe outcomes rather than function
names, prune noisy rules, and leave mechanical checks to CI.

## Selfcheck

The two bypass cases are executable: `references/bypass-test.md`.
