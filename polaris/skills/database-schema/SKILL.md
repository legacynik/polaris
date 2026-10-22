---
name: database-schema
description: ◇ Read the real schema before any database work — locate migrations, ORM models and generated types, verify every table and column you will touch, and refuse a stale schema reference as truth. Use before writing or changing a query, a migration, a model, an RLS policy, a seed or a data fix, or before answering any question about what the database contains. Not for choosing a data model or a migration strategy, which is architecture.
version: 1.0.1
user-invocable: true
auto: true
status: active
job: "make the agent read the schema truth before it writes or claims anything about the database, with a script that fails when a column is missing, dropped or renamed"
when_not: "pure data-model or migration-strategy decisions (architecture) · database-free changes · a question already answered by a schema_scan check run in this session on the same tables"
lifecycle: "produces no file: the schema-in-scope block lives in the response, the check output in the PR description; nothing to drain"
invokes: [architecture]
invoked-by: [human]
io: "takes a repository and the tables or columns a task touches → returns the schema sources, a STALE flag on references older than the migrations, and FOUND/MISSING/DROPPED/RENAMED per column, which the implementation and its tests consume"
---

# database-schema

## Overview

Agents guess column names, trust a hand-written schema page, and only find out at runtime. This
door makes the schema the first read of any database task and turns "the column exists" into an
exit code. The truth is the migrations (and the live database when you can read it); a
`schema-reference.md` is a map that is usually behind.

Measured 2026-10-17: in three product repositories the schema reference was older than
the newest migration (by 2 days, 15 days and 43 days). Reading the reference alone, as the donor
skill told you to, was wrong in 3 of 3 repos. And 5 of 201 documented columns exist in no
migration at all: they were added to the database by hand, so the migrations are not complete either.

## Where this goes (host repository decides)

This skill produces: **none (the schema-in-scope block stays in the response)**; the `check` output
goes in the PR description. If the task also updates a schema reference, that file stays where the host
repository already keeps it; never create a second one.

## When to use / when not to use

- Before writing or editing a query, ORM call, migration, model, RLS policy, seed, backfill or data fix.
- Before answering "does table X have column Y", "what does this table store", "why is this field null".
- Before a test that reads or writes the database (so the test uses real column names).

**Not for:** deciding the data model, keys, normalization, an expand/contract migration order or
replication/consistency trade-offs. Those are commitments: go to `architecture`.

## Process

1. **Locate the truth.**
   ```bash
   python3 <skill-dir>/scripts/schema_scan.py locate --repo <repo>
   ```
   Exit `1` (nothing found): stop and ask where the schema lives; never invent one. Exit `3`
   (a reference is STALE): use it only to find table names; take columns from migrations. More
   than one migration directory: confirm which one the deployed database runs before trusting any.
2. **Read the tables in scope.** For each table: the newest migrations that name it (search the
   migration directory for the table name, read the last ones in file order), the ORM model, the
   generated types. If a read-only live connection is available (Supabase MCP, `psql` on a
   non-production database), `information_schema.columns` beats every file.
3. **Write the schema in scope** in your response before the code: table · column · type ·
   nullable · default · FK · enum values, each with the `file:line` it came from.
4. **Check before you hand over.** Every `table.column` the diff reads or writes:
   ```bash
   python3 <skill-dir>/scripts/schema_scan.py check --repo <repo> orders.status billing.invoices.trace_id \
       --db "$READONLY_DATABASE_URL"     # local or staging; the query runs in a read-only transaction
   ```
   **Reading migrations can refute a column, never prove it.** Without `--db` the best answer is
   exit `3` (CONCERNS: declared by the migrations, not proven) — enough to keep reading code, not
   enough for a migration, a data fix or a destructive change. Only `--db` can exit `0`: it reads
   `information_schema.columns` inside an explicit read-only transaction that is rolled back, and an
   unreachable database is exit `1`, never a fallback. Names must be plain identifiers
   (`[a-z_][a-z0-9_$]*`) and `--db` a `postgresql://` URL or a `key=value` connection string;
   anything else is exit `2` and never reaches the database. `LIVE-MISSING` beats any static FOUND; `DRIFT` (live, but no
   migration declares it) is exit `3` and means a migration is missing. Never point `--db` at a
   production primary with a writing role; a read replica, staging or `supabase start` is the target.
   Statically it replays every migration root in order (SQL through a real lexer, following
   `SET search_path`, schema renames and `DROP TYPE/EXTENSION … CASCADE`; Alembic `upgrade()`
   through `ast`, in `down_revision` order, local helpers inlined) into a (schema, table) ->
   columns state. Refusals:
   `MISSING` · `DROPPED` (column or table) · `RENAMED` · `NO-TABLE` (no migration creates it: a view,
   a function, a table made by hand, a model ahead of the database) · `AMBIGUOUS` (same table name in
   two schemas: pass `schema.table.column`) · `OPAQUE` (changed by DDL the replay cannot model: a
   DO block or function, CREATE TABLE AS / LIKE / INHERITS / PARTITION OF) · `BLIND` (an Alembic
   file or `op.execute` it cannot read). Non-zero: fix the code or the migration, never the check;
   for `NO-TABLE`/`OPAQUE`/`BLIND` read the definition by hand. Paste the output in the PR.
5. **If the schema changes:** a new migration (never edit an applied one) · regenerate the types ·
   update the schema reference in the same PR. If other services read the table, the change needs
   data backfill, or a column is dropped or renamed, stop and go to `architecture` first
   (expand/contract). RLS or Supabase auth: write the policy for every command the code runs (an UPDATE also needs
   a SELECT policy, see Gotchas) and test the affected row count, not only the absence of an error.

## Gotchas

- Stale reference → it is a map, not evidence: `check` never reads it, on purpose.
- `MISSING` on a column the reference documents → drift: the column was added outside migrations.
  Confirm on the live database (read-only) and add the missing migration; do not just use it.
- Several migration roots in one repo (one product repo has three) → ask which one is deployed.
- `OPAQUE` on a column changed inside a `DO $$ … $$` block → the change was conditional or dynamic;
  read that block (the output names the file) before relying on the column.
- Supabase: an UPDATE without a matching SELECT policy updates 0 rows with no error → test the row count.
- Enum values live in a CHECK constraint or a `create type` → read it; do not infer from code.
- A column found only in ORM/types and in no migration → the model is ahead of the database; ask.

## Common rationalizations

| Excuse | Reality |
|---|---|
| "I read the schema reference, that is the schema" | It was behind the migrations in 3 of 3 repos. |
| "The model file has the field" | Models drift ahead of migrations; the database runs migrations. |
| "`check` said FOUND, so it exists" | Static FOUND is exit 3: four critic rounds found columns PostgreSQL had removed. Use `--db`. |
| "Tests will catch a wrong column" | Only if they hit a real database; mocks repeat your guess. |
| "Small query, no need" | Wrong column names are the cheapest bug to prevent and the most common. |

## Red flags

- A query or answer about the database with no `file:line` source for its columns.
- "I assume the column is called …".
- A migration that edits an existing migration file.
- Renaming or dropping a column in one step while another service reads it.

## Verification

- [ ] `locate` ran this session; its exit code and any STALE line are in the response.
- [ ] The schema-in-scope block cites migration/model files, not only the reference doc.
- [ ] `check` exits 0 with `--db` for every column the diff uses (or 3 without a database, said
  so in the PR); output pasted in the PR.
- [ ] A schema change ships its migration, regenerated types and updated reference together.
