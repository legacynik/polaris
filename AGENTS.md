# Polaris skills package — agent instructions

This repository is the Polaris skills package: every skill lives under `polaris/skills/<skill>/`,
and each `SKILL.md` is the instruction to follow, exactly.

## Install and update

Only through the skills CLI:

```bash
npx skills add legacynik/polaris -g --skill '*'   # install
npx skills update -g -y                           # update after a merge to main
```

The CLI installs skill folders only. A skill finds its own scripts and templates through
`${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/<skill>/`, so an installed skill needs nothing else.

## Where things are

- The skill list, what each skill does and the `_polaris/config.yml` keys it reads:
  [README.md](README.md) and [docs/skills.md](docs/skills.md). Do not copy that list here.
- The session commands, for an agent that does not load skills by itself:
  [start](polaris/skills/start/SKILL.md), [update](polaris/skills/update/SKILL.md),
  [end](polaris/skills/end/SKILL.md), [plan-week](polaris/skills/plan-week/SKILL.md),
  [report](polaris/skills/report/SKILL.md), [polaris-status](polaris/skills/polaris-status/SKILL.md),
  [polaris-grill](polaris/skills/polaris-grill/SKILL.md).
- The contract root in every product repository is `_polaris/`, never `polaris/`. Your
  `team/<login>/` folder name is your exact GitHub login; never create another person's path.

## Changing a skill

Follow [CONTRIBUTING.md](CONTRIBUTING.md): the branch and PR flow, the version bump, the changelog
entry and the gates a change must pass.
