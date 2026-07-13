# Changelog

All notable changes to Polaris Team OS. The installed version is pinned in
`polaris/.claude-plugin/plugin.json`.

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
