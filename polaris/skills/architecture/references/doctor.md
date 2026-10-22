# `doctor` — what it measures, and what it refuses to repair

`python3 scripts/arch_doctor.py --root <repo> [--quick] [--json]`

It owns no verdict of its own. It resolves each checker the harness already ships, runs it, and
reports one row: `check · verdict · blocking · evidence · realignment`. **Only a RED is ever
marked blocking**: a row nobody could judge is not the row to lead with. Every number comes from a
checker that existed before this verb did — nothing here re-implements a measurement.

The table of checkers, with each one's contract, lives in `scripts/arch_doctor_sources.py`; the
running half is `arch_doctor.py`. The split exists so that a change to how the doctor
**reports** cannot change what it **measures**.

## What it measures

| check | the checker | quick | blocking | RED when |
|---|---|---|---|---|
| `backbone` | `check_context_backbone.py --check <root>` | yes | yes | exit 2 |
| `decisions` | `decisions_health.py --check <root>` | yes | yes | exit 1 |
| `scope-drift` | `polaris_drift_check.py --intents <declared>` | yes | no | its clean line absent |
| `symbol-drift` | `polaris_symbol_drift.py` | no | no | never — see below |
| `decision-drift` | `polaris_decision_drift.py` | no | no | its clean line absent |
| `dependency-drift` | `polaris_dependency_drift.py` | no | no | its clean line absent |
| `test-drift` | `polaris_test_drift.py` | no | no | its clean line absent |
| `install-hygiene` | `check_install_hygiene.py` | no | no | exit 1 |

**Each checker's own contract decides, and only the codes it declared may mean RED.** The four
drift scripts exit 0 whether or not they found drift, so their verdict comes from the exact line
they print when clean, anchored at the start of a line — `^decision-drift: clean\b` and its
siblings. A substring match is not good enough: it read a report about a file called `cleanup.py`
as a clean repository.

`--quick` is the cheap, repository-scoped measure: three checks, read-only, a **five second budget
shared across the whole run**, exit 0 whatever it finds. It is what the naked invocation runs, and
it reaches nothing outside the repository — `install-hygiene` reads the install roots under `$HOME`
and is a full-run check only. A check that would start past the budget, or that the budget cuts short, reports
`over quick budget` rather than blaming the checker for being slow. The full run exits **2** when `backbone` or `decisions` is RED.

Each checker is looked for in the host repository first, then in the package this skill shipped
in, then in the Polaris installation the repository declares (`$POLARIS_VAULT`, or
`git config polaris.vault`), then in this skill's own `scripts/` (where the backbone checker
ships, so its row always runs). `--which` puts the skill's own copy first. A checker found in
none of them is `UNKNOWN`, never invented.

## What it refuses

**It never writes inside the repository under test, and that does not depend on the checkers
behaving.** The ledger-reading checks are handed a **copy** of the repository's ledger inside a
scratch directory thrown away with the run, so a checker that appends cannot reach the tree. The
one checker that appends by design is pointed at the scratch directory too. Repairing drift as a
side effect of measuring it is how a false document becomes a signed one.

**It never reports a fabricated zero.** Seven things are `UNKNOWN`, never GREEN:

- the checker is not installed here — the harness is absent, not clean;
- the checker cannot answer a repository-wide question (`symbol-drift` asks about named files);
- the recording it reads does not exist — an empty ledger measures nothing;
- **its input is not wired** — `scope-drift` with no declared intent source would call every
  changed file unowned and read RED by construction, which measures nothing at all;
- **the checker itself failed** — a traceback, or any exit code it never promised, is the checker
  breaking, not a verdict about the repository. The evidence says `checker failed:` and the
  realignment is to fix the checker before reading the row. The traceback is read **before** the
  exit code, because a crash exits 1 and 1 is what two of these checkers declare as their RED;
  reading the code first let a crash borrow a verdict it never earned;
- **the doctor's own step failed** — the ledger copy is the doctor's work, so a recording it
  cannot read is `ledger unreadable`, one row, never a traceback out of the run;
- **there is nothing here to judge** — a repository with no `decisions/` register is not a
  repository with an unhealthy one.

**A repository that never adopted a thing has not failed it.** `LIVE_DOC_MISSING` and
`FRONTMATTER_MISSING` on `backbone`, and a missing `decisions/` register on `decisions`, are
demoted to `UNKNOWN`, do not block the run, and route to adoption
(`check_context_backbone.py --init .`) rather than to `doc` — writing a document into a repository
with no backbone to hold it is not the repair.

**A gone path is a finding, not a typo.** A `CITED_PATH_MISSING`, `COMPONENT_PATH_MISSING` or
`DECISION_CALL_SITE_MISSING` row carries the realignment: restore the path, or fix the citation —
`doc` to re-true the document, `land` to move the call sites. Nothing is resealed: freshness is
computed at read time, and there is no seal.

## What to do with the output

Nothing, on its own. Each row's last column is the verb the founder invokes next, and every check
has an answer for both `RED` and `UNKNOWN` in [menu.md](menu.md) — including the rows where the
honest answer is that no verb follows. A finding acted on inside the doctor run is a repair nobody
asked for.
