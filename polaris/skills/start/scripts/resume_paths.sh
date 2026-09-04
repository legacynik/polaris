#!/usr/bin/env bash
# resume_paths.sh — the deterministic half of /start: WHERE this repo's session state lives.
#
# Two homes, one rule each. `ROOT` is THIS worktree's contract: the session log, the handoff and
# the plan tick live and commit where the panel runs, on the branch the session happened on.
# `CURRENT` — the gitignored cockpit — keeps the one-home rule and resolves against the MAIN
# worktree: a panel in `.worktrees/x` that grows its own cockpit grows one no merge ever brings
# back (four were found stranded in one repo, the oldest since 07/08).
# Shared by /start and /end so the rule has one implementation, not three copies.
#
# Prints MAIN_WT, ROOT, LOGIN, CURRENT, RADAR. Exits 2 rather than guessing.
set -uo pipefail

MAIN_WT="$(git worktree list --porcelain 2>/dev/null | head -1 | sed 's|^worktree ||')"
[ -n "${MAIN_WT:-}" ] || { echo "resume_paths: not a git checkout — stop, do not guess a path" >&2; exit 2; }

HERE_WT="$(git rev-parse --show-toplevel 2>/dev/null)"
MAIN_ROOT="$MAIN_WT/_polaris"; [ -f "$MAIN_ROOT/config.yml" ] || MAIN_ROOT="$MAIN_WT"
ROOT="$HERE_WT/_polaris"; [ -f "$ROOT/config.yml" ] || ROOT="$HERE_WT"
[ -f "$ROOT/config.yml" ] || { echo "resume_paths: no Polaris contract under $HERE_WT — see docs/TEAM-ONBOARDING.md" >&2; exit 2; }
LOGIN="$(git config --local --get polaris.login 2>/dev/null || gh api user --jq .login 2>/dev/null)"
[ -n "${LOGIN:-}" ] || { echo "resume_paths: cannot resolve login — gh auth login, then git config --local polaris.login" >&2; exit 2; }

# THE cockpit: the #212 resolver where the repo carries it, the identical rule inline where
# it does not — the package ships to repos that have no vault scripts.
CURRENT="$(python3 "$MAIN_ROOT/scripts/state_home.py" path 2>/dev/null)"
[ -n "${CURRENT:-}" ] || CURRENT="$MAIN_ROOT/team/$LOGIN/current.md"
[ -f "$CURRENT" ] || CURRENT="$MAIN_ROOT/state/current.md"

# The vault copy first, then the one shipped beside this script: a product repo has no vault
# to climb to, and without the shipped copy every one of them answered "radar assente".
RADAR="$MAIN_ROOT/scripts/handoff_radar.py"
[ -f "$RADAR" ] || RADAR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/handoff_radar.py"
[ -f "$RADAR" ] || RADAR=none

# Every value is shell-quoted, because the caller `eval`s this. Unquoted, a checkout under a
# directory with a space in its name split into words and /start died at Step 1b with
# «command not found: Vibe» — on the founder's own vault (polaris#14). `%q` round-trips an
# apostrophe and a `$` too, so the path comes back byte-identical whatever is in it.
printf '%s=%q\n' MAIN_WT "$MAIN_WT" ROOT "$ROOT" LOGIN "$LOGIN" CURRENT "$CURRENT" RADAR "$RADAR"
