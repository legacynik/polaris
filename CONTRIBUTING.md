# Contributing

A change to a skill lands as a pull request against `main` that passes the gates below. Users only
receive what merges to `main`, through `npx skills update -g -y`.

## Propose a skill change

1. Open an issue that names the skill, the behaviour you saw, and the behaviour you want. A bug
   carries the input that reproduces it.
2. Branch from `main`, change the skill folder under `skills/<skill>/`, and raise its
   `version:` in the `SKILL.md` frontmatter. Every skill touched by the PR must move its version.
3. Add a public English entry under `## Unreleased` in [CHANGELOG.md](CHANGELOG.md): what changes
   for the user, and the skill with its new version.
4. If the change alters what a skill does, invokes, reads from `_polaris/config.yml` or refuses to
   do, update its section in [docs/skills.md](docs/skills.md) and, when the one-line summary changes,
   the table in [README.md](README.md).
5. Run the gates, then open the PR.

A new skill follows the same path, plus one row in the README table, one section in
`docs/skills.md`, and its path in `.claude-plugin/marketplace.json`. Its description starts with
`◇ `; a new session command instead starts with `Polaris skill — ` and is added to the list in
`check_skills.sh`.

## What every skill must hold

- **Self-contained.** A skill runs with only what its folder and the other skills in
  `skills/` carry. It never calls a skill, script or path outside the package, and it never
  asks the user to run anything under `bin` or `scripts`: the skills CLI does not
  install those.
- **Adapts through the repository.** Repository-specific values (tracker, labels, output paths,
  deploy workflows) come from the product repository's `_polaris/config.yml`. A missing key is named,
  never guessed.
- **Credits only in `CREDITS.md`.** Upstream sources and licenses go in the skill's own
  `CREDITS.md`, listed in the root [CREDITS.md](CREDITS.md). Never in `SKILL.md`, a reference or a
  script.
- **No README at the root of a skill folder.** `SKILL.md` is the entry point.
- **No private names.** No customer, person or infrastructure name, no machine path, no credential.

## Gates

Run from the repository root, on your branch, after merging `origin/main`:

```bash
bash scripts/check_skills.sh
python3 scripts/check_skill_versions.py origin/main
uvx --with pyyaml pytest tests -q
```

| Gate | Fails when |
|---|---|
| `check_skills.sh` | a skill's description lacks the `◇ ` mark, it names a retired or private path, or the `start` settings hook fails its selfcheck |
| `check_skill_versions.py` | a skill changed against the base without raising its `version:` |
| `pytest tests` | a shipped script, template or contract test breaks |

Before a release, the maintainer also runs `package_perimeter.py` over `skills`: it refuses a
machine path, a private name or a key-shaped string in any shipped file. It is not part of this
repository, so a contributor cannot run it; a PR that fails it is sent back with the finding.
