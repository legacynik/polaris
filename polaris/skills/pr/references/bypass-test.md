---
title: pr — bypass-test (must fail if a body that cannot be judged gets through)
description: Six ways a PR body slips past the owner, each must make controlla_pr.py exit non-zero; an unreachable tracker, or a body with no PR to read the files from, must exit 2, never 0.
status: active
---

# Bypass-test

```bash
#!/usr/bin/env bash
set -u
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/controlla_pr.py"
T="$(mktemp -d)"
ok=0
must_fail() { python3 "$S" --body "$1" --no-visuale --repo "$2" >/dev/null 2>&1 && { echo "BYPASS: $3"; ok=1; } || true; }
: > "$T/empty.md"
printf '## Summary\nAll good.\n' > "$T/no-verdict.md"
printf '## In breve\n**Decisione richiesta:** merge sì\n\nChiude #1\n' > "$T/fake-close.md"
printf '## In breve\n**Decisione richiesta:** merge sì\n\nCloses #1, #2\n' > "$T/two-in-one.md"
printf '## In breve\n**Decisione richiesta:** merge sì\n\nCloses #1\n' > "$T/unreachable.md"
must_fail "$T/empty.md" none/none "empty body"
must_fail "$T/no-verdict.md" none/none "no verdict, no issue"
must_fail "$T/fake-close.md" none/none "Italian close word GitHub ignores"
must_fail "$T/two-in-one.md" none/none "two issues after one keyword"
python3 "$S" --body "$T/unreachable.md" --no-visuale --repo none/none >/dev/null 2>&1
[ $? -eq 2 ] || { echo "BYPASS: unreachable tracker did not exit 2"; ok=1; }
printf '## In breve\n**Decisione richiesta:** merge sì\n\nNessuna issue.\n' > "$T/no-pr.md"
python3 "$S" --body "$T/no-pr.md" --repo none/none >/dev/null 2>&1
[ $? -eq 2 ] || { echo "BYPASS: no --pr and no --visuale was judged from the working directory"; ok=1; }
python3 "$S" --selfcheck >/dev/null || { echo "BYPASS: selfcheck red"; ok=1; }
rm -rf "$T"
exit $ok
```

Expected: exit 0 and no `BYPASS:` line. Any line means the gate approves what it cannot judge.
