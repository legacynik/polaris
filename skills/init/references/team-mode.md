# init --team — team mode, in detail

Prior art: gstack's `gstack-team-init required|optional` (garrytan/gstack `bin/gstack-team-init`,
`bin/gstack-session-update`). Kept: the two modes, the session-start auto-update throttled to once
an hour, silent and fail-open, and `required` enforced by a hook that denies skills, because a
session-start hook cannot stop a session. Changed: the version is **pinned** (gstack follows
latest), the install is `npx skills add` at that tag, and the rule is also written to `AGENTS.md`
so every harness reads it, not only Claude Code.

## What is written

| File | Content |
|---|---|
| `.polaris/team.json` | `mode`, `ref`, `source` = `https://github.com/<owner>/<name>/tree/<ref>/skills` |
| `.polaris/session-start.sh` | the hook below; POSIX `sh`, no dependency beyond `npx` |
| `.claude/settings.json` | SessionStart → the hook; `required` adds PreToolUse `Skill` → the hook with `--check` |
| `AGENTS.md` | one section between `<!-- polaris-team:start -->` and `<!-- polaris-team:end -->` |

Re-running rewrites only these; foreign hooks and the rest of `AGENTS.md` stay. Switching from
`required` to `optional` removes the PreToolUse check.

## The hook

- **SessionStart.** Pin installed (`~/.polaris/installed-<pin>` exists): exit 0, silent, no network
  — a pinned tag never changes, so the update is a new pin. Otherwise, when the stamp
  `~/.polaris/checked-<pin>` is older than 60 minutes, it touches it and starts
  `npx -y skills add <source> -g -y --skill '*'` in the background; success writes the marker. It
  always exits 0 and prints one line: `optional` recommends, `required` says STOP.
- **--check** (`required` only, before every skill). Pin installed: exit 0, silent. Not installed:
  exit 2 with the install command on stderr, which the harness shows while it blocks the call.

`required` blocks skill calls, not the whole session: a session-start hook cannot stop a session,
and blocking every prompt would make an offline teammate's repo unusable. The `AGENTS.md` STOP rule
covers the rest, as in gstack.

Known ceiling: the marker is per pin, so skills removed by hand are not noticed until the pin
changes. Bumping the pin = edit `ref` and `source` together, or re-run `init --team` with `--ref`.

## Choosing the pin

`<owner>/<name>` is the repository Polaris was installed from (the `source` of `init` in
`~/.agents/.skill-lock.json`); `polaris_team.py` takes it as `--repo`, or from `POLARIS_REPO`, and
names none of its own.

```bash
gh release view --repo <owner>/<name> --json tagName --jq .tagName
```

Pin a released tag, never a branch: a branch moves under every teammate at once.
