# Polaris Team OS — agent instructions (tool-agnostic)

This repository ships the Polaris Team OS skills. In Claude Code they install as a plugin (see
[README](README.md)). Any other agent CLI (Codex, Cursor, etc.) uses them straight from a checkout
of this repository: read the relevant SKILL.md below and follow it exactly.

## Skills

| Command | File | Purpose |
|---|---|---|
| start | [polaris/skills/start/SKILL.md](polaris/skills/start/SKILL.md) | Resume the authorized outcome from the latest local handoff/checkpoint; self-provision your own `team/<login>/` on first run |
| polaris-status | [polaris/skills/polaris-status/SKILL.md](polaris/skills/polaris-status/SKILL.md) | Explicit full portfolio/repository pulse, team collisions, freshness, memory and health |
| polaris-grill | [polaris/skills/polaris-grill/SKILL.md](polaris/skills/polaris-grill/SKILL.md) | Repo-grounded product and technical interview with decision-complete execution handoff |
| update | [polaris/skills/update/SKILL.md](polaris/skills/update/SKILL.md) | Mid-session checkpoint in your own `team/<login>/sessions/` |
| end | [polaris/skills/end/SKILL.md](polaris/skills/end/SKILL.md) | Close a session: handoff, decision/lesson proposals, optional pathspec-only commit |
| plan-week | [polaris/skills/plan-week/SKILL.md](polaris/skills/plan-week/SKILL.md) | Your own weekly focus — yours to execute; only red work waits for a named approver |
| report | [polaris/skills/report/SKILL.md](polaris/skills/report/SKILL.md) | Weekly report — planned versus actual, evidence from the tracker |
| polaris-memory | [polaris/skills/polaris-memory/SKILL.md](polaris/skills/polaris-memory/SKILL.md) | Search/record team memory via the `polmem` CLI — recall-first before building; recall ≠ current state |
| pol-apex-curate | [polaris/skills/pol-apex-curate/SKILL.md](polaris/skills/pol-apex-curate/SKILL.md) | Curate a repo's `CLAUDE.md` apex — distill lessons/decisions into a ≤200-line, propose-only patch |

## Notes for non-Claude agents

- Where a skill references `$CLAUDE_PLUGIN_ROOT`, substitute the path of this repository checkout.
- Repo-contract templates live in [polaris/templates/repo-contract/](polaris/templates/repo-contract/).
- The `polmem` memory CLI: with Claude Code, install once per machine with
  `bash polaris/scripts/install-polmem-cli.sh` (adds `~/.local/bin/polmem`, resolved from the
  plugin cache). **Without Claude Code**, run the shim straight from this checkout — it finds the
  target repo's committed bundle from your working directory:
  `alias polmem='python3 /path/to/this-checkout/polaris/bin/polmem'`.
- `polmem recall` reads the repository's committed memory; `polmem remember` **writes** one line to
  the repo's committed journal — never put secrets, credentials, customer data or personal
  information in it.
- The contract root in every product repository is **`_polaris/`** — one root, never `polaris/`,
  never both. Your `team/<login>/` folder name is your exact GitHub login
  (`gh api user --jq .login`); never create another contributor's path.
- Boundaries the skills enforce apply to you too: no tracker mutations from the lifecycle
  commands, propose-then-confirm for `decisions.md` / `lessons.md`, and no signature gate on
  bounded reversible work — only **red** work (access/RLS/auth, personal data, processor/vendor,
  irreversible migration, legal/customer commitment, audited production promotion, material
  outcome/architecture change) waits for its **named** approver. If the repo ships a workflow
  charter (`profile.yml` → `workflow:`), that charter's boundaries win.
