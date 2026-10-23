---
title: polaris-sweep — bypass tests
description: One case per defect, with fails_before and the output from BEFORE (the bypass succeeds) and AFTER (the bypass fails). The reviewer that auto-merge relies on cannot be the only part of the loop without red cases.
status: active
---

# Bypass-test di `polaris-sweep`

Rule: the case is written **before** the code, and it must **succeed** (SPEC-MADRE, Phase 2).

The BEFORE of the three cases is the same and was run on 2026-08-17 on unversioned polaris-sweep
(407 lines of prose):

```bash
python3 polaris-sweep/scripts/sweep_gate.py automerge ... 
# can't open file '.../scripts/sweep_gate.py': [Errno 2] No such file or directory → exit 2
```

**No script existed**: Phase 4.5 was prose, so any well-written verdict
authorized auto-merge. The field evidence is the REAL run-state
`_polaris/sweep/runs/acme-app/pr-59.md` (2026-05-01): it declares `auto_mergeable: true`
**without** `head_sha`, without `attestazione`, without `risk` in the frontmatter.

---

## B1 — approve verdict on code that never ran (tests that prove nothing)

`fails_before:` `polaris-sweep` unversioned (pre-1.0.0)

An excellent static review of a PR never run anywhere: the three lenses read,
none executes. BEFORE: the Auto-mergeable block depended only on the prose of Phase 4.5.

**AFTER** — run 2026-08-17 on v1.0.0 (from the selfcheck, branch B1):

```
NEGATO: attestazione 'non-attestata': questo codice non e' mai stato eseguito da nessuna parte — real test prima del merge
exit=1
```

`attestazione: non-deployabile` (doc-only) stays PASS: the attestation is not required where there
is no runtime to prove.

## B2 — the PR touches the pipeline and approves itself

`fails_before:` `polaris-sweep` unversioned (pre-1.0.0)

A PR that modifies `.github/workflows/`, the suite gates or the `.fix/contract.yml` contract
can alter exactly the checks that should stop it. BEFORE: no check on paths.

**AFTER** — run 2026-08-17 on v1.0.0 (selfcheck, branch B2):

```
NEGATO: la PR tocca la pipeline (.github/workflows/ci.yml): il gate non approva chi modifica il gate — merge umano
exit=1
```

## B3 — verdict issued on a SHA different from HEAD

`fails_before:` `polaris-sweep` unversioned (pre-1.0.0)

The sweep approves, then the PR receives more commits: the comment stays, and so does the verdict, and it holds for
code that no longer exists. BEFORE: the run-state did not even record the SHA (see `pr-59.md`).

**AFTER** — run 2026-08-17 on v1.0.0, against the real pre-v1 run-state:

```bash
python3 scripts/sweep_gate.py automerge --run _polaris/sweep/runs/acme-app/pr-59.md \
  --pr-head deadbeef123 --files files-59.txt
NEGATO: campo 'head_sha' assente o vuoto nel run-state: senza, il verdetto non e' legato a niente
NEGATO: campo 'attestazione' assente o vuoto nel run-state: senza, il verdetto non e' legato a niente
NEGATO: campo 'risk' assente o vuoto nel run-state: senza, il verdetto non e' legato a niente
exit=1
```

And with the field present but stale (selfcheck, branch B3):

```
NEGATO: verdetto emesso su aaa111 ma la PR e' a bbb222: STALE — la revisione ha letto un codice che non esiste piu'
exit=1
```

---

## B4 — PR outside the prod perimeter blocked by the risk:trivial requirement

`fails_before:` `polaris-sweep v1.0.0` — the INVERSE defect of the first three: over-blocking.
Repo owner decision 2026-08-17: *"PRs that do not touch pipeline or prod are ALWAYS auto-merged"*.
v1.0.0 required `risk:trivial` + attestation on ALL PRs — even a doc-only one stayed in
the human's queue, which is exactly the bottleneck the loop exists to remove.

Setup: run-state `verdict: approve · head_sha: aaa111 · attestazione: non-attestata ·
risk: medium` · diff = `docs/README.md, tests/test_x.py` · contract with
`deployabili: [src/*, app/*]`.

**BEFORE** — run 2026-08-17 on v1.0.0 (script from `git show`):

```
NEGATO: risk 'medium': solo risk:trivial si fonde da solo
NEGATO: attestazione 'non-attestata': questo codice non e' mai stato eseguito da nessuna parte — real test prima del merge
exit=1
```

**AFTER** — same command on v1.1.0 (with `--repo` declaring the perimeter): `exit=0`.

The counter-branches that stay DENIED (selfcheck 18/18): same diff but inside `deployabili` →
strict path · perimeter **not declared** → strict path (we do not guess what is prod) ·
pipeline in the diff → always DENIED, the perimeter does not save it.

---

## Selfcheck

```bash
python3 scripts/sweep_gate.py --selfcheck ; echo "exit=$?"
```

18 checks, all `ok`, `exit=0` — run 2026-08-17 (13 from v1.0.0 + 5 for the prod perimeter).
Ignorance branches included: run-state missing/empty → 2, file-list missing/empty → DENIED,
placeholder `.` → DENIED, perimeter not declared → strict path. Never PASS in the dark.
