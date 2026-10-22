# Bypass-test — the baseline, and the tests that must fail

## The baseline (`fails_before`), measured before the door was written

**Donor.** `~/.agents/skills/database-schema` (379 lines, no lockfile entry, local since
2026-05-18). Its core instruction: read the schema file, and "create
`_project_specs/schema-reference.md` for quick lookup … Claude: READ THIS before database work".
The 2026-08-17 skill census already classified it as schema *awareness*, not schema *design*, and kept its mechanism as a habit.

**Run (deterministic, 2026-10-17).** For each of three product repositories: last commit date of every
tracked `schema-reference*.md` against the last commit date of every migration directory.

| repo | reference last change | newest migration change | gap |
|---|---|---|---|
| product repo A (Supabase, 3 migration roots: 121 / 21 / 1 files) | 2026-10-07 | 2026-10-09 | 2 days |
| product repo B (SQL migrations, 65 + 1 files) | 2026-07-27 (a second copy: 2026-07-01) | 2026-08-11 | 15 days |
| product repo C (Supabase, 191 files) | 2026-08-24 | 2026-10-06 | 43 days |

**Verdict: HOLDS.** An agent following the donor literally reads a schema that is behind the
database in 3 of 3 repos, and in repo A it cannot tell which of three migration roots is deployed.

What the donor already did well and this door keeps: read before you write, use generated types,
regenerate them after a migration, the per-task verification block.

## Round 1 critic (BLOCK) and the redesign

The first `check` asked "do the table name and the column name appear in the same migration
file?". The fresh critic broke it on real repos: a column of another table in the same file passed
(`projects.email`, the column belongs to `clients`); a later file that merely mentioned a
dropped table hid the drop; `ALTER TABLE t DROP c` without `COLUMN`, a quoted schema-qualified
`DROP TABLE`, Alembic `op.drop_column`, untracked new migrations and same-day staleness all passed.
Patching co-occurrence regex by regex would be a half-closed invariant, so the check was replaced:
it now **replays every migration root in file order into a table -> columns state** and answers from
that state. Untracked (not ignored) migrations are read; staleness compares timestamps, using the
commit time of clean tracked files and the mtime of dirty or untracked ones.

## Round 2 critic (BLOCK) and the invariant

The replay itself failed open wherever it could not model DDL: an `ALTER TABLE … DROP` inside a
`DO $$ … $$` block, `op.execute("ALTER …")`, `batch_op.drop_column` (OPAQUE was checked after
FOUND), Alembic `downgrade()` and commented-out ops replayed as if they ran, keyword arguments read
in the wrong order, a column of `archive.users` approving `users.email`, quoted `"Email"` and
`"email address"` folded to `email`, and a `'--'` inside a string hiding the next statement.
Second round = the cap, so the reproducers were not patched one by one; the version-3 code holds
one invariant instead: **whatever the replay cannot model fails closed**. SQL goes through a
one-pass lexer (strings before comments, nested `/* */`, `$tag$` bodies but not `$1`); Alembic
is read with `ast`, `upgrade()` only, positional or keyword arguments, `batch_alter_table` bound to
its table, constant `op.execute` replayed as SQL and anything computed making the root BLIND;
tables are keyed by schema; a column added, dropped or renamed inside a dollar body (or a string
executed there) is OPAQUE for that column, a table dropped, renamed or moved there is OPAQUE whole,
and dynamic DDL (`format('alter table %I …')`) makes every table named in its literals OPAQUE.
Every round-2 fixture (31) was re-run: none prints FOUND for an absent column.

## Round 3 critic (BLOCK, run on real PostgreSQL 17 and Alembic) and the founder's call

Four plausible inputs still printed FOUND for a column PostgreSQL no longer had:
`ALTER SCHEMA … RENAME TO`, `DROP SCHEMA` inside a DO block, `SET search_path` before an
unqualified `ALTER TABLE`, an Alembic helper function called from `upgrade()`, and Alembic files
whose name order is not their `down_revision` order. Past the two-round cap the founder chose one
more fix round (2026-10-17). Each is modelled, not pattern-matched: schema renames move their
tables and schema DDL inside a body makes the schema's tables OPAQUE; `SET search_path` /
`RESET` drive unqualified resolution inside a file, and a path left non-public at the end of a
file or set through a top-level `set_config('search_path', …)` makes later unqualified DDL on a
name held by several schemas OPAQUE for every holder; module-level helpers called from
`upgrade()` are replayed inline, `conn.execute(...)` with constant SQL is replayed, any other
unresolved lower-case call makes the root BLIND; Alembic files are ordered by the
`revision`/`down_revision` graph, and a file without a readable revision id, a missing parent, a
cycle or SQL mixed with Alembic in one root makes it BLIND. All six round-3 fixtures now fail.

**Mutation proof of the selfcheck** (11 mutants, each must turn `--selfcheck` red): untracked
migrations ignored · dollar bodies ignored · `downgrade()` replayed · per-column uncertainty
ignored · OPAQUE checked after FOUND · AMBIGUOUS collapsed to FOUND · string lexer off ·
helpers ignored · file-name order instead of the revision graph · `SET search_path` ignored ·
an unparsable Alembic file ignored inside `replay_alembic`. 10 of 11 red; the eleventh is an
**equivalent mutant**: the revision-order step parses the same file first and already makes the
root BLIND, so that branch cannot be reached (kept as defence, not counted as proof).

## Round 4 critic (BLOCK) and the trust inversion

On real PostgreSQL 17 and Alembic again: `DROP TYPE … CASCADE` removed a column the replay still
held, and an Alembic `if` branch reaching `op.execute` or a helper was counted as always run; five
mutants survived (RESET search_path, `exec_driver_sql`, computed `execute`, an imported helper,
catalog-driven dynamic DDL). Four rounds, four new ways PostgreSQL removes a column indirectly:
evidence that a static replay can refute a column but never prove one. The founder did not answer
within 30 minutes; the recommended option was applied. **A static FOUND is now exit 3 (CONCERNS),
never PASS; exit 0 needs `--db`**, a read-only query of the live `information_schema.columns`
(`PGOPTIONS=-c default_transaction_read_only=on`); an unreachable database is exit 1. The round-4
inputs are modelled too (columns carry their type; `DROP TYPE/DOMAIN … CASCADE` drops the typed
columns, `DROP EXTENSION … CASCADE` the columns of non-builtin types, the same inside a body
makes them OPAQUE; an `if` reaching `execute`/`exec_driver_sql`/a DDL op/a helper makes the root
BLIND), and the five survivors have selfcheck witnesses.

**Live proof** (2026-10-17, temporary PostgreSQL 17.10 cluster): the type-cascade fixture applied
with psql ("drop cascades to column status of table orders"); `check orders.id --db` → FOUND +
LIVE-FOUND, exit 0; `check orders.status --db` → DROPPED + LIVE-MISSING, exit 1; a
`CREATE TABLE` under the same `PGOPTIONS` → "cannot execute CREATE TABLE in a read-only
transaction"; a wrong role or an unreachable host → exit 1. Cluster stopped afterwards.

**Mutation proof after the inversion**: 25 mutants, 23 killed. Two survive: the unparsable-Alembic
branch (equivalent, see round 3) and a mutant that turns a failed `--db` read into an empty row set
(equivalent: every item then reads LIVE-NO-TABLE and fails); its dangerous form — a failed `--db`
falling back to the static verdict — is killed ("an unreachable --db must FAIL").

## Round 5 gate review (BLOCK) and the `--db` boundary

The live path itself had two holes, reproduced on PostgreSQL 17.10 with `log_statement=all`:
(1) a table argument such as `cases\'); COMMIT; BEGIN READ WRITE; INSERT …; --` with
`standard_conforming_strings=off` escaped the doubled-quote literal and committed an INSERT, and a
URL `options=-c default_transaction_read_only=off` overrode the read-only default; (2) a catalog
name containing a tab and a newline forged an extra TSV row, so a column absent from the catalog
exited 0. Closed at the boundary, not by escaping better: every `[schema.]table.column` part must
be a plain identifier `[a-z_][a-z0-9_$]*` (anything else is exit 2, statically and with `--db`),
so no argument text reaches the SQL; the catalog query runs inside an explicit `begin transaction
read only` … `rollback` that no default option can switch off; the result is one JSON value parsed
with `json` and shape-checked (three strings per row), so a name with tabs or newlines cannot forge
a row. **Re-proof on a fresh cluster**: both injection payloads → exit 2, the guard table unchanged
(`1`); with the read-only-off URL option the server log shows only `begin transaction read only`,
the catalog `select`, `rollback`; real column → exit 0, absent column → exit 1. New mutants
(identifier validation off, explicit read-only transaction removed, PGOPTIONS guard off, TSV
parsing back, shape check off): 5 of 5 red.

## Round 6 gate review (BLOCK) and the connection argument

The `--db` value itself reached psql as a positional argument, so `--db=-cBEGIN READ WRITE; INSERT …;
COMMIT;` was read as a psql `-c` option: it committed a row and, with a crafted `-cselect '[[…]]'`,
forged the catalog answer (exit 0 for an absent column). A `select 1` replacement of the catalog
query also survived the selfcheck, because the stub only looked for words anywhere in the query.
Closed: psql now receives the address only as `--dbname=<value>`, one argument it never parses as
an option; `--db` must be a `postgresql://` / `postgres://` URL or a `key=value` connection string
(anything else, a leading dash included, is exit 2); the output must be exactly one line; the stub
refuses unless it gets `--dbname=`, the explicit read-only transaction and a query that starts with
the exact catalog SELECT and holds no `--` or `;`. **Re-proof on a fresh PostgreSQL 17.10 cluster
with `log_statement=all`**: both dash attacks → exit 2, the quoted-name payload → exit 2, guard
table unchanged (`1`); with a URL that turns the read-only default off the server log holds only
`begin transaction read only`, the catalog `select`, `rollback` (3 times each); real column → exit 0,
absent column → exit 1, `key=value` form → exit 0. **Mutation sweep: 24 of 24 killed**
(untracked, bodies, downgrade, uncertainty, string lexer, helpers, file order, search_path, RESET,
`exec_driver_sql`, unresolved helper, catalog-dynamic DDL, type cascade, conditional Alembic,
read-only option, read-only transaction, `--db` fallback, positional `--db`, `--db` shape check,
one-line output, row shape check, static FOUND as PASS, DRIFT as PASS, `select 1` query).

## Round 7 gate review (BLOCK) and Unicode look-alikes

`public.unicode_probe.K` (U+212A KELVIN SIGN) exited 0: Python's `str.lower()` turned it into an
ASCII `k` before the identifier check, so the tool asked PostgreSQL about a different column than
the one requested. Names are now validated before any case folding and must be ASCII
(`[A-Za-z_][A-Za-z0-9_$]*`); a look-alike is exit 2. The same review showed a query mutant that
appends `and false` to the catalog WHERE clause still passed the selfcheck, because the stub
checked only the query prefix: the stub now requires the exact catalog SELECT for the requested
table. Both mutants (`and false`, validation after lowercasing) are red.

## Oracle measurement (2026-10-17)

Every column documented by the three repos' hand-written schema references (21 tables, 201
columns) checked against the replayed state: **196 FOUND, 5 MISSING, 0 parser misses**. The 5
MISSING columns are declared by no migration in their repo (`git grep` over every migration finds
no `ADD COLUMN` for them): they were added to the database outside migrations. The verdict is
right, and it is the drift the Gotchas section tells the agent to confirm on the live database.
Version 3, same 201 columns: 196 FOUND, the same 5 MISSING, 0 OPAQUE. Round-2 critic's sample of
219 columns taken from real CREATE TABLE / ADD COLUMN statements: 211 FOUND, 8 DROPPED by later
migrations (correct), **0 false alarms**; round-3 critic's independent sample: 0/36. After the
round-3 changes the 219-column sample is unchanged (211 FOUND, 8 DROPPED). An intermediate version that made a whole table OPAQUE
whenever a DO block touched it flagged 45 of 219 — that is why opacity is per column.

## Tests that must fail (all in `scripts/schema_scan.py --selfcheck`, 83 branches)

Every static item the tables below list as `0` now exits `3`: a declared column is CONCERNS until
`--db` proves it. The `--db` branches use a stub `psql` (via `SCHEMA_SCAN_PSQL`) that exits 9 unless
it receives the read-only option: declared+live → 0, declared without `--db` → 3, live but
undeclared → 3 (DRIFT), declared but not live → 1, live in two schemas → 1, unreachable → 1, no
psql → 1, a forged row with tab/newline → 1, non-JSON or malformed catalog output → 1, SQL or a
quote/backslash in a name → 2, extra output lines → 1, a `--db` that looks like a psql option or
is neither a URL nor `key=value` → 2. The stub also exits 8 without the explicit read-only
transaction, 6 without `--dbname=`, 7 unless the query starts with the exact catalog SELECT. The round-4 and mutant witnesses (`SELF_WITNESSES`) all → 1.

The table lists the families; the exact items live in `SELF_SQL_EXPECT` / `SELF_PY_EXPECT`.

| input | must be | why it guards the door |
|---|---|---|
| repo with no migration, ORM or types | `locate` → 1 | ignorance is not a pass |
| same repo, `check users.email` | 1 | nothing replayed is not "found" |
| column in `CREATE TABLE public.users (…)` / after a rename | 0 | happy paths still pass |
| column never declared | 1 | the guessed column |
| column named only in a comment (`-- drop column ghost`) | 1 | comments are not DDL |
| `DROP COLUMN nick, DROP bio` (optional `COLUMN`, several actions) | 1, 1 | every drop form |
| renamed column, old name | 1 | stale code after a rename |
| table dropped (`drop table if exists "public"."legacy" cascade`), then mentioned again | 1 | a later mention does not resurrect it |
| column of another table in the same file (`projects.email`) | 1 | co-occurrence is not membership |
| `CREATE TABLE … AS SELECT` | 1 (OPAQUE) | unknown columns are not found columns |
| table only in an ORM model | 1 (NO-TABLE) | the model ahead of the database |
| `ADD COLUMN IF NOT EXISTS` then `CREATE TABLE IF NOT EXISTS` again | 0 | a no-op create keeps the columns |
| Alembic `op.drop_column` / `op.add_column` | 1 / 0 | Python migrations replayed too |
| column present only in `schema-reference.md` | 1 | the reference is never evidence |
| `DO $$ … drop column … $$`, `execute 'alter table … drop column …'`, dynamic `format('%I')` | 1 (OPAQUE) | unmodelled DDL fails closed |
| `enable row level security` inside a DO block | 0 | non-column DDL does not blind the table |
| `downgrade()` defined before `upgrade()` re-adding a dropped column | 1 | only upgrade runs |
| `op.drop_column(column_name=…, table_name=…)`, constant `op.execute`, `batch_op.drop_column` | 1 | every Alembic form |
| non-constant `op.execute(SQL)` | 1 (BLIND) | unreadable migration fails closed |
| same table name in two schemas, unqualified / qualified | 1 (AMBIGUOUS) / 0 | schema is part of the name |
| quoted `"Email"`, `"full address"` queried as `email` / `full` | 1 | quoting is not folded away |
| a default `'x, ghost text'` | ghost → 1 | strings are not DDL |
| `drop schema tmp cascade`, `alter table moved set schema archive` | 1 / 0 | schema-level moves |
| `alter schema hist0 rename to hist1` / `do $$ … drop schema s2 cascade $$` | 1, hist1 → 0 / 1 | schema DDL |
| `set search_path to sp; alter table spt drop column payload` | sp → 1, public → 0 | path-aware resolution |
| search_path left set to `lk` at the end of a file, unqualified drop in the next | both holders → 1 | leaked path fails closed |
| helper `remove_obsolete()` called by `upgrade()`, `conn.execute(text('ALTER …'))` | 1, untouched column → 0 | Alembic call graph |
| `f00_create.py` ← `a00_drop.py` (`down_revision`) | 1 | revision graph, not file names |
| Alembic file that does not parse | 1 (BLIND) | unreadable migration fails closed |
| reference one hour older than a migration / newer | `locate` → 3 / 0 | sub-day staleness |
| malformed item / no item / absent repo | 2 | usage error, never 0 |

## Known bypasses (declared, not closed)

- **Not invoking the door at all.** Nothing blocks a database edit made without it; the trigger is
  the description. Closing this needs a PreToolUse hook on migration/model paths — not built.
- **Dynamic DDL whose table names come from the catalog** (a loop over `pg_tables` with no table
  name in any literal) makes the whole root BLIND: safe, noisy, and rare (0 in the three repos).
- **Revision features beyond `down_revision`** (`depends_on`, branch labels) are not followed;
  the graph order may then differ from `alembic upgrade head` in a branched history.
- **Functions run later, not now**: a function body that would alter a table when called is
  treated like a DO block (OPAQUE for the columns it changes), even if nobody calls it.
- **Query names are folded to lower case**: a quoted mixed-case or spaced column cannot be asked for
  and reports MISSING (safe direction).
- **Views are not modelled**: NO-TABLE.
- **Several roots**: a column passes only if every root that knows the table holds it; which root is
  deployed is still a question for a human (`locate` prints the NOTE).
