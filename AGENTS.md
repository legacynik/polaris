# AGENTS.md

## Project overview

This repository is the Polaris skills package: each skill is a folder under `polaris/skills/<skill>/`
whose `SKILL.md` an agent follows. Users install and update it only through the skills CLI.

The skill list and the `_polaris/config.yml` keys each skill reads live in [README.md](README.md)
and [docs/skills.md](docs/skills.md); do not copy them here. How the structures work (delivery
cycle, plan file, tracking, decisions, documents, context pack, sessions, memory) is in `docs/`.
The router is [base-workflow](polaris/skills/base-workflow/SKILL.md); the session commands are
[start](polaris/skills/start/SKILL.md), [end](polaris/skills/end/SKILL.md),
[status](polaris/skills/status/SKILL.md) and [week](polaris/skills/week/SKILL.md).

## Setup

```bash
git clone https://github.com/legacynik/polaris && cd polaris
H="$(mktemp -d)"   # a clean install never touches your real HOME
HOME="$H" npx skills add "$PWD" -g --skill '*' -y
ls "$H/.agents/skills"   # one folder per skill under polaris/skills
```

## Test commands

Run all of them from the repository root; every one must pass before a PR.

```bash
bash polaris/scripts/check_skills.sh
python3 polaris/scripts/check_skill_versions.py origin/main
uvx --with pyyaml pytest polaris/tests -q
# every selfcheck of the clean install above (tdd-dev's need pytest on the path)
for f in "$H"/.agents/skills/*/scripts/*.py; do
  grep -q -- --selfcheck "$f" && { HOME="$H" uv run --no-project --with pytest python "$f" --selfcheck >/dev/null || echo "FAIL $f"; }
done
```

## Conventions

- Skill bodies (`SKILL.md`, `references/`) are English.
- Each skill is self-contained: it runs with its own folder and the other skills in
  `polaris/skills/`, and never calls a skill, script or path outside the package.
- Credits go only in the skill's own `CREDITS.md`, indexed from [CREDITS.md](CREDITS.md); the body
  cites no donor.
- No README inside a skill folder.
- Any change to a skill's files bumps its `version:`.
- No customer, person or infrastructure names anywhere in a skill.

## PR instructions

One PR per batch of changes, opened only after every test command above is green. The full flow,
including the CHANGELOG entry and the docs to update, is in [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

- Never commit secrets, tokens or keys; the perimeter scan refuses key-shaped strings.
- Files under `polaris/bin` and `polaris/scripts` never reach users (the CLI installs skill folders
  only), so no skill may depend on them.
- The contract root in a product repository is `_polaris/`; a `team/<login>/` folder is its owner's
  exact GitHub login, and no agent creates another person's path.
