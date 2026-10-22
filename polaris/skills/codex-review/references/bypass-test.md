---
title: codex-review — bypass tests
description: The two ways this skill's own text can make a run fail, as executable checks. Both exit 0 on the current SKILL.md; each fails if a runnable example regresses.
status: active
---

# Bypass cases

Run from the skill directory. Each command exits 0 when the skill is sound and 1 when the case
it guards has come back.

## B1 — a model id that returns 400 recommended as runnable

`fails_before:` codex-review 0.9.0, whose bundled guide carried `-m gpt-5.2-codex` in four
runnable examples (CLI, CI action, config file, flag table) while its own warning said every
`-codex` id fails on a ChatGPT login. Followed verbatim, the guide failed.

```bash
! grep -nE -- '-m [a-z0-9.-]*-codex|model[ =:"]+[a-z0-9.-]*-codex' SKILL.md references/codex-flags.md
```

## B2 — an invocation without stdin closed or a timeout

`fails_before:` the first Codex lens of the PR sweep: no `< /dev/null`, no `timeout`, an hour
blocked on stdin with a zero-byte output. Every `codex exec` block in this skill must carry both.

```bash
python3 - <<'PY'
import re, sys
text = open("SKILL.md").read()
blocks = [b for b in re.findall(r"```bash\n(.*?)```", text, re.S) if "codex exec" in b]
bad = [b for b in blocks if "< /dev/null" not in b or "timeout " not in b]
print(f"{len(blocks)} codex exec block(s), {len(bad)} without stdin closed and a timeout")
sys.exit(1 if bad or not blocks else 0)
PY
```
