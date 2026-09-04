#!/usr/bin/env bash
# resume_paths.sh — the deterministic half of /start: WHERE this repo's session state lives.
#
# One home: every path resolves against the MAIN worktree, whatever tree the panel sits in.
# A panel in `.worktrees/x` that builds paths from its cwd grows a gitignored cockpit there
# that no merge ever brings back — four were found stranded in one repo, the oldest since
# 07/08. Shared by /start and /end so the rule has one implementation, not three copies.
#
# Prints MAIN_WT, ROOT, LOGIN, CURRENT, RADAR. Exits 2 rather than guessing.
set -uo pipefail

MAIN_WT="$(git worktree list --porcelain 2>/dev/null | head -1 | sed 's|^worktree ||')"
[ -n "${MAIN_WT:-}" ] || { echo "resume_paths: not a git checkout — stop, do not guess a path" >&2; exit 2; }

ROOT="$MAIN_WT/_polaris"; [ -f "$ROOT/config.yml" ] || ROOT="$MAIN_WT"
[ -f "$ROOT/config.yml" ] || { echo "resume_paths: no Polaris contract under $MAIN_WT — see docs/TEAM-ONBOARDING.md" >&2; exit 2; }
LOGIN="$(git config --local --get polaris.login 2>/dev/null || gh api user --jq .login 2>/dev/null)"
[ -n "${LOGIN:-}" ] || { echo "resume_paths: cannot resolve login — gh auth login, then git config --local polaris.login" >&2; exit 2; }

# THE cockpit: the #212 resolver where the repo carries it, the identical rule inline where
# it does not — the package ships to repos that have no vault scripts.
CURRENT="$(python3 "$ROOT/scripts/state_home.py" path 2>/dev/null)"
[ -n "${CURRENT:-}" ] || CURRENT="$ROOT/team/$LOGIN/current.md"
[ -f "$CURRENT" ] || CURRENT="$ROOT/state/current.md"

# The vault copy first, then the one shipped beside this script: a product repo has no vault
# to climb to, and without the shipped copy every one of them answered "radar assente".
RADAR="$ROOT/scripts/handoff_radar.py"
[ -f "$RADAR" ] || RADAR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/handoff_radar.py"
[ -f "$RADAR" ] || RADAR=none

# Every value is shell-quoted, because the caller `eval`s this. Unquoted, a checkout under a
# directory with a space in its name split into words and /start died at Step 1b with
# «command not found: Vibe» — on the founder's own vault (polaris#14). `%q` round-trips an
# apostrophe and a `$` too, so the path comes back byte-identical whatever is in it.
printf '%s=%q\n' MAIN_WT "$MAIN_WT" ROOT "$ROOT" LOGIN "$LOGIN" CURRENT "$CURRENT" RADAR "$RADAR"
