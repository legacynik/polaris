#!/usr/bin/env bash
# polaris/scripts/check_skills.sh — shipped skill-surface gate.
#
# Every skill is promoted from the lab and marks itself with a diamond in its own
# description (`◇ Polaris — `), so skills are READ, not listed: a hand list is a skill
# promoted upstream and forgotten here, green all the way to the release. Since 0.33.0 the
# session commands carry the same mark; the separate `Polaris skill — ` contract is retired.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
fail=0
doors=0
for f in skills/*/SKILL.md; do
  name=$(basename "$(dirname "$f")")
  # A quoted scalar is its content (YAML needs the quotes when the text holds ": ").
  desc=$(sed -n 's/^description: //p' "$f" | head -1 | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/")
  if [[ "$desc" == "◇ "* ]]; then doors=$((doors + 1))
  else echo "FAIL unknown skill (no ◇ marker in its description): $name"; fail=1; fi
  BANNED='POLARIS_VAULT|Desktop/All Vibe Proj|pol-bootstrap|pol-report|pol-base-workflow'
  if grep -nE "$BANNED" "$f"; then
    echo "FAIL legacy or founder-vault reference: $name"; fail=1
  fi
done
[[ $doors -gt 0 ]] || { echo "FAIL doors: none shipped — the suite sync never ran"; fail=1; }
# The compaction hook is a STRING in a template until somebody runs it, and a string is
# green under every breakage there is. Its selfcheck installs the template into a throwaway
# repository and EXECUTES the hook command twice — once with no resolver (must be silent and
# exit 0), once with one (must run it).
python3 skills/start/scripts/install_settings.py --selfcheck || fail=1
[[ $fail -eq 0 ]] && echo "check_skills: OK ($doors doors)"
exit $fail
