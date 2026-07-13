# Polaris Team OS — agent instructions (tool-agnostic)

This repository ships the Polaris Team OS skills. In Claude Code they install as a plugin (see
[README](README.md)). Any other agent CLI (Codex, Cursor, etc.) uses them straight from a checkout
of this repository: read the relevant SKILL.md below and follow it exactly.

## Skills

| Command | File | Purpose |
|---|---|---|
| start | [polaris/skills/start/SKILL.md](polaris/skills/start/SKILL.md) | Begin a session: verify the branch, resolve the `_polaris/` contract, self-provision your own `team/<login>/` on first run, recall memory, brief |
| update | [polaris/skills/update/SKILL.md](polaris/skills/update/SKILL.md) | Mid-session checkpoint in your own `team/<login>/sessions/` |
| end | [polaris/skills/end/SKILL.md](polaris/skills/end/SKILL.md) | Close a session: handoff, decision/lesson proposals, optional pathspec-only commit |
| plan-week | [polaris/skills/plan-week/SKILL.md](polaris/skills/plan-week/SKILL.md) | Your own weekly plan — a proposal until the CEO signs it |
| report | [polaris/skills/report/SKILL.md](polaris/skills/report/SKILL.md) | Weekly report — planned versus actual, evidence from the tracker |

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
  commands, plans need the CEO signature before execution, propose-then-confirm for
  `decisions.md` / `lessons.md`.
