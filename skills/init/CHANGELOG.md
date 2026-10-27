# Changelog — init

## 0.7.1 — 2026-10-27

- `--team` writes the pinned skills source as `https://github.com/<owner>/<name>/tree/<ref>/skills`:
  the package now keeps its skills at the repository root, not under `polaris/`.

## 0.7.0 — 2026-10-27

- **Ships the dependency installer**: `scripts/install_deps.py` (moved from the lab's
  `_standard/`) — `deps` plans the binaries (bd, browser-harness, serena), the MCP servers
  (Serena, Context7, Sequential Thinking, ai-memory) and Beads per harness through each harness's
  own command, `--apply` runs them; `doctor` is read-only (skills per harness, missing deps per
  Polaris skill, homonyms, dead hooks, judge keys by presence). It reads the skills root it is
  installed in, recognises Polaris skills by `◇ Polaris` in their description, writes a Claude
  Code hook only when a caller passes `--hook`/`--mark` (the lab's `install.sh --deps` does), and
  `--selfcheck` runs both modes in a throwaway HOME. No value from a config or env var is printed.
- `description:` names bd (Beads) and browser-harness, which the installer now carries
  (promote's dependency rule). Eval `n02` (install the deps on my machine) becomes positive `p07`.
- "When" names the installer; "Not for" no longer points at the lab's `install.sh`.
  Tests: `tests/test_install_deps.py` (RED recorded with `red_check.py`).

## 0.6.0 — 2026-10-25

- Public-package clean (C5): **`polaris_team.py` takes `--repo <owner>/<name>` (or `POLARIS_REPO`) and names no repository of its own**: a run without either exits 2 instead of pinning a hard-coded owner. SKILL.md step 5 and `references/team-mode.md` say where to find it (the install source in `~/.agents/.skill-lock.json`). Minor: an invocation without `--repo` now refuses.

## 0.5.1 — 2026-10-25

- `description:` quoted. Its unquoted `: ` ("harness: audit") made the installer's YAML parse
  throw, so `npx skills add` skipped init with one warning line. Caught by the new `yaml:` check
  of `_standard/validate_suite.py`.

## 0.5.0 — 2026-10-24

- Team mode, from gstack's `gstack-team-init`: `scripts/polaris_team.py --team required|optional
  --ref <tag>` writes the pin (`.polaris/team.json`), a SessionStart hook that installs or updates
  the pinned skills in the background at most once an hour, silently and fail-open, its
  registration in `.claude/settings.json`, and one `AGENTS.md` section for every other harness.
  `required` also blocks skill calls (exit 2) while the pin is missing; `optional` nudges. An
  installed pin is never fetched again (a new ref is the update). Idempotent.
  Tests: `tests/test_polaris_team.py` (RED recorded with `red_check.py`).
- The 60-line form: the body is the five fixed sections; the full procedure moved verbatim to
  `references/procedure.md`, team mode to `references/team-mode.md`. Description starts
  "◇ Polaris — " and names its hard deps (git, python3). The script path no longer names a
  harness variable. `[form: …]` lines removed from `_standard/nonconforming.allow`.
- Evals in the suite format: `eval/prompts.json` (10 cases, 4 negatives), `eval/checks.json`,
  `eval/split/`.

## 0.4.0

- Self-contained install: scripts ship in the skill, no vault required (#591).
