---
title: review — second opinion from another model family
description: The hardened, read-only invocation of another model family's CLI on a diff, absorbed from the codex-review skill (1.0.0). Read before changing any flag.
status: active
---

# Second opinion

A reviewer from the same model family shares the author's blind spots (records lesson
2026-07-12). This mode hands the same diff to another family's CLI, read-only, and keeps only
findings that survive a check against the source. Runs on tier 3, or when someone asks for it.

Use whatever other-family CLI the harness has (an OpenAI-family CLI beside a Claude session, a
Claude-family CLI beside a Codex session). The model is that CLI's own configured default: this
skill pins none. The commands below use the Codex CLI as the worked example, because its flags
were the ones observed failing live; translate each flag's reason, not its spelling.

No such CLI on PATH → `SECOND-OPINION: not-run (no CLI)`, then a second fresh reviewer on a
different model than the first. Never install a tool on someone's machine unasked.

## Steps

1. **The diff to a file inside the repository**, never pasted into the prompt, never truncated
   (`head -500` once dropped 87% of a 4k-line diff while reading like a complete review).

   ```bash
   ID=<pr-number-or-branch-slug>; D=.tmp/second-opinion/$ID; mkdir -p "$D"
   gh pr diff "$ID" > "$D/diff"                                  # a PR
   git diff --staged > "$D/diff"                                 # the staged change
   git diff "$(git merge-base HEAD origin/main)" > "$D/diff"     # the branch
   ```

2. **A strict output schema**: every key in `properties` also in `required`, at every level,
   `additionalProperties: false`, or the run dies with a 400 after its reasoning.

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

3. **The prompt in `$D/prompt.md`**; the last block is not optional:

   ```
   Adversarial pre-merge review. The diff is at .tmp/second-opinion/<ID>/diff.
   Read it, then read the source files it touches plus their direct callers and guards.
   CUSTOM RULES: read the AGENTS.md files whose directory covers the touched files and apply
   every rule under their "Code Review Rules" sections; cite the rule verbatim in any finding
   it motivates. A rule violation is High minimum.
   Assume the code is wrong until proven otherwise. For each finding give the concrete failure
   scenario (inputs/state -> wrong outcome). No style preferences.
   Set approved=false if any critical/high finding stands.

   HARD CONSTRAINTS:
   - Do NOT run tests, builds, or any execution command. READ-ONLY.
   - Do NOT attempt network access.
   - Read only the touched files and their direct callers.
   - Emit the JSON result as your FINAL message and stop.
   ```

4. **Run detached, stdin closed, under a hard timeout.**

   ```bash
   nohup timeout 900 codex exec --json --sandbox read-only --skip-git-repo-check \
     --output-schema "$D/schema.json" --output-last-message "$D/findings.json" \
     "$(cat "$D/prompt.md")" < /dev/null > "$D/run.log" 2>&1 &
   ```

   Poll until the process exits: a foreground call capped by the harness looks like a hang.

5. **Check it read the source.** With a JSONL event trace:

   ```bash
   jq -rs '[.[] | select(.item.type=="command_execution") | .item.command] | join("\n")' "$D/run.log" \
     | grep -cF -f <(sed -n 's#^+++ b/##p' "$D/diff") || echo "diff-only: never opened the touched files"
   ```

6. **Collect**, the log as fallback (`--output-last-message` is not guaranteed; the log is
   ANSI-encoded, so `grep -a`):

   ```bash
   jq -r '.findings[] | "[\(.severity|ascii_upcase)] \(.title) (\(.file):\(.line))"' "$D/findings.json"
   grep -a -oE '"severity":\s*"[a-z]+"|\[(CRITICAL|HIGH|MEDIUM|LOW)\][^"]{0,160}' "$D/run.log"
   ```

7. **Verify every finding against the source**: open the cited line, reproduce the failure
   scenario by reading, mark it `verified` or `dropped: <why>`. Only verified findings enter the
   Standards file.
8. **Delete `$D`** once collected.

## Why each flag exists (each observed live)

| Flag / choice | Why |
|---|---|
| `< /dev/null` | without it the CLI blocks forever reading stdin, and writes a zero-byte output after an hour |
| `--skip-git-repo-check` | an untrusted working directory aborts at once |
| no `--full-auto` | deprecated, and it contradicts `--sandbox read-only` |
| `timeout 900` + `nohup … &` | the harness caps a foreground call (ten minutes on some); a longer run is killed by the caller and looks like a hang |
| `--output-schema` | the last-message file alone is not guaranteed: the run can end on a tool block |
| `--json` | the JSONL trace is the only way to prove the touched files were opened |
| HARD CONSTRAINTS block | unconstrained, the reviewer ran the project's test suite and hit an external host for ~50 minutes with no review |
| no pinned model id | some ids return 400 on a subscription login; the CLI's configured default is the one that works |

## Output

```text
SECOND-OPINION: ran (<cli>) | not-run (<reason: no CLI / timed out after N min / zero output>)
TRACE: opened touched files | diff-only
FINDINGS: <n verified> verified · <n dropped> dropped
- [HIGH] <title> (<file>:<line>) — verified: <failure scenario>
```

## Code Review Rules in the repository

The CLI applies `## Code Review Rules` sections of the `AGENTS.md` files covering the changed
paths. Each rule states an invariant and its safe path, not implementation details ("keep the
`completed` event name: cloud consumers listen for it; rename only with a backward-compatible
alias"). Start with the checks reviewers keep explaining; prune noisy rules; leave mechanical
checks to CI.

Credits: the Code Review Rules pattern and the JSONL trace check follow OpenAI's public Codex
documentation ("Custom code review rules for Codex", the Codex CLI docs). Paraphrased.
