---
title: tdd-dev — bypass tests
description: One case per defect. Each declares fails_before and records the output BEFORE (the bypass succeeds) and AFTER (the bypass fails). A gate without its red bypass is a claim, not a gate.
status: active
---

# Bypass tests for `tdd-dev`

Rule: the case is written **before** the code, and it must **succeed** against the old version.
If it does not, the defect you were about to cure does not exist — stop. Output blocks are quoted
exactly as the scripts print them.

---

## B1 — the `record` CLI was unusable: argparse collision on `dest="cmd"`

`fails_before:` `v0.1.0` — confirmed twice in independent field-eval runs: both suite arms worked
around it by importing the module, and an unattended loop would have stopped there.

The defect: `add_subparsers(dest="cmd")` and the `--cmd` option of the `record` subparser wrote
to the **same** attribute `a.cmd`. The value of `--cmd` overwrote the subcommand name, `main()` no
longer recognised `record` and printed the help. The selfcheck was green because it called
`cmd_record()` with a hand-built `Namespace`, bypassing `main()` — the broken branch was never run.

Setup:

```bash
cd "$(mktemp -d)" && printf 'def test_x():\n    assert False\n' > t.py
```

Command:

```bash
python3 <suite>/tdd-dev/scripts/red_check.py record \
  --test t.py::test_x --cmd "/usr/bin/false" --out r.jsonl; echo "EXIT=$?"; ls r.jsonl
```

**Expected BEFORE** — the bypass SUCCEEDS: no run recorded, the skill is unusable from the CLI.

```
usage: red_check.py [-h] [--selfcheck] {record,verify} ...
...
EXIT=2
(no log written)
```

Run 2026-08-17 on v0.1.0: output identical to the above (`print_help`, `EXIT=2`, no `r.jsonl`).

**Expected AFTER** — the same command records the run:

```
ROSSO exit=1 -> r.jsonl
EXIT=0
r.jsonl
```

**AFTER** — run 2026-08-17 on v1.0.0: identical to the expected output.

Permanent detection: the selfcheck now also drives the CLI path (`main()` through a subprocess),
not only the imported functions, so the class "selfcheck that bypasses the entry point" cannot
hide there again. Mutation run 2026-08-17: `dest="cmd"` restored → selfcheck exits **1** (the B1
branch fires) · fix restored → exits **0**.

---

## B2 — targeted GREEN can claim handoff without durable regression evidence

`fails_before:` `tdd-dev v2.0.0` pre-merge. The blind grader found a RED/GREEN JSONL and an agent
claim that `pytest` had passed, but no durable proof connecting that suite run to the cycle. The
new core contract therefore remained unproved.

The test was added first to `red_check.py --selfcheck`:

```text
FAIL handoff senza suite registrata -> FAIL
exit=1
```

After the minimum fix, `suite` appends the authoritative command and exit code to the same JSONL;
final `verify --suite-cmd` rejects a missing, failing, mismatched, or pre-GREEN entry.

```text
ok   handoff senza suite registrata -> FAIL
ok   suite registrata ma rossa -> FAIL
ok   suite verde prima del GREEN mirato -> FAIL
ok   suite diversa da quella dichiarata -> FAIL
ok   rosso, verde e suite successiva registrati -> PASS handoff
ok   CLI 'suite' registra l'evidenza autoritativa
```

Detection permanente: `python3 scripts/red_check.py --selfcheck` exercises both CLI paths and the
complete RED→GREEN→suite receipt.
