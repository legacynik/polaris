# Changelog

All notable changes to Polaris Team OS. The installed version is pinned in
`polaris/.claude-plugin/plugin.json`.

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
