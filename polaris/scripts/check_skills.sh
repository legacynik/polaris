#!/usr/bin/env bash
# polaris/scripts/check_skills.sh — naming + path hygiene gate (spec D5 + de-hardcoding)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
fail=0
for f in skills/*/SKILL.md; do
  name=$(basename "$(dirname "$f")")
  desc=$(sed -n 's/^description: //p' "$f" | head -1)
  case "$name" in
    start|update|end) ;;                       # bare names allowed
    pol-*) ;;                                  # convention
    *) echo "FAIL name: $name (must be pol-* or start/update/end)"; fail=1;;
  esac
  [[ "$desc" == "Polaris skill — "* ]] || { echo "FAIL desc prefix: $name"; fail=1; }
  # absolute founder paths allowed ONLY in the vault-resolution block
  bad=$(grep -n "Desktop/All Vibe Proj" "$f" | grep -v "Vault resolution" -A0 || true)
  block_line=$(grep -n "## Vault resolution" "$f" | cut -d: -f1 || true)
  while IFS=: read -r ln _; do
    [[ -z "$ln" ]] && continue
    if [[ -z "$block_line" ]] || (( ln < block_line )) || (( ln > block_line + 15 )); then
      echo "FAIL hardcoded path outside resolution block: $name:$ln"; fail=1
    fi
  done <<< "$(grep -n 'Desktop/All Vibe Proj' "$f" || true)"
done
[[ $fail -eq 0 ]] && echo "check_skills: OK"
exit $fail
