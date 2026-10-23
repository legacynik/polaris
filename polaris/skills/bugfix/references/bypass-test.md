---
title: bugfix — the per-stage gate bypass tests
description: One case per gate. Each declares fails_before and reports the output from BEFORE (the bypass succeeds) and AFTER (the bypass fails). A gate without its red bypass is a declaration, not a gate.
status: active
---

# Bypass tests of `bugfix` (per-stage gate)

B1–B4 were born with gate v0.1.0, which since 2026-08-17 lives inside `bugfix`. The commands hold unchanged with
`bugfix/scripts/fix_gate.py`.

Rule: the case is written **before** the code, and it must **succeed**. If it does not, the defect you
were about to cure does not exist — stop (SPEC-MADRE, Phase 2).

---

## B1 — record without domain or class

`fails_before:` gate `v0` (no script existed)

```bash
printf -- '---\nid: t\nrepo: r\nstato: aperto\n---\n' > /tmp/b1.md
python3 scripts/fix_gate.py check --stage ingresso --record /tmp/b1.md --repo . ; echo "exit=$?"
```

**BEFORE** — no gate exists, so nothing stops an incomplete record:

```
zsh: command not found: fix_gate.py     → exit=127, il record passa
```

**AFTER** — run 2026-08-11 on gate `v0.1.0`:

```
FAIL: campi mancanti o vuoti nel record: dominio, classe, cecita, sorgente
exit=1
```

---

## B2 — placeholder value that satisfies the presence check

`fails_before:` gate `v0.1.0-pre` (first variant, only checked that the key was there)

This is the bypass that already hit this suite: a plan validator accepted `deadline: .` and `serves: .`
without even printing a warning.
senza nemmeno stampare un warning.

```bash
printf -- '---\nid: t\nrepo: r\ndominio: .\nclasse: logica\ncecita: bassa\nsorgente: log\nstato: aperto\n---\n' > /tmp/b2.md
python3 scripts/fix_gate.py check --stage ingresso --record /tmp/b2.md --repo <repo-con-contratto> ; echo "exit=$?"
```

**BEFORE** — `dominio` is there, so the presence check passes: `exit=0`.

**AFTER** — covered by the selfcheck (line «valore-placeholder '.' -> FAIL»), verified 2026-08-11:

```
FAIL: campi mancanti o vuoti nel record: dominio
exit=1
```

Values treated as absent: `` (empty) · `.` · `-` · `--` · `?` · `tbd` · `todo` · `n/a` ·
`na` · `none` · `null` · `<>`.

---

## B3 — contract missing, check silently disabled

`fails_before:` gate `v0.1.0-pre`

The worst case, and the easiest to write by mistake: if the contract is missing, `dominii` is
`None`, and a check written as «if the list is there, verify» **skips without saying anything** — the
record passes. It is the canonical form of G2: the gate approves when it cannot decide.

```bash
mkdir -p /tmp/repo-senza-contratto
python3 scripts/fix_gate.py check --stage ingresso --record <record-valido> --repo /tmp/repo-senza-contratto ; echo "exit=$?"
```

**BEFORE** — `exit=0`: no vocabulary, no check, no message.

**AFTER** — covered by the selfcheck (line «contratto assente -> FAIL, mai PASS silenzioso»),
verified 2026-08-11:

```
FAIL: contratto senza 'dominii': il vocabolario di dominio non si improvvisa
      (atteso in <repo>/.fix/contract.yml)
exit=1
```

---

## B4 — unimplemented stage that passes

`fails_before:` gate `v0.1.0-pre`

Asking for a stage that does not exist yet must not produce a PASS: that would be a way to skip
the whole workflow by writing a wrong name.

```bash
python3 scripts/fix_gate.py check --stage riproduzione --record <record-valido> --repo <repo> ; echo "exit=$?"
```

**AFTER** — verified 2026-08-11:

```
stage sconosciuto: riproduzione (noti: ingresso)
exit=2
```

`2` is a usage error and **blocks**, like `1`. The later stages arrive with slices T2..T8: until
they exist, nobody passes through there by mistake.

---

## B5 — orphan test: committed but never collected by CI

`fails_before:` `bugfix v0.1.0` (no stage checked collection)

This is R5 of the field eval: the suite arm
on a product repo committed a new test that **no CI workflow references** — phase ④
closed on a test that only protects whoever runs it by hand. The legacy flow had collection already in the
`ci.yml` subset.

Setup:

```bash
cd "$(mktemp -d)" && mkdir -p .fix tests
printf 'def test_orfano():\n    assert True\n' > tests/test_orfano.py
printf 'def test_altro():\n    assert True\n'  > tests/test_altro.py
printf -- '---\nid: t1\nrepo: r\ndominio: auth\nclasse: logica\ncecita: bassa\nsorgente: issue\nstato: fixato\ntest: tests/test_orfano.py::test_orfano\n---\n' > rec.md
printf 'dominii: [auth]\nci.collect: python3 -m pytest --collect-only -q tests/test_altro.py\n' > .fix/contract.yml
```

Command:

```bash
python3 <bugfix>/scripts/fix_gate.py check --stage raccolto --record rec.md --repo . ; echo "exit=$?"
```

**BEFORE** — run 2026-08-17 on v0.1.0: the stage does not exist, the orphan test crosses the whole
workflow with nothing stopping it:

```
stage sconosciuto: raccolto (noti: causa, deposito, firma, ingresso, mutazione, prod, raggio, realtest, riproduzione, rosso, verde)
exit=2
```

(`2` blocks the explicit call, but the defect is the absence: none of the 11 stages checked
collection, and in the field the record passed — R5.)

**AFTER** — run 2026-08-17 on v1.0.0. The CI subset collects but does not contain the test:

```
FAIL: test ORFANO: tests/test_orfano.py::test_orfano non e' raccolto da 'ci.collect' — committato, ma la CI non lo eseguira' mai
exit=1
```

With `ci.collect` pointed at the subset that contains it: `exit=0`. Collection that fails (nonexistent
path, pytest exit 4): `FAIL: la raccolta CI fallisce (exit 4)` — never a silent PASS.

---

## B6 — thrashing: the fourth fix attempt instead of questioning the architecture

`fails_before:` `bugfix v1.0.0` — rule: 3+ failed fixes → STOP, re-examine the architecture.

Setup: `rosso_log` with **4 red runs** of the same test and then a green; contract with
`test.suite: /usr/bin/true`.
Command: `fix_gate.py check --stage verde --record rec.md --repo .`

**BEFORE** (v1.0.0, run 2026-08-17): `exit=0` — the suite passes and nobody counts the attempts:
fix no. 4 proceeds exactly like no. 1.

**AFTER** (v1.1.0, same command):
```
FAIL: CIRCUIT BREAKER: >=4 run rossi dello stesso test — 3+ fix falliti non chiedono il fix n.4,
chiedono di questionare l'architettura. Dichiara 'architettura_riesaminata: <cosa hai concluso>' per procedere
exit=1
```
With `architettura_riesaminata:` declared → PASS (explicit escape, never silent).
2 runs (1 red + 1 green) → no breaker.

## B7 — callers listed from memory, never produced by a command

`fails_before:` `bugfix v1.0.0` — a fix at the primary site with the callers never looked at is a
mute fix, shipped silently.

Command: `check --stage raggio` on a record with `chiamanti: [f_a, f_b]` + declared issue axes,
**without** `chiamanti_cmd`.

**BEFORE** (v1.0.0): `exit=0` — it was enough that the list existed.
**AFTER** (v1.1.0): `FAIL: 'chiamanti_cmd' assente: i chiamanti si PROVANO col comando che li ha
prodotti` · `exit=1`. `chiamanti: [nessuno]` stays PASS without a command (zero is declared).

## B8 — investigation started without consulting the bug archive

`fails_before:` `bugfix v1.0.0` — donor: acme-web `backend-debug` (active search for recurrence
by module+exception: «may be a RECURRING bug — check if the previous fix regressed»).

Command: `check --stage causa` on a record with a valid `causa_in: path:riga`, **without** the
`ricorrenza` field.

**BEFORE** (v1.0.0): `exit=0` — the pattern/prevention/detection triad was passive storage.
**AFTER** (v1.1.0): `FAIL: 'ricorrenza' assente: l'archivio bug si interroga PRIMA di indagare` ·
`exit=1`. Placeholder `.` → FAIL; `ricorrenza: 0 match in archivio` → the check passes.

---

## B9 — grep passed off as proof of the blast radius

`fails_before:` `bugfix v1.1.0` — found by the repo owner on the spot («the radius is seen with Serena
graph, always»): B7 demanded ONE command, but `chiamanti_cmd: grep -rn compute_price backend/`
passed — and grep finds text, not references.

**BEFORE** (v1.1.0, run 2026-08-17): `exit=0`.
**AFTER** (v1.1.1, same command): `FAIL: 'chiamanti_cmd' non e' un verbo del code-graph … il
raggio si vede col graph (Serena), MAI a grep` · `exit=1`. With
`chiamanti_cmd: find_referencing_symbols compute_price` → `exit=0`. Accepted verbs:
find_referencing_symbols/find_symbol/find_implementations/find_declaration/trace_path/
references/call_hierarchy.

---

## B10 — fail-open of `verde`: `cd x && suite` ran `/usr/bin/cd`, exit 0, zero tests

`fails_before:` `bugfix v1.1.1` — found by the **field validator** (eval on a product repo,
2026-08-17): the real contract said `cd backend && PYTHONPATH=... pytest`; `shlex.split`
without a shell turned it into argv `["cd","backend","&&",...]` → on macOS `/usr/bin/cd` exists,
ignores the arguments and **exits 0**: the suite NEVER ran and `verde` passed. The worst
possible failure for a gate that declares itself fail-closed.

Setup: contract with `test.suite: cd <dir> && /usr/bin/false` (a command that MUST fail).
Command: `fix_gate.py check --stage verde --record rec.md --repo .`

**BEFORE** (v1.1.1, run 2026-08-17): `exit=0` — fail-open.
**AFTER** (v1.1.2, same command): `FAIL: la suite non passa (exit 1)` · `exit=1`.

Fix: the CONTRACT's commands run with the shell (`_sh`, trust = the repo's Makefile) on all
the stages that execute (`riproduzione`, `verde`, `raccolto`, `prod`) + a guard on **127**: a
command not found is never a red nor a reproduction — it is an error, said loudly. Same
fix in `red_check.py` of tdd-dev (which recorded a bogus GREEN on the same pattern), plus
defect C: `record` on an unresolvable test file is now a usage error IMMEDIATELY, not a silent
`file_sha: assente` that only surfaces at verify.

---

## Selfcheck — proof that the ignorance branches are covered

```bash
python3 scripts/fix_gate.py --selfcheck ; echo "exit=$?"
```

**76 checks**, all `ok`, `exit=0` — rerun 2026-08-17 after B6-B8 (11 new branches:
breaker/thrashing, proven callers, recurrence). The ignorance branches — record missing, record
empty, contract missing, nonexistent collection command, placeholder — never exit 0. A
selfcheck that only proves the happy path is a promise, not a proof.
