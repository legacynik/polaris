---
title: implement — bypass tests
description: One case per way past the build's gates. Each says what it tries, what stopped it, and the output. A gate without its red bypass is a declaration, not a gate.
status: active
---

# Bypass tests of `implement-plan`

Run on bd 1.3.1, a throwaway `bd init --stealth` db, `POLARIS_TELEMETRY_OFF=1`. Each case below
carries its own commands and output; the PR that created the skill also carries the whole E2E run
(claim → task → phase gate, open finding, killed claimant).

## I1 — claim the molecule's next step with `--mol`

`fails_before:` the brief's wording ("claim from `bd ready --mol` with `--claim`")

```
$ bd ready --mol tst-mol-v6c --claim --json
{ "error": "--claim cannot be combined with --mol" }      → exit 1
$ bd ready --parent tst-mol-v6c --metadata-field step=task --claim --json
[('tst-mol-v6c.1', 'in_progress', 'w2', '2026-10-24T21:26:49Z')]   → claimed, 5-min lease
```

Steps say: read with `--mol`, claim one named task with `feature_gate.py claim --step` (reaper
first, then `bd update --claim`); the E2E's stand-in gate does the same.

## I2 — close a phase while a blocking finding is open

The finding is a bead with `blocks:<phase>`, so bd itself refuses the close, before any judge:

```
$ bd create "review: parser drops trailing field" --parent tst-mol-v6c \
    --deps discovered-from:tst-mol-bo8,blocks:tst-mol-bo8 --external-ref gh-12 \
    -l kind:finding,src:review,blocking --no-inherit-labels --silent
tst-mol-v6c.1
$ bd close tst-mol-bo8 -r gate
cannot close blocked issue: tst-mol-bo8 is blocked by [tst-mol-v6c.1] (use --force to override)
```

The two remaining ways past it, `--force` and `bd dep remove`, are banned in Not for and checked
by `feature_gate.py edges` (adoption tests §2.1).

## I3 — keep fixing while the loop reverts itself

`fails_before:` no breaker existed; a loop could revert forever.

```
$ fix_budget.py --base <base> --scope '*.py'          # two fixes, both reverted
STOP — score 30 (stop above 20): 2 reverts, 0 files outside the scope. … → exit=1
$ … plus an untracked billing.cfg, scope a.py
STOP — score 50 (stop above 20): 2 reverts, 1 files outside the scope: billing.cfg. … → exit=1
```

## I4 — run the breaker without a scope

Every file would be "in scope" if none were declared. Refused instead:

```
$ fix_budget.py --base <base>
fix_budget.py: error: the following arguments are required: --scope      → exit=2
```

## I5 — a claimant dies holding a step

Poured step, claimant heartbeating, `kill -9`. The step stays held until its lease expires, the
next claim's reaper reclaims it, and the dead claimant's next heartbeat fails:

```
21:16:57 loop-b claim while lease live:  issue already claimed by loop-a
21:22:03 after TTL, before the supervisor: status=in_progress assignee=loop-a
21:22:05 supervisor (bd reclaim --older-than 0s):  crs-mol-060 (was held by loop-a)
21:22:05 after reclaim: status=open assignee=None
21:22:08 zombie loop-a heartbeats: Error … issue not claimable: crs-mol-060 status open
21:22:10 loop-b claims it: status=in_progress assignee=loop-b
```

`feature_gate.py claim` reaps with `--older-than 0s`, so recovery waits only for the 5-min lease.
