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
#   resume_paths.sh | resume_paths.sh --selfcheck
set -uo pipefail

# The fixtures: a checkout whose path holds a space and an apostrophe (polaris#14), the cockpit
# fallback, and the two refusals — no contract, no checkout — each exiting 2.
selfcheck() {
  local self d repo out fail=0
  self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
  d="$(mktemp -d)"; repo="$d/Team's \$repo"
  mkdir -p "$repo/_polaris" && git -C "$repo" init -q && git -C "$repo" config polaris.login ada
  ( cd "$repo" && bash "$self" >/dev/null 2>&1 ); [ $? -eq 2 ] || { echo "FAIL: no contract must exit 2"; fail=1; }
  : > "$repo/_polaris/config.yml"
  out="$(cd "$repo" && bash "$self")" || { echo "FAIL: a valid checkout exited non-zero"; fail=1; }
  ( eval "$out"
    top="$(cd "$repo" && git rev-parse --show-toplevel)"
    [ "$ROOT" = "$top/_polaris" ] && [ "$LOGIN" = ada ] \
      && [ "$CURRENT" = "$top/_polaris/state/current.md" ] && [ -f "$RADAR" ] ) \
    || { echo "FAIL: eval did not round-trip ROOT/LOGIN/CURRENT/RADAR: $out"; fail=1; }
  ( cd "$d" && bash "$self" >/dev/null 2>&1 ); [ $? -eq 2 ] || { echo "FAIL: outside a checkout must exit 2"; fail=1; }
  rm -rf "$d"
  [ "$fail" = 0 ] && echo "resume_paths selfcheck: ok (quoted paths · cockpit fallback · no contract · no checkout)"
  return "$fail"
}
[ "${1:-}" = "--selfcheck" ] && { selfcheck; exit; }

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
