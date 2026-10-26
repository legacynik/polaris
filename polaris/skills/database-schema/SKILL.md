---
name: database-schema
description: ◇ Polaris — Read the real schema before any database work — locate migrations, ORM models and generated types, verify every table and column you will touch, and refuse a stale schema reference as truth. Use before writing or changing a query, a migration, a model, an RLS policy, a seed or a data fix, or before answering any question about what the database contains. Not for choosing a data model or a migration strategy, which is architecture. Requires python3 and git; psql for live checks.
version: 1.1.2
user-invocable: true
auto: true
status: active
job: "make the agent read the schema truth before it writes or claims anything about the database, with a script that fails when a column is missing, dropped or renamed"
when_not: "pure data-model or migration-strategy decisions (architecture) · database-free changes · a question already answered by a schema_scan check run in this session on the same tables"
lifecycle: "produces no file: the schema-in-scope block lives in the response, the check output in the PR description; nothing to drain"
invokes: [architecture]
invoked-by: [human, grill]
io: "takes a repository and the tables or columns a task touches → returns the schema sources, a STALE flag on references older than the migrations, and FOUND/MISSING/DROPPED/RENAMED per column, which the implementation and its tests consume"
---

# database-schema

## What it does

Makes the schema the first read of any database task and turns "the column exists" into an exit
code. The truth is the migrations, and the live database when you can read it; a
`schema-reference.md` is a map that is usually behind (it was behind the migrations in 3 of 3
product repos, 2026-10-17).

## When

- Before writing or editing a query, ORM call, migration, model, RLS policy, seed, backfill or data fix.
- Before answering "does table X have column Y", "what does this table store", "why is this field null".
- Before a test that reads or writes the database, so it uses real column names.

## Steps

1. **Locate the truth**: `python3 <skill-dir>/scripts/schema_scan.py locate --repo <repo>`. Exit 1
   (nothing found) → ask where the schema lives; never invent one. Exit 3 (a reference is STALE) →
   use it only for table names. Several migration roots → confirm which one the deployed database runs.
2. **Read the tables in scope**: the newest migrations naming each table, the ORM model, the
   generated types. A read-only live connection (non-production) beats every file:
   `information_schema.columns`.
3. **Write the schema in scope** before the code: table · column · type · nullable · default · FK ·
   enum values, each with the `file:line` it came from.
4. **Check before you hand over** every `table.column` the diff reads or writes:
   `python3 <skill-dir>/scripts/schema_scan.py check --repo <repo> <table.column>... --db "$READONLY_DATABASE_URL"`.
   Migrations can refute a column, never prove it: without `--db` the best answer is exit 3
   (declared, not proven) — enough to read code, not for a migration, data fix or destructive
   change. Only `--db` can exit 0. Never point it at a production primary with a writing role.
   Non-zero → fix the code or the migration, never the check. Every refusal:
   [process.md](references/process.md).
5. **A schema change**: a new migration (never edit an applied one), regenerated types, the schema
   reference updated, all in one PR. Another service reads the table, a backfill is needed, or a
   column is dropped or renamed → stop and go to `architecture` (expand/contract). RLS: a policy for
   every command the code runs, and test the affected row count.

## Output

No file. In the response: the `locate` exit code and any STALE line, then the schema-in-scope
block with `file:line` sources. In the PR description: the `check` output — exit 0 with `--db`,
or exit 3 without a database, said so.
**Next:** back to the caller; a schema change → `architecture`.

## Where this goes

This skill produces: **none (the schema-in-scope block stays in the response)**; a schema reference stays where the repo keeps it.

## Not for

- Choosing the data model, keys, normalization, an expand/contract order or consistency
  trade-offs (`architecture`).
- Changes that touch no database; a question a `check` already answered this session on the same tables.
