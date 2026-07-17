#!/usr/bin/env bash
# polaris/scripts/check_skills.sh — shipped command-surface gate
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
fail=0
expected=$'end\nplan-week\npolaris-grill\npolaris-status\nreport\nstart\nupdate'
actual=$(find skills -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)
[[ "$actual" == "$expected" ]] || {
  echo "FAIL commands: expected start/polaris-status/polaris-grill/update/end/plan-week/report"; fail=1;
}
for f in skills/*/SKILL.md; do
  name=$(basename "$(dirname "$f")")
  desc=$(sed -n 's/^description: //p' "$f" | head -1)
  case "$name" in
    start|polaris-status|polaris-grill|update|end|plan-week|report) ;;
    *) echo "FAIL command: $name"; fail=1;;
  esac
  [[ "$desc" == "Polaris skill — "* ]] || { echo "FAIL desc prefix: $name"; fail=1; }
  if grep -nE 'POLARIS_VAULT|Desktop/All Vibe Proj|pol-bootstrap|pol-report|pol-base-workflow' "$f"; then
    echo "FAIL legacy or founder-vault reference: $name"; fail=1
  fi
done
[[ $fail -eq 0 ]] && echo "check_skills: OK"
exit $fail
