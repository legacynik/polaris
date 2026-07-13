# Changelog

All notable changes to Polaris Team OS. The installed version is pinned in
`polaris/.claude-plugin/plugin.json`.

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

### Fixed (second external review, gpt-5.6 — 3 High, 3 Medium)
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

### Fixed (external Codex review of v0.5.0..v0.6.1 — 3 High, 5 Medium, 2 Low)
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
  (noemi W20–W27): `TL;DR` → `Planned versus actual` → `Day by day` (from the contributor's session
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
  messages). Evolved from the noemi-ai pre-Team-OS README.
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
