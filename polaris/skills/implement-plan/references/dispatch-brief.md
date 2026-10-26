---
title: implement — the brief every task agent receives
status: active
---

# Dispatch brief (one task, one fresh-context agent)

The orchestrator fills the `<…>` fields from the claimed task bead and the plan file, and sends
the brief as the agent's whole context. The agent inherits nothing else: no conversation, no
earlier task. Adapted from the repository's subagent dispatch preamble (git rules, TDD gate,
report shape) and from superpowers' subagent-driven-development (fresh context per task, a
precise brief instead of history).

```markdown
## Task <bead id>: <bead title>

Plan: <plan file path> — read §5 Contracts and §6 DoD for this phase (<phase n>) only.
Acceptance: <bead acceptance / description>.
Scope: the only paths you may change: <globs>. Anything else is out of scope: stop and say so.

### Rules (no exceptions)
1. Work only in <worktree>, on branch <branch>. Run `git rev-parse --abbrev-ref HEAD` before
   every commit; another branch → stop.
2. Commit with an explicit pathspec (`git add -- <file>`), never `-A` or `.`. English messages.
   Never `reset --hard`, `checkout -- <file>`, `stash`, a merge, a push, a tag or a deploy.
3. Test first. Record the RED before any production code:
   `python3 <skills>/tdd-dev/scripts/red_check.py record --test <node id> --cmd "<pytest cmd>" --out <log>`
   then implement, then `record` again (GREEN) and `verify --log <log> --test <node id>`.
   A RED stated in words does not exist.
4. Never write a secret into a file, a commit or your report.
5. A revert is a commit titled `Revert …` (`git revert`), never a silent undo: the fix budget
   counts them. Before each new fix attempt run
   `python3 <skills>/implement-plan/scripts/fix_budget.py --base <task base> --scope <scope> --scope <log>`;
   exit 1 = stop and report its line, change nothing more.

### Report (≤ 20 lines)
- Commit SHA(s) and the files touched.
- Each new test: node id, the RED line from the log, then GREEN.
- `verify` exit code; the full test command's last line.
- Anything you found outside the scope: one line each (the orchestrator files them as beads).
```

The orchestrator never trusts the report alone: it re-runs `red_check.py verify` and the fix
budget itself before closing the task bead.
