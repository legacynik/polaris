# ship — the optional pre-command hook

A tripwire, not a security boundary: the binding control is `babysit` (the owner's label on the
head SHA, server state) and branch protection. Opt in per repository.

## What it catches

`scripts/pre_tool_hook.py` reads one shell command and blocks (exit 2) the default spelling of:

- any raw merge (`gh pr merge`, the merge API): merges go through `merge_gate.py execute`;
- `gh pr create` without a clean redaction scan, the version and changelog checks the `ship:`
  contract declares, or a fresh real-test verdict (drafts skip the verdict);
- `gh pr create|new|ready|edit` with a body that `pr`'s checker refuses.

Shell wrappers (`bash -c`, `eval`, subshells) and `gh api` calls other than the merge endpoints
are not read, so they are not judged. Any internal error blocks. The emergency bypass
`SHIP_BYPASS_GATE=1` is logged.

## Wiring it in your harness

Any harness that runs a hook before each shell command can call it, as long as the hook pipes a
JSON object carrying the command at `tool_input.command` on stdin:

```bash
echo '{"tool_input": {"command": "gh pr merge 9"}}' | python3 <skill-dir>/scripts/pre_tool_hook.py
echo $?   # 2 = blocked
```

- A harness with a pre-tool hook on its shell tool: register
  `python3 <skill-dir>/scripts/pre_tool_hook.py` as that hook, matched on the shell tool only.
  Example (Claude Code): `.claude/settings.json` → `hooks.PreToolUse`, matcher `Bash`.
- A harness whose hook sends another shape: wrap it with a few lines that re-emit
  `{"tool_input": {"command": …}}`.
- A harness with no such hook: skip it; `babysit` and branch protection still hold.

Proof: `python3 scripts/pre_tool_hook.py --selfcheck` and `references/bypass-test.md`.
