---
title: start — first use and the resume paths
description: Steps 1b–2 of the pre-form start body, kept verbatim: how resume_paths.sh resolves the paths, and what first use provisions.
status: active
---

## Step 1b — One home (every path below comes from here, never from the cwd)

```bash
eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"
```

`MAIN_WT`, `ROOT`, `LOGIN`, `CURRENT` (this repo's ONE cockpit) and `RADAR` all resolve against the MAIN
worktree. Non-zero exit: read the message and stop, never guess a path. The script resolves the
contract in `_polaris/` (`_polaris/config.yml`, else where the repository root is itself named `_polaris` and
carries `./config.yml`,
else stop and point to `docs/TEAM-ONBOARDING.md`) and the identity
(`git config --local --get polaris.login`, else `gh auth status` and `gh api user --jq .login`
cached once with `git config --local polaris.login`).

## Step 2 — Provision your own team path (first use only)

If `$ROOT/team/$LOGIN/profile.yml` is absent, provision **only that contributor's** path from the
plugin template. Never create `team/<login>/` folders for other people.

```bash
mkdir -p "$ROOT/team/$LOGIN/weeks" "$ROOT/team/$LOGIN/reports" "$ROOT/team/$LOGIN/sessions"
cp "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/templates/repo-contract/profile.yml" "$ROOT/team/$LOGIN/profile.yml"
perl -pi -e "s/^github: .*/github: $LOGIN/" "$ROOT/team/$LOGIN/profile.yml"
```

Then install the team settings — the permissions preset and the compaction hook of Step 3b.
It merges and never clobbers: a second run changes nothing and says so, and a
`.claude/settings.json` it cannot parse stops it (`SETTINGS_UNREADABLE`, exit 1, nothing
written) rather than being replaced.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/install_settings.py" --repo "$MAIN_WT"
```

Hooks are read at session start, so the one it writes takes effect from the NEXT session.

The identity gate runs in BOTH branches, whether the profile was just created or already existed:

```bash
grep -q "^github: $LOGIN$" "$ROOT/team/$LOGIN/profile.yml" \
  || { echo "STOP: profile github: does not match cached login ($LOGIN) — fix it first"; exit 1; }
```
