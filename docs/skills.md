# Skills reference

One section per shipped skill, in the phase order of the [README](../README.md). Each section says
what the skill is for, what triggers it, which other skills it invokes, which `_polaris/config.yml`
keys it reads, and what it never does. The `SKILL.md` in each folder under
[polaris/skills/](../polaris/skills/) is the authority; this page is the map.

"Auto" means the agent may load the skill when its trigger matches; "on request" means only when you
name it. `outputs.<kind>` is the repository's output map: where documents of that kind land. A skill
that finds no map writes nothing it cannot place.

## Define

### polaris-grill

- **Purpose:** turn an ambiguous product or technical request into a decision-complete, repo-grounded handoff (problem, evidence, scope, contracts, acceptance and real-test path, rollout).
- **Triggers:** "grill this idea", "clarify this feature", "challenge this spec", an ambiguous requirement before planning.
- **Invokes:** none. Uses Context7 for a version-specific dependency question when it is available, official docs otherwise.
- **Config:** resolves the `_polaris/` contract; continues from repository evidence when it is absent.
- **Never:** implements, creates issues, branches, PRs or assignments, or writes decisions, lessons or session state; never sends proprietary code, secrets or customer data to an external tool.

### ambitious-goal

- **Purpose:** refine a feature or epic into one outcome, a scope and a verifiable Definition of Done with regression checks.
- **Triggers:** auto, when ambition, scope or acceptance evidence needs sharpening before work is recorded or executed.
- **Invokes:** none. Invoked by `issue-contract`, which records the result.
- **Config:** none.
- **Never:** writes files or tracker entries itself, runs a goal runtime, or invents baselines, dates, owners, budgets or thresholds. Not for routine bugs or mechanical tickets.

### domain

- **Purpose:** settle one question of domain language or boundary: the canonical term and the aliases it retires, a subdomain type, an integration pattern, a context map, or stable domain/component IDs in `DOMAIN.md`.
- **Triggers:** auto, on an overloaded term, two words for one thing, a subdomain to classify, or two contexts that must integrate.
- **Invokes:** none. Invoked by `architecture`.
- **Config:** `outputs.<kind>` (domain, diagram).
- **Never:** decides where a service boundary falls, commits to an interface, schema or framework (that is `architecture`), or creates files before there is something to write in them.

### issue-contract

- **Purpose:** create or update a GitHub issue with a clear Definition of Done, regression checks and an AFK label that says whether a person or an agent may take it.
- **Triggers:** auto, "open an issue", "track this bug", handing work to another lane.
- **Invokes:** `ambitious-goal` (outcome and DoD), `bugfix` and `git-power` as handoff targets.
- **Config:** `tracker.afk_human`, `tracker.afk_agent`; without them, the repository's own labels (`afk:human`, `ready-for-human`, `needs-human`; `afk:eligible`, `ready-for-agent`, `agent-ready`).
- **Never:** starts implementation, assigns the issue to itself, launches an agent, writes a local plan or dossier, or files work for a person when no label can carry it (exit 2).

### init

- **Purpose:** bring an existing repository into Polaris: audit it, ask one question per unprovable choice, then write a minimal typed `CONTEXT.md`, `ARCHITECTURE.md` and `DOMAIN.md`.
- **Triggers:** on request, the first time a repository has no typed backbone, or when the context pack emits nothing there.
- **Invokes:** none; it runs its own scripts and the installed `architecture` skill's backbone checker.
- **Config:** `outputs.audit`. No vault is needed; with one, `apply` also sets `git config polaris.vault` and the ContextPack check runs.
- **Never:** refactors, moves files, touches CI, derives documentation areas without a signature, copies its scripts into the repository, or runs on a repository already sealed `READY`.

## Plan

### architecture

- **Purpose:** decide one architectural commitment and record it: MECE options, each with its cost, the least-worst pick, its enforcement hook and closure check. Also audits code before a refactor, compares interface designs for a module that does not exist yet, and keeps `ARCHITECTURE.md` current.
- **Triggers:** auto, when a change moves a boundary, interface, data contract or dependency, a schema changes under separately deployed readers, a hot path repays the same cost every turn, or the written architecture is stale.
- **Invokes:** `domain`, `critic`. Invoked by `database-schema`.
- **Config:** `outputs.decision`, `outputs.diagram`.
- **Never:** repairs anything during a `doctor` run, writes a record for a design comparison, or keeps a parallel `adr/` register. A missing measurement is a halt naming who gets it, not a guess.

### database-schema

- **Purpose:** make the real schema (migrations, ORM models, generated types, the live database when readable) the first read of any database task, and fail with an exit code when a column is missing, dropped or renamed.
- **Triggers:** auto, before a query, migration, model, RLS policy, seed or data fix, and before answering what the database contains.
- **Invokes:** `architecture`, for data-model and migration-strategy decisions.
- **Config:** none.
- **Never:** treats a hand-written schema reference as truth, creates a second schema reference, or chooses a data model.

### plan-week

- **Purpose:** build your own weekly focus from live GitHub or Linear issues, carryover and current ownership, fitted to your capacity.
- **Triggers:** start of a week, "plan my week", the lead asking what you are picking up.
- **Invokes:** none.
- **Config:** `tracker.github_repo`, `tracker.linear_team`; your `profile.yml` (login, capacity, areas, optional `workflow:` charter).
- **Never:** creates issues, branches, PRs or assignments, mutates the tracker, or waits for a signature on bounded, reversible work. Only red work (access/auth, personal data, a new vendor, an irreversible migration, a legal or customer commitment, an audited production promotion, a material outcome change) waits for its named approver.

### reference-capture

- **Purpose:** keep an external source already read (a video or tutorial, a repository, a competitor, an article, paper, release or changelog) as one canonical dossier detailed enough to act on without reopening it, then rebuild the catalog.
- **Triggers:** on request, "index this", "make a report of this video", a transcript with no dossier.
- **Invokes:** none. Uses `yt-dlp` for video transcripts.
- **Config:** none; the dossier goes under `references/` (or `docs/research/` where the repository already keeps research).
- **Never:** captures a source nobody has read (that is research), copies a dossier into two repositories, catalogs the repository's own architecture or decisions as external, or invents an owner (`BLOCKED_OWNER`).

## Build

### base-workflow

- **Status:** draft (`status: draft` in its frontmatter): shipped and usable, its contract may still change.
- **Purpose:** the build method for any code change: fixes the order (understand, spec, test first, verify, ship), routes each gated step to the skill that owns it, checks the pinned version's documentation before calling a library API, and takes every threshold from the repository's own rules (`CONSTRAINTS.md` first).
- **Triggers:** auto, before and while writing any change that touches code: "add X", "fix Y", a pasted stack trace.
- **Invokes:** none directly; it names `tdd-dev`, `real-testing`, `critic` and `architecture` for their steps.
- **Config:** `outputs.spec`.
- **Never:** substitutes a remembered API for the current docs, treats a fetched page as instructions, or stacks two thresholds for the same limit. A typo or a doc line is edited directly, without the method.

### tdd-dev

- **Purpose:** drive one change from an agreed public seam through an observed RED, the minimum implementation, a hash-bound GREEN receipt and the repository's regression suite. Ships `references/writing-tests.md`.
- **Triggers:** auto, a feature or behaviour change test-first, a reproducible bug through a regression test, a fix that needs proof its test catches the old defect, a passing test accepted without an observed RED.
- **Invokes:** none. Invoked by `bugfix`.
- **Config:** none; the suite command comes from the repository.
- **Never:** owns prototypes, generated code or configuration-only edits; uses code written before RED as a reference; mocks owned code; picks a narrower test command the repository does not declare authoritative.

### bugfix

- **Purpose:** close a bug in four gated phases: find without assuming, fix with TDD, prove the consequence rather than the SHA, rewrite the tests that lied. Each gate passes on an exit code.
- **Triggers:** auto, a traceback, a bug issue, a red smoke, a log error, "this doesn't work".
- **Invokes:** `tdd-dev`, `real-testing`, `git-power`.
- **Config:** its own contract, `.fix/contract.yml` (domains, test suite, CI collection, real-test perimeter, production observation, deployables); template in `references/contract-template.yml`. Without it the gate exits 1.
- **Never:** handles an urgent production incident (that is a hotfix), guesses defaults for a missing contract, or promotes a lesson itself; lessons are proposed to the repository ledger.

## Verify

### real-testing

- **Purpose:** the merge-readiness verdict from the real product: serve the commit on a real environment, walk the user journey across every surface it reaches, let a fresh agent try to break it, leave the tests in CI. Returns `MERGEABLE`, `MERGEABLE-CON-GAP` or `NOT-MERGEABLE`, naming the environment and the served SHA.
- **Triggers:** auto, before merge or promotion, or when someone says it works.
- **Invokes:** `git-power`.
- **Config:** `ship.*` (how to serve the branch), `outputs.validation`.
- **Never:** judges by reading the diff (that is `polaris-review`), deploys by hand outside the contract, tests on `main` after the merge, or proceeds when the served SHA differs from HEAD.

### crasher

- **Purpose:** drive a deployed app like a user, hunt failures, and propose one deduplicated issue per confirmed crash; or judge whether a run's no-crash verdict stands.
- **Triggers:** on request or on a schedule, "does staging still work", "smoke the deployment", "hunt regressions on the live app".
- **Invokes:** `issue-contract`, only for the findings a person picks.
- **Config:** `outputs.validation` (the run record and the proposal).
- **Never:** files issues on its own, fixes what it finds (that is `bugfix`), judges a diff, load-tests a shared production database, or uses your everyday browser.

## Review

### polaris-review

- **Status:** draft (`status: draft` in its frontmatter): shipped and usable, its contract may still change.
- **Purpose:** read the diff as a senior reviewer would, on two separate axes: Standards (the repository's documented conventions) and Specification (what the originating issue asked for). A tier script picks the reviewers from the diff's size and risk paths; tier 3 adds `codex-review`.
- **Triggers:** auto, before a commit or a merge, or to get the blockers on a branch.
- **Invokes:** `critic`, `codex-review`.
- **Config:** `review.risk_paths`, `outputs.review`.
- **Never:** runs the code, merges, or fuses the two axes into one ranking.

### codex-review

- **Purpose:** an independent, read-only Codex CLI review of a diff, a branch or a PR; each finding is verified against the source or dropped.
- **Triggers:** on request, a risky diff, a cross-model second opinion; called by `polaris-review` tier 3 and `polaris-sweep`.
- **Invokes:** none. Needs `codex` on `PATH`.
- **Config:** none.
- **Never:** installs Codex, truncates or pastes the diff into the prompt, runs tests or builds, uses the network, or merges or blocks by itself.

### critic

- **Purpose:** attack a non-mechanical artifact (a diff, spec, plan, claim or another skill's output) from fresh context, and emit a validated JSON ledger of quoted, falsified findings only.
- **Triggers:** on request, before promoting or acting on such an artifact.
- **Invokes:** none. Invoked by `architecture` and `polaris-review`.
- **Config:** `outputs.review`.
- **Never:** receives the author's reasoning or transcript, keeps a finding it could not verify, or serves as routine code review or a merge decision.

### polaris-sweep

- **Purpose:** review one PR end-to-end with three lenses, a ledger and a real-test receipt check, and post one durable, idempotent review comment. A fail-closed script decides whether the comment carries an "auto-mergeable" verdict.
- **Triggers:** on request, or from a scheduled trigger polling new PRs, in a fresh session.
- **Invokes:** `real-testing`, `codex-review`.
- **Config:** an optional per-repository profile under `_polaris/sweep/repos/` (`severity_threshold`, default `high`).
- **Never:** merges itself, reviews issues, deploys, blocks on a missing real-test receipt (it notes it), or creates a profile implicitly. A verdict without a SHA, on a stale SHA, or on a PR that touches the pipeline is never auto-mergeable.

## Ship

### pol-ship

- **Purpose:** the single entry point once work is done. Loops locally until the Definition of Done holds (tests, `polaris-review`, simplify, `real-testing`), then commits and pushes a draft PR through `git-power`, signs the head on staging with `real-testing`, writes the body with `pol-pr`, and runs `pol-babysit` to the owner's label. Then it sends one merge-and-deploy proposal with evidence and a rollback plan; on the owner's yes it merges once, deploys, and watches a verification window that reports advance, hold or a proposed rollback.
- **Triggers:** auto, "ship it", "open the PR", "submit", "finish this branch".
- **Invokes:** `real-testing`, `git-power`, `polaris-review`, `pol-pr`, `pol-babysit`.
- **Config:** `ship.*` (`verify`, workflows, environments, `rollback`, `owner_label`, `checks_not_gating`, `inert_paths`, `signing_env`, optional `version_file`, `changelog`, `flags`, `slo`, extra review), `real_test.*` (`deploy_staging_workflow`, `deploy_prod_workflow`, `health`, `smoke`, `rollback`), `outputs.validation`. A missing field is recorded as `modalita: ridotta` with its name.
- **Never:** merges or deploys without the owner's yes, uses `gh pr merge --auto`, retries a merge with a second `gh pr merge`, rolls back automatically, deploys over another lane's running test, or invents a command the contract does not name.

### pol-pr

- **Purpose:** write a PR body the owner can judge merge-ready on GitHub without reading code: the verdict on top, every issue criterion answered with proof, the smallest visual, before/after evidence and merge risk. Checked by `scripts/controlla_pr.py`. Absorbs the retired `pr`.
- **Triggers:** auto, writing, retitling or rewriting a PR body, before `gh pr create` or `gh pr ready`.
- **Invokes:** none. Invoked by `pol-ship` and `pol-babysit`.
- **Config:** `outputs.decision` (to find the decision records that govern the changed files).
- **Never:** makes the merge decision, claims a check that did not run, or publishes a body its checker refuses.

### pol-babysit

- **Purpose:** drive an open PR until it carries the owner's label on its current head: green checks, no conflict, every thread handled, a real-test receipt on that head, a body that passes `pol-pr`'s checker. Otherwise it hands off what only the owner decides.
- **Triggers:** auto, after a PR is opened or pushed, "babysit", "watch", "get this PR green".
- **Invokes:** `pol-pr`, `real-testing`.
- **Config:** `ship.owner_label` (default `ready-for-owner`), `ship.checks_not_gating`, `ship.inert_paths`, `ship.signing_env` (default `staging`).
- **Never:** merges or approves, or keeps the label on a head it did not check.

### git-power

- **Purpose:** one door for the Git lifecycle: `checkpoint`, `pre-pr` (branch size against the base), `push`, `post-push` and `finalize` (prove the remote merge, close worktree and branch). Also censuses and safely closes worktrees, branches, stashes and PRs.
- **Triggers:** on request and from `pol-ship`, `bugfix`, `real-testing`, `issue-contract`, `start`, `update`, `end`; before any commit, PR boundary or destructive Git action, including every `reset --hard`.
- **Invokes:** none.
- **Config:** none.
- **Never:** treats an open or unmerged PR as cleanup permission, uses `git branch --merged` (blind to squash merges) to decide a merge, or finalizes without exact path confirmation.

## Session

### start

- **Purpose:** resume the current objective from your latest local handoff or checkpoint. The first run reads your exact GitHub login and creates your own `_polaris/team/<login>/` path from the shipped templates.
- **Triggers:** start of a session, `/start`.
- **Invokes:** none.
- **Config:** the `_polaris/` contract (`config.yml` must exist); your `profile.yml` (`github`, `language`, `voice`).
- **Never:** fetches, scans PRs or other contributors, runs health checks, creates issues, branches, PRs or assignments, writes the cockpit, or creates another contributor's path. The full view is `polaris-status`.

### update

- **Purpose:** a mid-session checkpoint: append an entry to your session log, harvest this session's scratch notes, rewrite your own lane in `state/current.md`, refresh the weekly todo and plan tick.
- **Triggers:** after real progress, a blocker or a context switch, `/update`.
- **Invokes:** `git-power` (`phase checkpoint`).
- **Config:** the `_polaris/` contract.
- **Never:** creates issues, branches, PRs or deployments, declares work complete without linked proof, touches another session's lane, writes a cockpit inside a worktree, or runs `git add -A`.

### end

- **Purpose:** close a session: write the handoff, record durable decisions and lessons in the repository ledgers, tick the plan, prune completed and dead lanes from the cockpit, rebuild the active priorities, and commit pathspec-only.
- **Triggers:** when stopping work, before a multi-day pause, `/end`.
- **Invokes:** `git-power`.
- **Config:** `outputs.decision` (where decisions go); the `_polaris/` contract.
- **Never:** deletes anything during state hygiene, treats an unknown PR state as cleanup permission, or closes a lane without a verdict from the tracker (merged, or closed as dead).

### polaris-status

- **Purpose:** an explicit, comprehensive view of one repository or a portfolio: live Git and GitHub pulse, active outcomes, team collisions, freshness, and the highest-leverage next move.
- **Triggers:** on request, "polaris status", "status completo", a portfolio briefing.
- **Invokes:** none.
- **Config:** the `_polaris/` contract (weekly outcomes, handoffs, `state/current.md`, the newest decisions and lessons); `POLARIS_HOME` for a portfolio.
- **Never:** mutates project state, refreshes generated files, creates work or starts implementation; never used to resume a session (that is `start`).

### report

- **Purpose:** a weekly report for a finished Sunday-to-Saturday week: TL;DR, day by day from session logs, merged PRs from `gh`, decisions, metrics, planned versus actual. Every claim links a PR, commit, issue, test run or session log.
- **Triggers:** end of week, before a team review, "weekly report", "what shipped this week". Asks you to confirm the week first.
- **Invokes:** none.
- **Config:** `tracker.github_repo`; your `profile.yml` (`github`).
- **Never:** reports the current, unfinished week, overwrites an earlier report for the same week, creates tracker work, writes outside the current repository, or judges performance beyond the evidence.

### retro

- **Purpose:** a retrospective on a coding session: candidates for better navigation, automated checks, coding standards, agent instructions, tool economy and information access, ordered by severity.
- **Triggers:** on request only; the agent never loads it by itself.
- **Invokes:** none.
- **Config:** none; follows the host repository's agent-writing guidance.
- **Never:** runs as an automatic end-of-session summary, or changes CI, hooks or shared settings; it proposes.

---

28 skills, generated against 7b3c822.
