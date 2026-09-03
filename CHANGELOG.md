# Changelog

All notable changes to Polaris Team OS. The installed version is pinned in
`polaris/.claude-plugin/plugin.json`.

## Unreleased

### Added
- `start` 1.3.0: **the three signals the system already computed and never showed**
  (`polaris-os#243`), plus the two surfaces the donor's four-file form landed with no reader
  (`#240`). One shipped script, `start/scripts/brief_signals.py`, prints a line ONLY when it has
  something to say: `TODOS_ACTIVE`/`TODO`/`FOLLOWUP_DUE` from `state/todos.md`, `RECENT` from the
  `## Recent Context` ring, `DEFERRED` (the `polaris-deferred` spool, counted under the git COMMON
  dir so a worktree sees the same number), `DRIFT` (the branch the MAIN worktree is parked on plus
  the count of modified files that are not this contributor's) and `SECTIONS_MISSING`. A repo
  without `state/todos.md` gets one line and exit 0, never an error.
  **Feature-detect for the typed backbone** (`#155`): `PACK=<id>` appears only where the host repo
  carries both `decisions/manifest.json` and `scripts/contextpack.py`; everywhere else the brief is
  exactly what it was. The `/start` word budget moved 900 → 940 ONCE for this step, declared in the
  test; the byte cap did not move.
- `end` 1.11.0: **`## Recent Context` is a real ring again** — `update/scripts/recent_context.py`,
  cap 5, newest first, idempotent, and every byte outside the section comes back identical. It
  replaces the per-repo `state/current-state.md` append: that surface was measured at 188 KB /
  93 blocks, last written nine days before anyone noticed it had died. `current-state.md` survives
  ONLY as the declared cross-repo vault copy (`git config polaris.vault_root`), explicitly not a
  cockpit and never authority.
- `end` 1.11.0: **closing means removing** — `update/scripts/state_close.py close` takes the thread
  out of `## Open`, moves its `state/todos.md` row from `## Active` to `## Completed` with today's
  date, and collapses `Updated:` to date and owner. An unknown key exits 2 and touches nothing.
  Automatic removal stays PARKED on `polaris-os#268` (`merge_truth` answers `None` once the branch
  ref is gone, the normal case after `--delete-branch`): `state_close.py candidates` lists the
  threads citing an issue or a PR, read-only, and the human closes them one line at a time.
- `update` 2.10.0: **the todo of the week follows the thread** — a checkpoint that advances a row in
  `state/todos.md` updates THAT row through `state_upsert.py week`, carrying its original `· Added:`
  stamp. The stamp is the age signal; re-stamping makes three-week-old work read as news.
- `plan-week` 1.3.0: Step 6b now reconciles `state/todos.md` (the live view) instead of writing
  `## Active` into the weekly plan, which has no such section — the merge could never have run.
  `## Completed` is rolled to the current week only (`state_close.py week-roll`); `## Active` is
  never zeroed and `## Follow-ups`, the only section that crosses weeks, is never touched.
- Templates for the host repo's state contract: `templates/repo-contract/state/{current,todos,goals}.md`.
  `todos.md` is the donor's TABLE form, the same shape `polaris-os#240` seeded, footer included.
  The one fence-aware line parser learned a `table_row()` branch (`state_lines.py`) rather than the
  package growing a second notion of "line" — that second notion is the root cause that once made
  seven state writers disagree, and a bullets-only reader had already proved it here: against the
  real `state/todos.md` it reported `TODOS_ACTIVE=0`, lost an overdue follow-up, and `state_upsert`
  appended a duplicate row stamped with this week beside the real one carrying `W32`.
- `todos.md` names its three writers, in the template and in the skills that obey it: `plan-week`
  reconciles `Active` and rolls `Completed`, `/update` refreshes the TEXT of a row the current
  thread cites and may not create one (`state_upsert --no-add`), `/end` moves a landed row into
  `Completed`. None of the three re-stamps `Added`; none empties `Active`.
- `plan-week` 1.3.0 / `update` 2.10.0: `update/scripts/todos_roll.py` — the `Completed` roll, split
  out of `state_close.py` because rolling the week is `plan-week`'s move, not `/end`'s.
- `polaris-status` 1.2.0: the state-health line counts `## Recent Context` entries against the cap
  instead of the blocks of a dense file that no longer exists.

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- `update` 2.10.0: **`verify` binds the cockpit to the run** (`polaris-os#84`). Three bypasses, three
  fixtures: an empty `touch` (mtime moves, nothing else), a cockpit re-dated by hand with nobody's
  name on it, and a cockpit with no `Updated:` line at all while the session logged today. The line
  must carry TODAY and this contributor, and `verify "<title>"` additionally requires that title to
  be the NEWEST entry in the append-only session log — which is what catches a `sed -i` re-date with
  no checkpoint behind it. Per `#240` the `Updated:` line is date and owner ONLY, so the title is
  asserted in the log, not in the line: one fact in each place. Selfcheck 7 → 11 cases.
- `update` 2.10.0: **the first harvest of the day is capped** (`polaris-os#89`).
  `checkpoint.sh harvest-slice <sid>` emits every line carrying this session's id wherever it sits,
  plus the head of the delta up to `HARVEST_CAP` (40). The cap is on the FOREIGN prefix, never on
  position: a positional cap drops exactly the own-id line that arrived last. Measured on the
  issue's fixture: 150-line scratch, 80% foreign → 38 lines read, 30/30 own lines kept.
- Release hygiene (`polaris#5`): the package no longer ships a founder machine path
  (`evals/scripts/replay_tasks.py` now reads `POLARIS_VENDOR_DIR`) or a real GitHub login in a
  fixture (`session_commit.sh` and `tests/real_session_commit.sh` use `acme-dev`). The perimeter
  test walks the tree instead of holding a list, and skips only lines marked `perimeter-guard`.

### Unchanged, and declared
- **The plan tick: RESTORE holds** (`polaris-os#85`) — the state declared in 0.20.0 stands, and it now
  has a gate that proves it: an existing weekly plan left unticked fails `checkpoint.sh verify`.
  `#85` decides the state by counting the hyphenated spelling in this file, which in RESTORE must be
  0: it is written "the plan tick" everywhere, and this note is the reason why.
  The other state is provably absent: nowhere does this changelog declare the tick superseded, and
  the apex `/update` row keeps the words "tick del plan".

## 0.20.0 — 2026-08-18

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- `update` 2.3.0: **the plan tick is back — the SECOND undeclared drop of the v2.0.0
  rewrite (498ed70), restored by founder verdict (polaris-os#85: plans are the roadmap).**
  Owed ONLY when `team/<login>/weeks/<current-week>.md` exists: absent file, zero noise
  (no gate that fails on nothing); present and untouched by the checkpoint, `verify`
  FAILs naming the file. `prepare` now prints `WEEKLY=` and `commit` takes N paths so
  the ticked plan lands with the session log in one pathspec-only commit. Fixture-proven:
  no-weekly pass · untouched-weekly exit 1 · ticked pass · multi-path commit.

## 0.19.0 — 2026-08-18

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- `update` 2.2.0: **the `state/current.md` reconcile step is back.** The v2.0.0 rewrite
  (498ed70, released in 0.17.0) silently dropped "Step 3 — Reconcile state/current.md"
  without a changelog line — the removal is hereby declared, late. Consequence observed
  2026-08-17: a session that checkpoints with `/update` but never runs `/end` leaves the
  open-items ledger stale, and whether it got refreshed depended on panel habit. Restored
  as a short prose step (Updated: line overwrite + Open add-and-flag, never close another
  owner's line) enforced by `checkpoint.sh verify`, which now FAILs when `current.md`
  predates today's session log.

### Added
- `end` 1.3.0: **worktree sweep** in the State-hygiene pass (`scripts/wt_sweep.sh`).
  The founder works worktree-first and `/end` is the only janitor he runs: a worktree
  that is clean AND merged into the default branch is removed (branch deleted with
  `-d`); a dirty worktree is NEVER touched (reported); clean-but-unmerged is a pause,
  reported with age; `git worktree prune` always. `--selfcheck` proves all four
  behaviors on a fixture repo; report-mode real-test on a 29-worktree repo found
  11 removable / 11 dirty (untouched) / 7 paused.
- `update` 2.1.0: after landing, one hygiene line via `wt_sweep.sh --report` —
  count only, `/update` never removes.

## 0.18.0

### Removed
- `real-testing`: the skill moved to its single source in the Polaris suite
  (`skills-suite/real-testing` v2.0.0, installed by symlink via `_standard/install.sh`).
  The plugin no longer ships a copy — a second distribution channel is exactly the
  divergence the 2026-08-16 single-source refactor removed (see the suite CHANGELOG
  and `docs/skill-refactor/2026-08-16-real-testing/`).

## 0.17.0

### Changed
- **`/update` 2.0.0 — the entry carries what is not progress.** The 31-Jan design had
  Completed / In Progress / Key Context / Files Modified; three of those fields eroded away over
  seven months of rewrites, leaving Done/Next/Blocker with nowhere to record a decision, a
  discovery, or a mistake — so that content either went missing or got improvised into an
  unstructured `Nota:` line. Restored as **In progress**, **Key context** (tagged
  `#decisione #architettura #scoperta #errore #superata #incidente`) and **Files**, plus a titled
  header and `wt:`/`branch:` provenance for multi-panel work. `Files` is written
  `path · symbol · why`: Serena navigates by symbol, so that is where the log and the code graph
  meet months later. Body down from 192 to 111 lines — the deterministic half moved to a script.
- **`/end` 1.2.0 — same entry format as `/update`.** It emitted Shipped / Still open / Next session
  while `/update` emitted a different set: same file, same reader, two grammars. It now writes the
  same entry, changing only the word after the timestamp and closing on `Next session`.
- **Both skills follow one memory rule.** Archive (`lessons.md`, `decisions.md`): write always,
  append-only — a lesson waiting for approval dies with the session. Apex (`CLAUDE.md`, `rules/`):
  never from a session skill; it is reached only through `/pol-apex-curate`, which proposes.
  Architectural choices are proposed as ADRs, where they stay linked to the code.

### Added
- **`skills/update/scripts/checkpoint.sh`** — the deterministic half of the checkpoint: `prepare`
  (root, login, branch, worktree, paths, harvest offset, hygiene), `harvest-done`, `commit`,
  `verify`, `due-done`. It costs no context and cannot be skipped by a model in a hurry.
- **`verify` fails loudly when a step was skipped.** It exists because a step that lives only in
  prose eventually gets skipped — including by whoever wrote it: on 2026-08-08 the author of the
  harvest step skipped it the same day he added it.
- **Recurring work rides the ritual that actually runs.** `state/due.md` lists jobs as
  `YYYY-MM-DD · name · every Nd`; `prepare` prints whatever is due and `due-done` moves the date
  forward by itself. Hung off `/update`, which runs daily, rather than `/end`, which often does not.
- **Six behavioural eval cases for `/update`**, cut down from fourteen by an adversarial review that
  removed the tautological ones (checks any model passes forever) and merged two pairs — notably
  keep-the-facts and invent-nothing, which as separate cases are both satisfied by a degenerate
  "dump everything, then say nothing" strategy that never exercises selection.

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- **Two eval assertions were wrong, not the skill.** `current.md resta fuori dal commit` was written
  inverted and said so in a `_negated_by_design` field nobody ever closed, so it reported red on
  correct behaviour; new `head_files_omit` lets a negative claim be stated directly. `dichiara il
  differimento` looked for the English word `defer` while the skills write Italian logs — the model
  had correctly written "rinviato"; `output_mentions` now accepts `a|b` alternatives.
- **The harness keeps the model output** (`_eval_output.txt`). A red assertion with no transcript
  costs a full re-run to diagnose, and reading it is what showed the skill was right both times.

## 0.16.0

### Added
- **`/polaris-status` measures state health before sweeping it.** New Step 5b.0: counts open threads
  and cockpit blocks first (two commands, no thread reading), reports the numbers, and only over
  threshold (>10 threads / >8 KB, or >20 blocks / >50 KB) asks ONE question before investigating.
  Under threshold it says "state healthy" and skips the expensive pass entirely — the sweep used to
  run unconditionally, paying full price on a file with five live threads.
- **Per-repo investigation of what already landed.** `state_reconcile.py` keys on the branch alone,
  so threads sitting on `main` and identified by issue/PR numbers in their text came back
  `unverified` forever and the file only grew. Everything it cannot resolve now goes to ONE Sonnet
  subagent **per product repo** (never one per thread), which resolves each `#N` via `gh`, each
  branch against `origin/main`, each SHA for reachability, and returns LANDED / OPEN / UNCLEAR with
  its evidence. UNCLEAR is a valid answer and is never rounded to LANDED; another contributor's
  thread is reported, never proposed for removal.
- **A behavioural eval harness for the session skills** (`polaris/evals/`). Fixtures build a
  throwaway repo in a declared state (N threads, N blocks, chosen branch, full `_polaris/` contract);
  assertions read the filesystem and git, so a case has one answer instead of a graded opinion. Every
  case declares `fails_before` — the skill version it must be RED on, because a case green on both
  sides tests nothing. `--selfcheck` verifies the harness with no model in the loop, and it already
  caught a bug in its own test data.

### Changed
- **`/update` pinned to `model: sonnet`.** Measured at 13% of a week's usage: it reads ~88k tokens of
  state to produce ~60 tokens of checkpoint. Sonnet rather than a cheaper tier because Step 3
  reconciles `current.md` across parallel panels — that step needs judgment, and losing another
  panel's thread costs more than the tokens saved.

### Proof
First real benchmark (`polaris/evals/polaris-status-workspace/iteration-1/benchmark.md`), new skill
vs the pre-change version on identical fixtures: **8/8 vs 4/8** — and the 4 the baseline passes are
the four non-discriminating safety guards. On 5 threads the baseline ran the full sweep
(`DID_INVESTIGATE: yes`) where the new one stops; on 14 threads the baseline investigated **without
asking**, the new one reported both counts and waited. Cost delta −5.3k tokens / −40s and
−6.0k / −76s. Stated honestly in the benchmark: the fixture has no remote and no issues, so it
understates the saving on a real vault, and half the assertions do not discriminate.

## 0.15.0

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- **Session state can no longer strand on a feature branch.** `session_commit.sh` now commits only
  from the repository's default branch (resolved from `origin/HEAD`, falling back to a local
  `main`/`master`) and **defers** everywhere else: the file stays on disk as the single copy and the
  next default-branch session lands it. Supersedes the 2026-07-19 "Option A" (commit-on-current-branch),
  which stranded daily session logs on branches that were paused or never merged — invisible to
  `/start` until merge — and produced N diverging branch copies of one append-only file.
- **`/end` no longer hand-commits in prose.** Step 5 now calls the same script with the new `--end`
  mode, so the handoff, session log, weekly plan, `decisions.md`, `lessons.md` and the `polmem`
  journal line inherit the identical guard: pathspec-only, default-branch-only, no `git add -A`,
  no foreign-file drag, honest failure reporting. `--end` may commit the two ledgers (its vetted
  promotion) but still refuses `state/current.md` and `.env*`.
- **The guard is reachable from the skills-CLI install.** The script moved to
  `skills/update/scripts/session_commit.sh` so `npx skills` ships it with the skill (previously it
  lived outside any skill directory, so on a skills-CLI machine `$CLAUDE_PLUGIN_ROOT/scripts/…`
  resolved to nothing and the whole "enforced in code" step silently did nothing). Both skills
  resolve plugin-root first, then `~/.agents/skills/…`, with an explicit same-rule manual fallback.

### Added
- Six adversarial self-checks covering every new branch: off-default defer (nothing committed, file
  intact on disk), deferred content landing on the next default-branch run, `--end` promoting the
  ledgers, `--end` still refusing state/secrets, `--end` deferring off-default, `origin/HEAD`-driven
  default resolution, and a `master`-default repository. Each guard was mutation-tested: breaking it
  fails a named check.

## 0.10.0

### Added
- **`/polaris-grill`.** A read-only, repo-grounded product and technical interview that combines
  live code, backend and schema contracts, `_polaris/` state, decisions, lessons, targeted
  `polmem recall`, and version-aware Context7 documentation. It auto-answers from evidence, asks one
  decision-bearing question at a time, and emits a bounded execution handoff without implementing,
  mutating trackers, or inventing a second spec system.
- **Portable `/polaris-status`.** The existing full-status workflow now ships from the versioned
  package as a provider-neutral Agent Skill. It owns the expensive Git/GitHub pulse, team scan,
  freshness, memory and health paths removed from `/start`, and is discoverable by Agent Skills
  installers as well as the Claude plugin.

### Changed
- **`/start` is resume-only.** It reads the current outcome, local branch, latest owned
  handoff/checkpoint, active blocker and concrete next action. Repo pulse, remote fetch, open PRs,
  other contributors, decision/lesson slices, memory recall and health moved behind the explicit
  operator status workflow instead of being paid on every session start.
- **Recurring identity resolution is local.** The exact GitHub login is resolved and cached in
  repo-local git config on first use; subsequent starts do not call GitHub just to locate the
  contributor profile.
- The release contract now caps `/start` at 7 KB / 900 words and fails if status operations creep
  back into it.

## 0.9.0

### Removed
- **The CEO signature gate is gone — `ceo_signature`, `execution_authorized` and `auto_authorized`
  no longer exist** (founder call, 2026-07-15: "leva proprio la mia firma"). The model was
  backwards, and 0.8.0's `auto_authorized: secondary` was a patch on a broken default rather than a
  fix. The live engineering charter this plugin is supposed to serve says the opposite in writing:
  green work is **self-merged by its owner** after the applicable gates, amber **proceeds** on a
  recorded `Decision / Why / Risk / Next step` ("silence is not a block"), the lead "**is not the
  default technical gate**", and their review of the weekly focus is "**priority alignment, not a
  technical approval gate**". A plugin shipping the inverse trains contributors to ask permission
  for reversible work and makes the founder the whole team's bottleneck.

### Changed
- **The weekly plan states truth, not permission**: `status: active|carried|superseded` +
  `lead_review: pending|read|reordered`. The plan is committed and travels into the PR — visible
  and correctable at any time, blocking at none. `/start` briefs it as **active work**; `/report`
  measures against it as the contributor's own stated intent, and a plan overtaken by a real
  reprioritisation is reported as a priority change, not a miss.
- **The gate survives exactly where being wrong is irreversible — the red stop-lines**, and it
  names an approver instead of defaulting to the lead: access/RLS/auth expansion, personal-data
  use/retention/deletion, new processor/vendor, irreversible migration, legal/customer commitment,
  audited production promotion, material outcome/architecture change. **The repository's own
  charter (`profile.yml` → `workflow:`) outranks this list** — an audited repo may name approvers
  the plugin cannot know about (e.g. a signed segregation-of-duties matrix).
- **`weekly_capacity` is a planning guide, not a quota.** The live contract had already corrected
  this by hand (`weekly_capacity: 3 # planning guide, not a quota`) before the plugin caught up; a
  hard cap turns an honesty device into a lid on output.
- **`/end` closes a thread only against verified merge.** `git worktree list` (a worktree still
  holding the branch = live), `git branch --merged origin/main`, `gh pr list --head`. An open PR is
  not a closed thread, a green real-test is not a merge, and a branch with no recent commits is
  **parked, not dead** — with several panels on several worktrees, parked-while-you-work-elsewhere
  is the normal shape of the work, and dropping it is the exact loss this file exists to prevent.
- **There is no CEO in this contract.** The role is gone, not just the signature field — `/plan-week`
  Step 1 still read "the CEO reviews and signs it", which the first sweep missed because it banned
  the phrase `CEO signs`. What exists: a repo **owner**, and (where a repo has one) a **lead** who
  sets outcomes, priorities and red stop-lines. `## PM action` in `/report` is no longer "decisions
  the CEO must take" but "blockers only someone else can clear, with a named owner" — and "none" is
  the healthy default. The contract test now bans the bare word, because authority-by-rank is how
  the gate grows back under a new name.
- **`current.md` converges on the MAIN worktree** — `/update` and `/end` resolve it via
  `git worktree list --porcelain | head -1`, never from the checkout they happen to sit in. The real
  workflow is many panels in many worktrees whose handoff must land where the next session opens:
  main. Since the file is gitignored it never travels with a branch, so v0.8.1's per-checkout
  isolation was the **bug, not the safety** — measured on one live repo, three worktrees each held
  an orphaned copy (80KB last touched 12 July, 66KB last touched 8 July, one absent), every one a
  handoff its own author never saw again. Consequences: **the branch is a thread's identity** (one
  panel, one worktree, one branch — the panel discriminator that makes the merge check possible
  without any panel knowing which others are alive), threads and `Next` lines are branch-keyed so
  panels stop overwriting each other, and a `current.md` found in a non-main worktree is surfaced as
  a pre-rule orphan, never silently deleted — it may be the only copy of a handoff.

## 0.8.2

### Changed
- **`/update` loses closing authority over `current.md` — only `/end` may close an item**
  (founder correction, issue #24 follow-up). 0.8.1 gave `/update` and `/end` the identical
  reconcile contract, including the same power to remove/close a ledger item. `/update` runs
  often, sometimes from several panels within the same hour — that shared delete path is exactly
  the surface that lets one panel's cleanup collide with another panel's still-open thread.
  `/update` may now only add a new item, update its own item's context, or flag one `stale?`;
  it never closes one, even its own. `/end` is unchanged: the sole, deliberate, evidence-cited
  (or promotion-with-pointer) point where an item leaves the ledger. Non-destructive by design if
  `/end` is skipped for a while — closed-but-unpruned items are noise, not corruption, and the
  existing `stale?` flag already surfaces them.
## 0.8.1

### Changed
- **`current.md` becomes an open-items LEDGER with reconcile semantics** (founder design session).
  Blind overwrite loses other panels' open items — the very fear that bred checkpoint stacking;
  append breeds 83KB diaries (a live 62-checkpoint file was purged today). `/update` and `/end` now
  READ the file first and reconcile: an item leaves ONLY by evidence-named closure or by promotion
  to an issue/plan (which leaves a `→ #123` pointer, never a silent delete); other owners' items
  are untouchable; idle >14d → flagged `stale?`, never auto-dropped. **Size is an output of the
  only-open-truth discipline, never an eviction criterion** — 10 open items = 10 items, each with
  its 1–3 lines of context; shipped-work narrative goes to the session log, decisions to
  decisions.md. `/start` reads it as the ledger and never drops open items itself.

## 0.8.0

### Added
- **Scoped pre-authorization (founder-granted).** `config.yml` may grant a contributor
  `auto_authorized: secondary`: the plan's secondary items start before the CEO signature
  (`status: auto-authorized`, surfaced by `/start` as startable). The grant lives in
  founder-owned `config.yml` ONLY — a self-provisioned profile can never grant it. The primary
  outcome and anything touching production or client-facing surfaces always waits for the
  signature. Closes G4 gap #3 (founder-bottleneck) without an SLA: the gate stays where it
  protects, disappears where it strangles.

## 0.7.12

### Added
- **`## Bottleneck` — mandatory section in `/report`.** The single biggest thing that slowed the
  week (from the evidence, not vibes) + ONE concrete removal proposal. Never "none" — a week with
  no named bottleneck means the author didn't look. Turns continuous bottleneck-hunting into a
  per-person async ritual (G4 gap #2, ai-native-engineering-team reference); the removal proposals
  feed PM action.

## 0.7.11

### Changed
- Version dropped from the brief header (founder: noise once the cache-staleness hunt is over) —
  header is now `{Greeting}. {Weekday} {date} — <repo> on <branch>`.

## 0.7.10

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- The brief renders as plain markdown, **never inside a code fence** — a fenced brief shows
  literal asterisks instead of bold section headers in the terminal (founder caught it live).

## 0.7.9

### Changed
- **Brief goes MARVIN-style.** Founder UX iteration: bold section headers with bullets
  (**THIS WEEK / PULSE / MEMORY / LAST SESSION / MY CALL**) instead of one-emoji-per-line; empty
  sections are omitted, never padded. Greeting + date + version header; ⛔ stale-checkout line
  still leads when the tree is behind. Headers translate to the profile `language:`; structure
  stays invariant across voices.

## 0.7.8

### Changed
- Brief template breathes: blank lines between the four blocks (header / this week / pulse /
  evidence+close) — ten content lines, never a squashed wall (founder UX feedback).

## 0.7.7

### Added
- **`voice:` in the contributor profile.** Per-contributor TONE for the brief: `cynical` (default
  dry co-pilot), `plain` (neutral, facts only), or a free-text tone line. Structure is invariant
  whatever the voice — fixed icons, rated `▶ My call`, evidence-grounded 💬 verdict, motivational
  ban: that's the product, not the personality.

## 0.7.6

### Added
- **`language:` in the contributor profile.** `/start` writes the brief in the contributor's own
  language (`language: it` → Italian lines under the same fixed icons); committed artifacts keep
  the repo convention. Default `en` when absent.

## 0.7.5

### Changed
- **Cynical co-pilot voice.** Motivational language is banned outright; "merged" is a fact,
  "great progress" is not. Two new closing lines: `💬 Last session:` — one dry verdict on what it
  actually moved (from the log, not from charity; unproven "done" claims get called out) — and
  `▶ My call:` — a ranked recommendation with blunt scores (n/10, leverage vs cost) and a
  one-clause why. The user overrules, but never gets a menu without a recommendation. Closes the
  iter-3 "ranked-recommendation nel briefing" item.

## 0.7.4

### Changed
- **The brief gets a face.** Fixed icon scheme (🧭 header · 🎯 outcome · 🔨 active · 📦 landed ·
  🌊 in motion · 🧪 proof · ⚠️/✅ blocker · 🧠 recall · ▶ first move) — the icons are the scanning
  UI. Voice: calm co-pilot on the radio — verb-first, punchy, dry wit at most one line, never
  instead of a fact.
- **Version in the header.** The brief opens with `· Team OS v<version>` read from plugin.json at
  runtime — no more guessing which cached release answered.

## 0.7.3

### Changed
- **The answer is the brief, not a reading diary.** `/start` outputs the ten-line brief only — no
  "everything read, nothing relevant" narration, no tool-log recap (live-run UX feedback). One
  exception leads: a checkout behind `origin/main` opens the answer with the action line
  ("pull before working"), because everything else was read from a stale tree.

## 0.7.2

### Changed
- **Context budget caps in `/start`.** A live measure on a mature repo found the real context cost
  is not the skill (+~1k tokens across 0.4.2→0.7.1) but uncapped inputs: `decisions.md` at 111KB
  (~28k tokens) and `hot.md` at 20KB. `/start` now reads the 10 most recent decisions/lessons
  entries, the first screen of `hot.md`, and treats a >30-line `state/current.md` as a decayed
  diary (read newest block, flag for trim). Older context is recall's job, on demand.

## 0.7.1

### Changed
- `/start` closes with an explicit build-method bridge: when the chosen first move is code, enter
  through the Superpowers flow (brainstorm → plan → TDD) or the workflow skill the repo's CLAUDE.md
  names — never straight into edits from the brief. No skill is force-loaded at session start:
  Superpowers already self-injects via its own SessionStart hook, and orientation sessions stay
  cheap.

## 0.7.0

### Added
- **`/start` repo pulse.** The brief is now a situational view, not a file read-back: after the
  contract files, `/start` grounds the LIVE state — `git log origin/main -5` (what landed),
  `git branch -vv --sort=-committerdate` (branches in motion, ahead/behind), `gh pr list` (open
  PRs by owner) — and treats plan-vs-pulse mismatches as brief-worthy collisions. Where the plan
  and the pulse disagree, the pulse wins.
- **polmem two-pass at start.** Warm recap first (`.wiki/hot.md` — what the repo's memory has been
  touching lately, zero queries), then the targeted recall; with no signed plan the query derives
  from the last session log + last landed commits.
- Brief grows to ten lines with `Recently landed:` and `In motion:`.

## 0.6.5

### Changed
- `/start` description slimmed to what the user sees in the command palette: "start a session —
  branch check, current state and recent decisions, polmem recall, 7-line brief; provisions your
  team path only on first use". Behavior unchanged.

## 0.6.4

### Changed
- **Founder-vault resolver case.** A repository whose root IS `_polaris` (the founder vault) now
  resolves to its own root when it carries `./config.yml` — one flow everywhere, no parallel
  founder-only session skills. Part of the single-method consolidation: the personal MARVIN-era
  `/start` `/end` `/update` command files are retired on the founder machine; the CEO layer is an
  external pull-based skill, never a second write path.

## 0.6.3

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it. (second external review, gpt-5.6 — 3 High, 3 Medium)
- **Identity gate now gates** (High): the v0.6.2 `grep || echo` continued on failure and skipped
  pre-existing profiles entirely. The gate hard-stops (`|| { …; exit 1; }`) and runs in BOTH
  branches — fresh or pre-existing profile.
- **Non-Claude users no longer stranded by the failure branch** (High): `command not found: polmem`
  now routes Codex/Cursor users to the checkout shim (`python3 <checkout>/polaris/bin/polmem`)
  instead of a Claude-only installer that exits 127 without a plugin cache.
- **The `/end` journal line reaches the team** (High): `polmem remember` writes `.wiki/journal/…`,
  but the offered pathspec commit staged only sessions/weeks — the journal file is now part of the
  handoff commit.
- `/start` never briefs an unsigned weekly file as active work (`execution_authorized` checked);
  commit evidence paginates (`gh api --paginate`); onboarding preflights the GitHub CLI
  (`gh --version`, `gh auth status`, `gh auth login`).
- All pinned in `test_terra_review_findings_stay_fixed`.

## 0.6.2

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it. (external Codex review of v0.5.0..v0.6.1 — 3 High, 5 Medium, 2 Low)
- **Self-provisioned profile kept `github: octocat`** (High): `/start` now rewrites the login
  (`perl -pi`) and gates on `grep -q "^github: $LOGIN$"` — a template login silently targets the
  wrong GitHub user in every evidence query.
- **AGENTS.md promised polmem to non-Claude CLIs the installer couldn't deliver** (High): the
  installed launcher resolves the Claude plugin cache only; non-Claude agents now get the checkout
  path (`python3 polaris/bin/polmem`, alias documented).
- **`remember` writes committed history but docs said polmem "only reads"** (High): read/write
  split stated everywhere; explicit privacy rule (no secrets/credentials/customer data/PII) on the
  `/end` journal line; shim header corrected.
- `gh pr/issue list` now pass `--limit 200` (default 30 truncated busy weeks); open PRs labeled
  "open at report time" (not reconstructable as of a past week); an unsigned plan is reported as an
  **unapproved proposal**, never a commitment baseline; decisions/lessons proposals carry the
  `(@<login>)` owner marker so report attribution is deterministic; `/end` commit snippet uses
  `$LOGIN` instead of literal placeholders; worked-example weekdays corrected.
- All fixes pinned in `test_codex_review_findings_stay_fixed`.

## 0.6.1

### Changed
- **`/end` feeds the repository memory.** After the handoff block, one machine-readable line goes
  into the repo journal (`polmem remember "session … — next: …"`); the offline distill decides what
  is durable. This closes the daily memory cycle mechanically — `/start` consumes (recall), `/end`
  feeds — for every contributor, since `remember` ships in the thin repo bundle. Same failure
  branches as `/start` (never `polmem init`).

## 0.6.0

### Changed
- **`/report` is a real report now, not a diff table.** Modeled on the production weekly reports
  (a product repo, W20–W27): `TL;DR` → `Planned versus actual` → `Day by day` (from the contributor's session
  logs, each linked) → `Merged PRs` (ground truth from `gh`, LOC + merge SHA; where logs and `gh`
  disagree, `gh` wins) → `Decisions in range` → `Blockers and incidents` → `Metrics` (derived at
  report time, never copied) → `PM action` (what the CEO must decide) → `Next week`. Scales
  honestly: a quiet week is a short report — never pad.
- **Evidence wiring fixed by a live REAL test.** Commits are resolved login→commits **server-side**
  (`gh api repos/$REPO/commits?author=$LOGIN&since=…&until=…`): the previous author-email approach
  returned zero on a real repo because squash commits carry the user's configured (personal) email,
  not the noreply form. `git fetch --prune` precedes evidence gathering; open PRs at end of range
  are part of the picture. This closes audit finding #5 (thin evidence commands) — commit/PR
  evidence now links into the repo graph mechanically, not "a intuito".
- Weekly-report template rewritten to the new structure.

## 0.5.2

### Added
- **`_polaris/README.md` template** (`polaris/templates/repo-contract/README.md`) — the contract's
  front door in every product repo: structure table (who writes what), the locked rules (single
  root, own-path provisioning, CEO signature gate, tracker stays the execution truth) and the
  privacy boundaries (no personal capacity data, no mentor/investor terms, neutral commit
  messages). Evolved from a product repo's pre-Team-OS README.
- **`AGENTS.md` bridge** — the five skills are consumable by non-Claude agent CLIs (Codex, etc.)
  from a plain repo checkout: skill index with relative paths, `$CLAUDE_PLUGIN_ROOT` substitution
  note, contract root and boundary rules. Contract-tested.
- `team/<login>/handoff/` documented as the optional home for rich multi-session handoff docs.

### Decided (layout frozen)
- `weeks/` + `reports/` stay separate siblings — the identical ISO-week filename pairs them by
  construction; a `weekly/` merge would buy one click and cost a 3-surface migration.
- `team/<login>/` stays (vs bare `_polaris/<login>/`) — it separates people-space from contract
  files and keeps skill globs (`team/*/weeks/`) unambiguous.
- `state/current.md` stays at the root — ephemeral and per-checkout; moving it under a login adds
  no isolation.

## 0.5.1

### Changed
- **Plans are authored by their owner.** `/plan-week` now states it explicitly: the plan file lives
  in **your own** `team/$LOGIN/weeks/` (login from `gh api user`, same resolver as `/start`) and you
  never write another contributor's plan — the CEO reviews and signs (`ceo_signature`), they don't
  write it for you. Locked with the founder 2026-07-13 after a pre-created plan shipped into a
  product repo.
- **Worked examples de-placeholdered.** `/plan-week` and `/report` examples used `team/jeanpierre/`
  — the exact placeholder-login pattern that broke a real contract. Now `team/octocat/`, and the
  release contract test forbids placeholder logins in the skills.

## 0.5.0

### Changed
- **Single Polaris root: `_polaris/`.** The dual-root resolver (`polaris/` or `_polaris/`) is gone —
  it drifted from the convention every product repository already uses, and per-repo root choice is
  exactly how one repository ended up carrying both roots at once. `/start` and `/update` now
  resolve `_polaris/config.yml` only; README, onboarding and the release contract tests pin it.
- **Self-provisioning contributor paths.** A contributor's `team/<login>/` path is created by
  **their own first `/start`**, from the exact login `gh api user --jq .login` returns on their
  machine: profile.yml (from the plugin template), `weeks/`, `reports/`, `sessions/`. Nobody
  pre-creates paths for other people, and no login is ever guessed — placeholder folders
  (e.g. `team/jeanpierre`) silently break every `gh` evidence query.
- **`lessons.md` joins the contract.** Product repos carry `<root>/lessons.md` next to
  `decisions.md`; `/end` proposes durable lessons through the same confirm-before-write gate, and
  `/start` reads it alongside decisions.

### Migration
- Repositories that carried a `polaris/` root (no underscore): the repo owner renames it
  (`git mv polaris _polaris`) and deletes pre-created placeholder `team/` folders — real paths are
  recreated by each contributor's `/start`. See the migration note in `docs/TEAM-ONBOARDING.md`.

## 0.4.4

### Changed
- **Per-contributor sessions path.** Session logs move from the shared `<root>/sessions/` to the
  per-contributor `<root>/team/<login>/sessions/` — the same isolation `weeks/` and `reports/`
  already use, so contributors never write to a shared, collision-prone directory. `/update` and
  `/end` now append to `team/<login>/sessions/YYYY-MM-DD-@<login>.md`; `/start` reads its own recent
  session logs from the same path and globs `team/*/sessions/` for cross-contributor
  collision-awareness, alongside the existing `team/*/weeks/` check.
- README's repo-contract tree and `docs/TEAM-ONBOARDING.md`'s contract checklist updated to show
  `sessions/` nested under `team/<login>/`.

### Migration
- Repositories on ≤0.4.3: move existing `<root>/sessions/*-@<login>.md` files into
  `<root>/team/<login>/sessions/`. See the migration note in `docs/TEAM-ONBOARDING.md`.

## 0.4.3

Iteration from a live 6-run benchmark (with-skill vs baseline) — objective defects only.

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- **`/report` ISO-week off-by-one.** The report week is now the ISO week of the *period being
  reported* (`date +%G-W%V`; explicit `WEEK` for a past week), and the evidence window is derived
  from that week via `datetime.fromisocalendar`, so filename and evidence can no longer diverge. A
  run had filed a W28 report as W29.
- **`/report` used the local machine's git identity.** Evidence now queries the tracker by the
  contributor's GitHub login (`author:$LOGIN`) instead of
  `git log --author="$(git config user.email)"`, which resolves to whoever runs the command. Added a
  branch-sync guard: verify commit authorship before crediting a PR.
- **`/plan-week` ranking buried critical issues.** Severity now strictly outranks age: a
  `[CRITICAL]`/priority-labelled issue always ranks above an older non-critical one; staleness is the
  final tiebreak only.

### Added
- **`/plan-week` scope grounding.** When `preferred_areas` is empty, the skill looks for scope
  evidence in the repo (onboarding docs, `CODEOWNERS`, the contributor's recent PRs) and proposes
  updating `profile.yml` before ranking.
- **polmem not-memory-wired branch.** `/start` (and, by reference, `/plan-week` and `/report`)
  documents the real failure: tell the repo owner, do **not** run `polmem init` yourself. Reaffirms
  `recall` is assumed context, not current state.
- Tests for the week computation, login-based evidence, severity ranking, scope grounding, the
  not-wired branch, and template existence/English/worked-example parity.

### Changed
- Repo-contract templates (`config.yml`, `profile.yml`, `weekly-plan.md`, `weekly-report.md`)
  reconciled to English and aligned exactly to the skills' worked examples. The `github` field is
  now documented as the exact, case-sensitive GitHub login. Skills reference the plugin template path
  (`$CLAUDE_PLUGIN_ROOT/...`) so it always resolves.
- Genericised founder-specific strings in the `polmem` CLI (repo owner / CI).
- Professional README pass and English onboarding.

## 0.4.2 and earlier

Reduced the surface to the five repository-first commands plus the `polmem` CLI; removed the
founder-vault coupling, the bootstrap command, and duplicate report commands. Established the
committed repo-contract model and the plugin release gates (`check_skills.sh`, contract tests).
