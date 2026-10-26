---
name: status
description: ◇ Polaris — the explicit, full situational view of a portfolio or one repository — live git and GitHub pulse, active outcomes, team collisions, freshness, decisions accepted and still not done, and the one highest-leverage next move. Use on "polaris status / status completo", cross-repo priorities, or an explicit request to see everything. Not for resuming a session. Requires git, gh, python3.
version: 1.5.3
user-invocable: true
status: active
lifecycle: live git/GitHub + vault state + the decision gate → one briefing; writes nothing unless the single alignment confirm says yes
invokes: []
invoked-by: human
io: scope (portfolio | repo | both) → a briefing under 50 lines with the NOT_DONE decisions and MY CALL
---

# status

## What it does

Pays the cost `start` refuses to pay: network, repository pulse, portfolio state, team collisions,
health, and the decisions that were accepted and never enacted — then names one next move. It
observes; it does not refresh generated files, create work or start implementing.

## When

- "polaris status", "status completo", "where are we across the repos", "what should I do next".
- Weekly, or when the cockpit has grown and needs a proven cleanup.

## Steps

1. Scope: portfolio (`POLARIS_HOME`), one repository (its `_polaris/config.yml`, resolved with
   `eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"`), or
   both. No portfolio root → say so once and continue with the repository. Never hardcode a path.
2. Portfolio: pick ≤ 3 documents with the root's own index (`scripts/polaris_query_index.py`) or by
   recency, then the control surfaces (`state/current.md`, the board's Active, active plans'
   frontmatter); `polaris_freshness_check.py` read-only (0 fresh, 1 warn, 2 stale → a risk).
3. Repository pulse, bounded: `git fetch --prune origin` (offline → say so, never present stale as
   current), `git log origin/<default> -5 --oneline`, `git branch -vv --sort=-committerdate | head -8`,
   `gh pr list --state open --limit 10`; then the weekly files, the newest handoff, the cockpit.
4. Decided and not done — the gate's own list, verbatim, oldest first (minutes: 90 s per probe):
   ```bash
   SG="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py"
   D="${POLARIS_HOME:-$ROOT}"; [ -f "$D/scripts/check_decision_execution.py" ] || D="$(python3 "$SG" vault --root "$ROOT")"
   if [ -f "$D/scripts/check_decision_execution.py" ]; then
     python3 "$D/scripts/check_decision_execution.py" --root "$D" --not-done --timeout 90
   else echo "NOT_DONE: skipped — no decision gate here or in a declared vault"; fi
   ```
5. Keep only decision-grade signals: outcome vs actual branch, shipped without proof, blocked near a
   deadline, two owners on one area, stale state contradicted by live evidence. Tracker and git are
   truth; plans and handoffs are intent — name a disagreement, never reconcile it silently.
6. Alignment sweep only when the cockpit is over threshold (> 10 open lanes, > 8 KB, > 5 Recent
   Context entries): one fresh-context agent per product repository, read-only, verdict LANDED /
   OPEN / UNCLEAR with evidence; then ONE confirm for the whole cleanup (`references/procedure.md`).

History behind a mismatch: ask the agent memory (`ai-memory-retrieval`), skipped if absent —
context, never proof of current state.

## Output

Under 50 lines, the user's language, empty sections omitted: **POLARIS STATUS — {date}** ·
PORTFOLIO · CURRENT REPO · TEAM / COLLISIONS · MEMORY / HEALTH · **DECIDED, NOT DONE** (step 4
verbatim) · RISKS (≤ 3, evidence-backed) · ALIGNMENT (only if step 6 ran) · **MY CALL** — one move
and why. Then stop: no execution until asked.

## Where this goes

This skill produces: **none (a briefing; nothing is written without the one confirm)**.

## Not for

- Resuming the current objective → `start` (local, no network).
- The week's focus or report → `week`; a checkpoint or the close → `end`.
- A single implementation task, or cleaning anything without the one confirm.
