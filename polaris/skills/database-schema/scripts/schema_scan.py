#!/usr/bin/env python3
"""schema_scan.py — find a repository's schema truth before any database work.

    schema_scan.py locate --repo <path>
    schema_scan.py check  --repo <path> <[schema.]table.column> [...]
    schema_scan.py --selfcheck

`locate` lists every schema source: migration roots (the truth), ORM model and schema files,
generated types, and hand-written schema references (a map, often stale).

`check` replays each migration root in file-name order into a (schema, table) -> columns state.
SQL goes through a one-pass lexer (strings, quoted identifiers, nested comments, dollar bodies);
CREATE/ALTER/DROP TABLE and ADD/DROP/RENAME [COLUMN] are applied. Alembic files are read with
`ast`: only `upgrade()`, positional or keyword arguments, `batch_alter_table`, and constant
`op.execute()` SQL replayed as SQL.

Invariant: whatever the replay cannot model fails closed. A table named by DDL inside a dollar
body (DO blocks, functions) is OPAQUE; a table created by AS / LIKE / PARTITION OF is OPAQUE; a
root with non-constant `op.execute()` or an unparsable Alembic file is BLIND; an unqualified table
name present in more than one schema is AMBIGUOUS. None of them ever prints FOUND.

Trust model: reading migrations can refute a column, never prove it (four critic rounds kept
finding PostgreSQL behaviour that removes columns indirectly). So a static FOUND is CONCERNS,
and only `--db <url>` — a read-only query of the live `information_schema.columns` — can PASS.

Exit codes (suite convention): 0 PASS · 1 FAIL · 2 usage error · 3 CONCERNS.
  locate: 1 when no migration and no ORM/types source exists; 3 when a schema reference is
          older than the newest migration (read the migrations, not the reference).
  check:  1 when any item is refuted by the migrations, or by the live database with --db, or
          when --db cannot be queried; 3 when every item is declared by the migrations but not
          proven live (no --db), or live but not declared by any migration (DRIFT); 0 only when
          --db confirms every item and the migrations declare it.

Declared limits: query names are folded to lower case, so a quoted mixed-case or spaced column
is reported MISSING; views are not modelled statically (NO-TABLE), but --db sees them.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SKIP_DIRS = {"node_modules", ".venv", "venv", ".git", "dist", "build", ".next", "__pycache__", ".worktrees"}
MIGRATION_FILE = re.compile(r"(^|/)(migrations|versions)/[^/]+\.(sql|py)$")
REFERENCE_FILE = re.compile(r"schema-reference[^/]*\.md$", re.IGNORECASE)
TYPES_FILE = re.compile(r"(database[._-]types\.ts|db[._-]types\.ts|supabase[._-]types\.ts|(^|/)types/supabase\.ts)$")
ORM_FILE = re.compile(
    r"(\.prisma$|(^|/)drizzle/.*\.ts$|(^|/)schema\.(ts|py|sql)$|(^|/)models\.py$|(^|/)models/[^/]+\.py$|(^|/)entities/[^/]+\.ts$)"
)

IDENT = r'(?:"(?:[^"]|"")+"|[A-Za-z_][A-Za-z0-9_$]*)'
QNAME = rf"{IDENT}(?:\s*\.\s*{IDENT})*"
NOT_COLUMN = {"constraint", "primary", "unique", "foreign", "check", "exclude", "like"}
Key = tuple[str, str]
IDENT_ARG = re.compile(r"[a-z_][a-z0-9_$]*\Z")
IDENT_RAW = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")


def _ident(raw: str) -> str:
    raw = raw.strip()
    return raw[1:-1].replace('""', '"') if raw.startswith('"') else raw.lower()


def _qname(raw: str) -> tuple[str | None, str]:
    parts = [_ident(p) for p in re.findall(IDENT, raw)]
    return (parts[-2] if len(parts) > 1 else None), parts[-1]


@dataclass
class Table:
    origin: str
    columns: dict[str, str] = field(default_factory=dict)
    opaque: str = ""
    uncertain: dict[str, str] = field(default_factory=dict)
    types: dict[str, str] = field(default_factory=dict)


@dataclass
class Root:
    tables: dict[Key, Table] = field(default_factory=dict)
    gone: dict[Key, str] = field(default_factory=dict)
    col_gone: dict[tuple[Key, str], str] = field(default_factory=dict)
    blind: list[str] = field(default_factory=list)
    path: list[str] = field(default_factory=lambda: ["public"])
    path_leak: str = ""

    def resolve(self, schema: str | None, name: str) -> Key:
        if schema:
            return (schema, name)
        holders = [k for k in self.tables if k[1] == name]
        if self.path_leak and len(holders) > 1:
            for k in holders:
                self.make_opaque(k, f"changed by an unqualified statement under an unknown search_path ({self.path_leak})")
            return ("?", name)
        for s in self.path:
            if (s, name) in self.tables:
                return (s, name)
        return holders[0] if len(holders) == 1 else (self.path[0], name)

    def home(self, schema: str | None) -> str:
        return schema or self.path[0]

    def create(self, key: Key, where: str) -> Table:
        self.tables[key] = Table(origin=where)
        self.gone.pop(key, None)
        for k in [k for k in self.col_gone if k[0] == key]:
            self.col_gone.pop(k)
        return self.tables[key]

    def drop_table(self, key: Key, where: str) -> None:
        self.tables.pop(key, None)
        self.gone[key] = f"table dropped in {where}"

    def rename_table(self, key: Key, new: str, where: str) -> None:
        if key in self.tables:
            nk = (key[0], new)
            self.tables[nk] = self.tables.pop(key)
            self.gone[key] = f"table renamed to {new} in {where}"
            self.gone.pop(nk, None)

    def add_col(self, key: Key, col: str, where: str, typ: str = "") -> None:
        if key in self.tables:
            self.tables[key].columns[col] = where
            self.tables[key].types[col] = typ
            self.tables[key].uncertain.pop(col, None)
            self.col_gone.pop((key, col), None)

    def drop_col(self, key: Key, col: str, where: str) -> None:
        if key in self.tables:
            self.tables[key].columns.pop(col, None)
            self.tables[key].uncertain.pop(col, None)
            self.col_gone[(key, col)] = f"column dropped in {where}"

    def rename_col(self, key: Key, old: str, new: str, where: str) -> None:
        if key in self.tables:
            self.tables[key].columns.pop(old, None)
            self.tables[key].columns[new] = where
            self.col_gone[(key, old)] = f"renamed to {new} in {where}"
            self.col_gone.pop((key, new), None)

    def make_opaque(self, key: Key, why: str) -> None:
        if key in self.tables:
            self.tables[key].opaque = why


def lex_sql(text: str) -> list[tuple[str, list[str]]]:
    """Split SQL into (statement with strings blanked and comments removed, dollar bodies)."""
    out: list[tuple[str, list[str]]] = []
    cur: list[str] = []
    bodies: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "'":
            escaped = i > 0 and text[i - 1] in "eE" and (i < 2 or not (text[i - 2].isalnum() or text[i - 2] == "_"))
            j = i + 1
            while j < n:
                if escaped and text[j] == "\\":
                    j += 2; continue
                if text[j] == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        j += 2; continue
                    break
                j += 1
            cur.append("''"); i = j + 1; continue
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == '"':
                    if j + 1 < n and text[j + 1] == '"':
                        j += 2; continue
                    break
                j += 1
            cur.append(text[i:j + 1]); i = j + 1; continue
        if text.startswith("--", i):
            j = text.find("\n", i)
            i = n if j < 0 else j; cur.append(" "); continue
        if text.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("/*", j):
                    depth += 1; j += 2
                elif text.startswith("*/", j):
                    depth -= 1; j += 2
                else:
                    j += 1
            cur.append(" "); i = j; continue
        if ch == "$":
            m = re.match(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$", text[i:])
            prev_ident = i > 0 and (text[i - 1].isalnum() or text[i - 1] == "_")
            if m and not prev_ident:
                tag = m.group(0)
                end = text.find(tag, i + len(tag))
                end = n if end < 0 else end
                bodies.append(text[i + len(tag):end])
                cur.append(" "); i = end + len(tag); continue
        if ch == ";":
            out.append(("".join(cur), bodies)); cur, bodies = [], []
            i += 1; continue
        cur.append(ch); i += 1
    out.append(("".join(cur), bodies))
    return out


def _split_top(text: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _paren_body(text: str, open_at: int) -> str:
    depth = 0
    for i in range(open_at, len(text)):
        depth += (text[i] == "(") - (text[i] == ")")
        if depth == 0 and text[i] == ")":
            return text[open_at + 1:i]
    return text[open_at + 1:]


BODY_SCHEMA = re.compile(r"\b(drop|alter)\s+schema\s+(?:if\s+exists\s+)?(.+)", re.I | re.S)
BODY_DROP = re.compile(rf"\bdrop\s+table\s+(?:if\s+exists\s+)?(.+)", re.I | re.S)
BODY_ALTER = re.compile(rf"\balter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?({QNAME})\s*\*?\s+(.*)", re.I | re.S)
BODY_DYNAMIC = re.compile(r"\b(?:alter|drop)\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?(?:[\w.\"]*%[IsL]|'\s*\|\|)", re.I)


BUILTIN_TYPES = {"int", "int2", "int4", "int8", "integer", "bigint", "smallint", "serial", "bigserial",
                 "smallserial", "text", "varchar", "character", "char", "boolean", "bool", "uuid", "jsonb",
                 "json", "timestamptz", "timestamp", "date", "time", "timetz", "numeric", "decimal", "real",
                 "double", "float", "float4", "float8", "bytea", "interval", "inet", "cidr", "macaddr",
                 "money", "xml", "oid", "tsvector", "tsquery", "bit", "varbit", "point", "line", "box",
                 "circle", "polygon", "path", "lseg", "int4range", "int8range", "numrange", "tsrange",
                 "tstzrange", "daterange", "name", "regclass"}
DROP_TYPE = re.compile(r"drop\s+(type|domain|extension)\s+(if\s+exists\s+)?(.+)", re.I | re.S)


def _type_of(rest: str) -> str:
    m = re.match(rf"\s*({QNAME})", rest)
    return _qname(m.group(1))[1].rstrip("[]") if m else ""


def _typed_columns(root: Root, kind: str, names_raw: str) -> list[tuple[Key, str]]:
    names = {_qname(r)[1] for r in _split_top(re.sub(r"\b(cascade|restrict)\b", "", names_raw, flags=re.I))}
    hits = []
    for key, tab in root.tables.items():
        for col, typ in tab.types.items():
            if col not in tab.columns:
                continue
            if kind.lower() == "extension":
                if typ and typ not in BUILTIN_TYPES:
                    hits.append((key, col))
            elif typ in names:
                hits.append((key, col))
    return hits


def _body_statement(root: Root, s: str, where: str) -> None:
    why = f"changed inside a dollar-quoted body in {where}"
    m = DROP_TYPE.match(s)
    if m:
        for key, col in _typed_columns(root, m.group(1), m.group(3)):
            root.tables[key].uncertain[col] = f"its type may be dropped inside a dollar-quoted body in {where}"
        return
    m = BODY_SCHEMA.match(s)
    if m:
        raws = _split_top(re.sub(r"\b(cascade|restrict)\b", "", m.group(2), flags=re.I))
        first = re.match(IDENT, m.group(2).strip())
        names = {_qname(r)[1] for r in raws} if m.group(1).lower() == "drop" else ({_ident(first.group(0))} if first else set())
        for key in [k for k in root.tables if k[0] in names]:
            root.make_opaque(key, f"its schema was dropped or altered inside a dollar-quoted body in {where}")
        return
    m = BODY_DROP.match(s)
    if m:
        for raw in _split_top(re.sub(r"\b(cascade|restrict)\b", "", m.group(1), flags=re.I)):
            root.make_opaque(root.resolve(*_qname(raw)), f"table possibly dropped inside a dollar-quoted body in {where}")
        return
    m = BODY_ALTER.match(s)
    if not m:
        return
    key = root.resolve(*_qname(m.group(1)))
    tab = root.tables.get(key)
    if tab is None:
        return
    for action in _split_top(m.group(2)):
        if re.match(r"(rename\s+to|set\s+schema)\b", action, re.I):
            tab.opaque = f"renamed or moved inside a dollar-quoted body in {where}"
            return
        a = re.match(rf"rename\s+(?:column\s+)?({IDENT})\s+to\s+({IDENT})", action, re.I)
        if a and a.group(1).lower() != "constraint":
            tab.uncertain[_ident(a.group(1))] = why
            tab.uncertain[_ident(a.group(2))] = why
            continue
        a = re.match(rf"(?:add|drop)\s+(?:column\s+)?(?:if\s+(?:not\s+)?exists\s+)?({IDENT})", action, re.I)
        if a and (a.group(1).startswith('"') or a.group(1).lower() not in NOT_COLUMN):
            tab.uncertain[_ident(a.group(1))] = why


def _opaque_from_body(root: Root, body: str, where: str) -> None:
    sources = [body] + [lit.replace("''", "'") for lit in re.findall(r"'((?:[^']|'')*)'", body)]
    for src in sources:
        for stmt, nested in lex_sql(src):
            for s in re.split(r"\b(?=(?:alter|drop)\s+(?:table|schema|type|domain|extension)\b)", stmt, flags=re.I):
                _body_statement(root, s.strip(), where)
            for inner in nested:
                _opaque_from_body(root, inner, where)
    if BODY_DYNAMIC.search(body):
        literals = {w.lower() for w in re.findall(r"'([A-Za-z_][A-Za-z0-9_]*)'", body)}
        for key in list(root.tables):
            if key[1] in literals:
                root.make_opaque(key, f"named by dynamic DDL inside a dollar-quoted body in {where}")
        if not literals:
            root.blind.append(f"{where}: dynamic DDL with table names computed at run time")


def replay_sql(root: Root, text: str, where: str) -> None:
    outside_bodies = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$.*?\$\1\$", " ", text, flags=re.S)
    if re.search(r"set_config\s*\(\s*'search_path'", outside_bodies, re.I):
        root.path_leak = f"set_config('search_path') in {where}"
    for stmt, bodies in lex_sql(text):
        _apply_statement(root, stmt.strip(), where)
        for body in bodies:
            _opaque_from_body(root, body, where)


def _apply_statement(root: Root, s: str, where: str) -> None:
    m = re.match(rf"create\s+(?:(?:global|local)\s+)?(?:temp(?:orary)?\s+|unlogged\s+)?table\s+(if\s+not\s+exists\s+)?({QNAME})\s*", s, re.I)
    if m:
        schema, name = _qname(m.group(2))
        key = (root.home(schema), name)
        if m.group(1) and key in root.tables:
            return
        t = root.create(key, where)
        rest = s[m.end():]
        if not rest.startswith("("):
            t.opaque = f"created without a column list in {where}"
            return
        for item in _split_top(_paren_body(rest, 0)):
            first = re.match(IDENT, item)
            if not first:
                continue
            word = first.group(0).lower()
            if not first.group(0).startswith('"') and word in NOT_COLUMN:
                if word == "like":
                    t.opaque = f"created with LIKE in {where}"
                continue
            t.columns[_ident(first.group(0))] = where
            t.types[_ident(first.group(0))] = _type_of(item[first.end():])
        if re.match(r"\s*inherits\b", rest[len(_paren_body(rest, 0)) + 2:], re.I):
            t.opaque = f"created with INHERITS in {where}"
        return
    m = re.match(r"set\s+(?:session\s+|local\s+)?search_path\s*(?:to|=)\s*(.+)", s, re.I | re.S)
    if m:
        names = [_ident(x) for x in _split_top(m.group(1)) if x.strip().strip('"') != "$user"]
        root.path = ["public"] if not names or names == ["default"] else names
        return
    if re.match(r"reset\s+(search_path|all)\b", s, re.I):
        root.path = ["public"]
        return
    m = re.match(rf"alter\s+schema\s+({IDENT})\s+rename\s+to\s+({IDENT})", s, re.I)
    if m:
        old, new = _ident(m.group(1)), _ident(m.group(2))
        for key in [k for k in root.tables if k[0] == old]:
            root.tables[(new, key[1])] = root.tables.pop(key)
            root.gone[key] = f"schema renamed to {new} in {where}"
        return
    m = DROP_TYPE.match(s)
    if m:
        if re.search(r"\bcascade\b", m.group(3), re.I):
            for key, col in _typed_columns(root, m.group(1), m.group(3)):
                root.drop_col(key, col, f"{where} (drop {m.group(1).lower()} cascade)")
        return
    m = re.match(r"drop\s+schema\s+(?:if\s+exists\s+)?(.+)", s, re.I | re.S)
    if m:
        names = re.sub(r"\b(cascade|restrict)\b", "", m.group(1), flags=re.I)
        for raw in _split_top(names):
            schema = _qname(raw)[1]
            for key in [k for k in root.tables if k[0] == schema]:
                root.drop_table(key, f"{where} (drop schema)")
        return
    m = re.match(r"drop\s+table\s+(?:if\s+exists\s+)?(.+)", s, re.I | re.S)
    if m:
        names = re.sub(r"\b(cascade|restrict)\b", "", m.group(1), flags=re.I)
        for raw in _split_top(names):
            root.drop_table(root.resolve(*_qname(raw)), where)
        return
    m = re.match(rf"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?({QNAME})\s*\*?\s+(.*)", s, re.I | re.S)
    if not m:
        return
    key = root.resolve(*_qname(m.group(1)))
    for action in _split_top(m.group(2)):
        a = re.match(rf"rename\s+to\s+({QNAME})", action, re.I)
        if a:
            root.rename_table(key, _qname(a.group(1))[1], where)
            return
        a = re.match(rf"set\s+schema\s+({IDENT})", action, re.I)
        if a:
            if key in root.tables:
                nk = (_ident(a.group(1)), key[1])
                root.tables[nk] = root.tables.pop(key)
                root.gone[key] = f"table moved to schema {nk[0]} in {where}"
            return
        a = re.match(rf"rename\s+(?:column\s+)?({IDENT})\s+to\s+({IDENT})", action, re.I)
        if a and a.group(1).lower() != "constraint":
            root.rename_col(key, _ident(a.group(1)), _ident(a.group(2)), where); continue
        a = re.match(rf"add\s+(?:column\s+)?(?:if\s+not\s+exists\s+)?({IDENT})", action, re.I)
        if a and (a.group(1).startswith('"') or a.group(1).lower() not in NOT_COLUMN):
            root.add_col(key, _ident(a.group(1)), where, _type_of(action[a.end():])); continue
        a = re.match(rf"drop\s+(?:column\s+)?(?:if\s+exists\s+)?({IDENT})", action, re.I)
        if a and (a.group(1).startswith('"') or a.group(1).lower() not in NOT_COLUMN):
            root.drop_col(key, _ident(a.group(1)), where)


def _const(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == "text" and node.args:
        return _const(node.args[0])
    return None


def _arg(call: ast.Call, pos: int, kw: str) -> ast.AST | None:
    for k in call.keywords:
        if k.arg == kw:
            return k.value
    positional = [a for a in call.args if not isinstance(a, ast.Starred)]
    return positional[pos] if pos < len(positional) else None


def _column_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == "Column":
        return _const(_arg(node, 0, "name"))
    return None


HARMLESS = {"text", "print", "len", "range", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
            "isinstance", "getattr", "format", "sorted", "enumerate", "zip", "any", "all", "min", "max"}
DDL_OPS = {"create_table", "drop_table", "rename_table", "add_column", "drop_column", "alter_column"}


def replay_alembic(root: Root, text: str, where: str) -> None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        root.blind.append(f"{where} does not parse")
        return
    upgrade = next((f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == "upgrade"), None)
    if upgrade is None:
        return

    def blind(why: str) -> None:
        root.blind.append(f"{where}: {why}")

    def call(node: ast.Call, batch: dict[str, Key]) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            if func.id in helpers:
                if func.id not in stack:
                    stack.add(func.id)
                    walk(helpers[func.id].body, batch)
                    stack.discard(func.id)
            elif not (func.id[:1].isupper() or func.id in HARMLESS):
                blind(f"a call to {func.id}() the replay cannot follow")
            return
        if isinstance(func, ast.Attribute) and func.attr in ("execute", "exec_driver_sql") and not (
                isinstance(func.value, ast.Name) and func.value.id == "op"):
            sql = _const(_arg(node, 0, "statement"))
            replay_sql(root, sql, where) if sql is not None else blind(f"{func.attr}() with non-constant SQL")
            return
        if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
            return
        target, op = func.value.id, func.attr
        if target in batch:
            key = batch[target]
            if op == "add_column":
                col = _column_name(_arg(node, 0, "column"))
                root.add_col(key, col, where) if col else blind("add_column with a computed column")
            elif op == "drop_column":
                col = _const(_arg(node, 0, "column_name"))
                root.drop_col(key, col, where) if col else blind("drop_column with a computed name")
            elif op == "alter_column":
                col, new = _const(_arg(node, 0, "column_name")), _const(_arg(node, 99, "new_column_name"))
                if new and col:
                    root.rename_col(key, col, new, where)
            return
        if target != "op":
            if op in DDL_OPS or op == "execute":
                blind(f"{target}.{op} outside a recognised op/batch_alter_table context")
            return
        schema = _const(_arg(node, 99, "schema"))
        if op == "execute":
            sql = _const(_arg(node, 0, "sqltext"))
            replay_sql(root, sql, where) if sql is not None else blind("op.execute with non-constant SQL")
            return
        if op not in DDL_OPS:
            return
        table = _const(_arg(node, 0, "table_name" if op != "rename_table" else "old_table_name"))
        if table is None:
            blind(f"op.{op} with a computed table name"); return
        key = (schema or "public", table) if op == "create_table" else root.resolve(schema, table)
        if op == "create_table":
            t = root.create(key, where)
            for a in node.args[1:]:
                col = _column_name(a)
                if col:
                    t.columns[col] = where
        elif op == "drop_table":
            root.drop_table(key, where)
        elif op == "rename_table":
            new = _const(_arg(node, 1, "new_table_name"))
            root.rename_table(key, new, where) if new else blind("rename_table with a computed name")
        elif op == "add_column":
            col = _column_name(_arg(node, 1, "column"))
            root.add_col(key, col, where) if col else blind("add_column with a computed column")
        elif op == "drop_column":
            col = _const(_arg(node, 1, "column_name"))
            root.drop_col(key, col, where) if col else blind("drop_column with a computed name")
        elif op == "alter_column":
            col, new = _const(_arg(node, 1, "column_name")), _const(_arg(node, 99, "new_column_name"))
            if col and new:
                root.rename_col(key, col, new, where)

    def walk(stmts: list[ast.stmt], batch: dict[str, Key]) -> None:
        for st in stmts:
            if isinstance(st, ast.With):
                inner = dict(batch)
                for item in st.items:
                    ce = item.context_expr
                    if isinstance(ce, ast.Call) and getattr(ce.func, "attr", "") == "batch_alter_table":
                        table = _const(_arg(ce, 0, "table_name"))
                        if table is None or not isinstance(item.optional_vars, ast.Name):
                            blind("batch_alter_table with a computed table name"); continue
                        inner[item.optional_vars.id] = root.resolve(_const(_arg(ce, 99, "schema")), table)
                walk(st.body, inner)
                continue
            if isinstance(st, (ast.If, ast.For, ast.While, ast.Try)):
                for block in ("body", "orelse", "finalbody"):
                    walk(getattr(st, block, []), batch)
                for h in getattr(st, "handlers", []):
                    walk(h.body, batch)
                if isinstance(st, ast.If) and any(
                        isinstance(x, ast.Call) and (
                            getattr(x.func, "attr", "") in DDL_OPS | {"execute", "exec_driver_sql"}
                            or (isinstance(x.func, ast.Name) and x.func.id in helpers))
                        for x in ast.walk(st)):
                    blind("a conditional DDL branch in upgrade()")
                continue
            for node in sorted((x for x in ast.walk(st) if isinstance(x, ast.Call)), key=lambda x: (x.lineno, x.col_offset)):
                call(node, batch)

    helpers = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name not in ("upgrade", "downgrade")}
    stack: set[str] = set()
    walk(upgrade.body, {})


def _revision_ids(text: str) -> tuple[str | None, list[str]] | None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    values: dict[str, ast.AST] = {}
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            values[st.targets[0].id] = st.value
        elif isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name) and st.value is not None:
            values[st.target.id] = st.value
    if "revision" not in values:
        return None
    down = values.get("down_revision")
    parents = [] if down is None or (isinstance(down, ast.Constant) and down.value is None) else (
        [_const(e) for e in down.elts] if isinstance(down, (ast.Tuple, ast.List)) else [_const(down)])
    return _const(values["revision"]), [p or "?" for p in parents]


def _order(repo: Path, files: list[str]) -> tuple[list[str], str]:
    revs = [f for f in files if f.endswith(".py") and re.search(r"^def upgrade\s*\(", (repo / f).read_text(errors="replace"), re.M)]
    if not revs:
        return [f for f in files if not f.endswith(".py")], ""
    if any(f.endswith(".sql") for f in files):
        return revs, "SQL and Alembic migrations in one root: their order is unknown"
    ids: dict[str, tuple[str, list[str]]] = {}
    for f in revs:
        r = _revision_ids((repo / f).read_text(errors="replace"))
        if r is None or r[0] is None:
            return revs, f"{f} has no readable revision id"
        ids[r[0]] = (f, r[1])
    ordered, done = [], set()
    while len(done) < len(ids):
        ready = sorted((f, rid) for rid, (f, ps) in ids.items() if rid not in done and all(p in done for p in ps))
        if not ready:
            return revs, "the revision graph has a missing parent or a cycle"
        for f, rid in ready:
            ordered.append(f); done.add(rid)
    return ordered, ""


def _files(repo: Path) -> tuple[list[str], bool]:
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True)
    if tracked.returncode == 0:
        others = subprocess.run(["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard"],
                                capture_output=True, text=True).stdout.splitlines()
        files = sorted(set(tracked.stdout.splitlines()) | set(others))
        return [f for f in files if not (set(f.split("/")) & SKIP_DIRS) and (repo / f).is_file()], True
    found = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        found += [str((Path(root) / n).relative_to(repo)) for n in names]
    return found, False


def _when(repo: Path, rels: list[str], is_git: bool) -> float:
    """Newest change among rels: commit time when clean and tracked, file mtime otherwise."""
    newest = 0.0
    dirty: set[str] = set()
    if is_git:
        st = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--", *rels],
                            capture_output=True, text=True).stdout.splitlines()
        dirty = {line[3:].strip().strip('"') for line in st}
        ct = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%ct", "--", *rels],
                            capture_output=True, text=True).stdout.strip()
        newest = float(ct) if ct else 0.0
    for r in rels:
        if not is_git or r in dirty:
            newest = max(newest, (repo / r).stat().st_mtime)
    return newest


def scan(repo: Path) -> dict:
    files, is_git = _files(repo)
    migrations: dict[str, list[str]] = {}
    for f in files:
        if MIGRATION_FILE.search(f) and os.path.basename(f) != "__init__.py":
            migrations.setdefault(os.path.dirname(f), []).append(f)
    for d in migrations:
        migrations[d].sort()
    return {
        "is_git": is_git,
        "migrations": migrations,
        "orm": sorted(f for f in files if ORM_FILE.search(f) and not MIGRATION_FILE.search(f)),
        "types": sorted(f for f in files if TYPES_FILE.search(f)),
        "references": sorted(f for f in files if REFERENCE_FILE.search(f)),
    }


def _stamp(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "unknown"


def cmd_locate(repo: Path) -> int:
    s = scan(repo)
    if not s["migrations"] and not s["orm"] and not s["types"]:
        print("NONE: no migration directory, ORM model or generated types found.")
        print("  You cannot verify a column here. Ask where the schema lives, or create it before coding.")
        return 1
    newest = 0.0
    for d, fs in sorted(s["migrations"].items(), key=lambda kv: -len(kv[1])):
        ts = _when(repo, fs, s["is_git"])
        newest = max(newest, ts)
        print(f"MIGRATIONS {d}  {len(fs)} files  newest={os.path.basename(fs[-1])}  last-change={_stamp(ts)}")
    for f in s["orm"][:40]:
        print(f"ORM        {f}")
    if len(s["orm"]) > 40:
        print(f"ORM        … {len(s['orm']) - 40} more")
    for f in s["types"]:
        print(f"TYPES      {f}  last-change={_stamp(_when(repo, [f], s['is_git']))}")
    stale = False
    for f in s["references"]:
        ts = _when(repo, [f], s["is_git"])
        flag = ""
        if newest and ts < newest:
            flag, stale = f"  STALE: older than the newest migration ({_stamp(newest)})", True
        print(f"REFERENCE  {f}  last-change={_stamp(ts)}{flag}")
    if len(s["migrations"]) > 1:
        print("NOTE: more than one migration root — confirm which one the deployed database runs.")
    if stale:
        print("CONCERNS: a schema reference is older than the migrations. Use it as a map; take columns from migrations.")
        return 3
    print("OK")
    return 0


def replay(repo: Path, files: list[str]) -> Root:
    root = Root()
    ordered, problem = _order(repo, files)
    if problem:
        root.blind.append(problem)
    for f in ordered:
        if root.path[0] != "public" and not root.path_leak:
            root.path_leak = f"search_path {root.path} left set at the end of the previous file"
        root.path = ["public"]
        text = (repo / f).read_text(errors="replace")
        (replay_alembic if f.endswith(".py") else replay_sql)(root, text, f)
    return root


def _verdict(r: Root, schema: str | None, t: str, c: str) -> tuple[str, str] | None:
    known = {k for k in list(r.tables) + list(r.gone) if k[1] == t and (schema is None or k[0] == schema)}
    if not known:
        return None
    if schema is None and len({k[0] for k in known}) > 1:
        return ("AMBIGUOUS", f"table {t} exists in schemas {sorted(k[0] for k in known)}; name the schema")
    key = next(iter(known)) if len(known) == 1 else r.resolve(schema, t)
    if r.blind:
        return ("BLIND", f"cannot replay {r.blind[0]}; read the migrations by hand")
    if key in r.tables:
        tab = r.tables[key]
        if tab.opaque:
            return ("OPAQUE", f"{key[0]}.{t} {tab.opaque}; read it by hand")
        if c in tab.uncertain:
            return ("OPAQUE", f"{key[0]}.{t}.{c} {tab.uncertain[c]}; read it by hand")
        if c in tab.columns:
            return ("FOUND", f"{key[0]}.{t} declared in {tab.columns[c]}")
        if (key, c) in r.col_gone:
            kind = "RENAMED" if r.col_gone[(key, c)].startswith("renamed") else "DROPPED"
            return (kind, r.col_gone[(key, c)])
        return ("MISSING", f"{key[0]}.{t} exists ({tab.origin}), column never declared")
    return ("DROPPED", r.gone[key])


def live_columns(db: str, tables: set[str]) -> set[tuple[str, str, str]] | str:
    """(schema, table, column) rows of the live catalog, read-only; a string is the failure reason."""
    if not all(IDENT_ARG.match(t) for t in tables):
        return "refused: a table name is not a plain identifier"
    names = ",".join(f"'{t}'" for t in sorted(tables))
    sql = ("select coalesce(json_agg(json_build_array(table_schema, table_name, column_name)), '[]'::json) "
           f"from information_schema.columns where table_name in ({names})")
    env = dict(os.environ, PGOPTIONS=(os.environ.get("PGOPTIONS", "") + " -c default_transaction_read_only=on").strip(),
               PGCONNECT_TIMEOUT="10")
    psql = os.environ.get("SCHEMA_SCAN_PSQL", "psql")
    try:
        out = subprocess.run([psql, f"--dbname={db}", "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                              "-c", "begin transaction read only", "-c", sql, "-c", "rollback"],
                             capture_output=True, text=True, env=env, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"{psql} could not run: {e}"
    if out.returncode != 0:
        return (out.stderr.strip().splitlines() or [f"exit {out.returncode}"])[-1]
    lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
    if len(lines) != 1:
        return f"the catalog query must return exactly one line, got {len(lines)}"
    try:
        data = json.loads(lines[0])
    except ValueError as e:
        return f"the catalog query returned unreadable JSON: {e}"
    if not isinstance(data, list) or not all(
            isinstance(r, list) and len(r) == 3 and all(isinstance(x, str) for x in r) for r in data):
        return "the catalog query returned an unexpected shape"
    return {(r[0], r[1], r[2]) for r in data}


DB_ARG = re.compile(r"(postgres(?:ql)?://\S+|[A-Za-z_]+\s*=.*)\Z", re.S)


def _live_verdict(rows: set[tuple[str, str, str]], schema: str | None, t: str, c: str) -> tuple[str, str]:
    schemas = {r[0] for r in rows if r[1] == t and (schema is None or r[0] == schema)}
    if not schemas:
        return ("LIVE-NO-TABLE", f"no table or view {t} visible to this role")
    if len(schemas) > 1:
        return ("LIVE-AMBIGUOUS", f"{t} exists in schemas {sorted(schemas)}; name the schema")
    s = next(iter(schemas))
    return ("LIVE-FOUND", f"{s}.{t}.{c} in the live catalog") if (s, t, c) in rows else (
        "LIVE-MISSING", f"{s}.{t} has no column {c} in the live catalog")


def cmd_check(repo: Path, items: list[str], db: str | None = None) -> int:
    parsed = []
    for it in items:
        parts = it.split(".")
        if len(parts) not in (2, 3) or not all(parts):
            print(f"usage: '{it}' is not [schema.]table.column", file=sys.stderr)
            return 2
        if not all(p.isascii() and IDENT_RAW.match(p) for p in parts):
            print(f"usage: '{it}' must be plain identifiers ([a-z_][a-z0-9_$]*)", file=sys.stderr)
            return 2
        parts = [p.lower() for p in parts]
        parsed.append((parts[0] if len(parts) == 3 else None, parts[-2], parts[-1]))
    s = scan(repo)
    if not s["migrations"]:
        print("FAIL: no migration root to replay — the database state cannot be derived here. Run `locate`.")
        return 1
    roots = {d: replay(repo, fs) for d, fs in sorted(s["migrations"].items())}
    hints = s["orm"] + s["types"]
    rows: set[tuple[str, str, str]] | None = None
    if db is not None and not DB_ARG.match(db):
        print("usage: --db must be a postgresql:// URL or a key=value connection string", file=sys.stderr)
        return 2
    if db:
        got = live_columns(db, {t for _, t, _ in parsed})
        if isinstance(got, str):
            print(f"FAIL: --db was given but the live catalog could not be read: {got}")
            return 1
        rows = got
    bad = concerns = 0
    for schema, t, c in parsed:
        label = f"{schema + '.' if schema else ''}{t}.{c}"
        verdicts = [(k, f"{d}: {why}") for d, r in roots.items() if (v := _verdict(r, schema, t, c)) for k, why in [v]]
        if not verdicts:
            seen = [h for h in hints if re.search(rf"\b{re.escape(t)}\b", (repo / h).read_text(errors="replace"))]
            hint = f"; named in {seen[0]} — the model may be ahead of the database" if seen else ""
            verdicts = [("NO-TABLE", f"no migration creates table {t} (view, function, external){hint}")]
        for kind, why in verdicts:
            print(f"{kind:<13}{label}  {why}")
        static_ok = all(k == "FOUND" for k, _ in verdicts)
        if rows is None:
            if static_ok:
                concerns += 1
            else:
                bad += 1
            continue
        live, why = _live_verdict(rows, schema, t, c)
        print(f"{live:<13}{label}  {why}")
        if live != "LIVE-FOUND":
            bad += 1
        elif not static_ok:
            print(f"{'DRIFT':<13}{label}  live but not declared by the migrations: add the missing migration")
            concerns += 1
    if len(roots) > 1:
        print("NOTE: more than one migration root — a column passes only if every root that knows the table holds it.")
    if bad:
        return 1
    if concerns:
        if rows is None:
            print("CONCERNS: declared by the migrations, not proven. Re-run with --db <read-only url> to PASS.")
        return 3
    return 0


SELF_SQL = {
    "migrations/001_init.sql":
        "create table public.users (id uuid primary key, email text not null, nick text, old_name text,"
        " bio text, \"Email\" text, \"full address\" text, constraint u unique (email));\n"
        "create table cantieri (id uuid, note text); create table committenti (id uuid, email text);\n"
        "insert into users (id, email) values (1, '-- data; still a string');\n"
        "/* outer /* nested */ alter table users drop column email; */\n",
    "migrations/002_drop.sql":
        "-- alter table users drop column id;\nalter table users drop column nick, drop bio;\n"
        "alter table users rename column old_name to full_name;\n",
    "migrations/003_legacy.sql": "create table legacy (id uuid, note text);\n"
                                  "create table quirks (id uuid, label text default 'x, ghost text');\n",
    "migrations/004_gone.sql": 'drop table if exists "public"."legacy" cascade;\n',
    "migrations/005_mention.sql": "comment on table legacy is 'x'; select note from legacy;\n"
                                  "alter table cantieri add column if not exists stato text;\n"
                                  "create table if not exists cantieri (id uuid);\n",
    "migrations/006_ctas.sql": "create table snap as select * from users;\n",
    "migrations/007_do.sql": "create table events (id uuid, kind text); create table audit (id uuid, at text);\n"
                             "do $$ begin alter table events drop column kind; end $$;\n"
                             "create function f() returns void as $f$ begin insert into audit select * from events; end $f$;\n"
                             "create table logs (id uuid, msg text);\n"
                             "do $d$ declare t text; begin foreach t in array array['logs'] loop"
                             " execute format('alter table %I drop column msg', t); end loop; end $d$;\n"
                             "select $1 from events;\n"
                             "create table items (id uuid, note text); create table rls (id uuid);\n"
                             "do $$ begin execute 'alter table items drop column note'; "
                             "alter table rls enable row level security; end $$;\n",
    "migrations/008_schemas.sql": "create schema archive; create table archive.users (id uuid, email text);\n"
                                  "create table archive.notes (id uuid, body text);\n"
                                  "create schema tmp; create table tmp.scratch (id uuid); drop schema tmp cascade;\n"
                                  "create table moved (id uuid, v text); alter table moved set schema archive;\n",
    "migrations/009_schema_moves.sql":
        "create schema hist0; create table hist0.ev (id uuid, payload text); alter schema hist0 rename to hist1;\n"
        "create schema s2; create table s2.ev2 (id uuid, p text); do $$ begin drop schema s2 cascade; end $$;\n"
        "create schema sp; create table public.spt (id uuid, payload text); create table sp.spt (id uuid, payload text);\n"
        "set search_path to sp; alter table spt drop column payload; reset search_path;\n",
    "migrations/010_leak_a.sql": "create schema lk; create table public.lt (id uuid, v text); create table lk.lt (id uuid, v text);\n"
                                 "set search_path to lk;\n",
    "migrations/011_leak_b.sql": "alter table lt drop column v;\n",
    "app/models.py": "class Thing:\n    __tablename__ = 'things'\n    colour = Column(String)\n",
}
SELF_SQL_EXPECT = {
    "public.users.email": 0, "users.email": 1, "public.users.full_name": 0, "public.users.avatar": 1,
    "public.users.nick": 1, "public.users.bio": 1, "public.users.old_name": 1, "public.users.id": 0,
    "legacy.note": 1, "cantieri.email": 1, "cantieri.stato": 0, "snap.id": 1, "things.colour": 1,
    "events.kind": 1, "events.id": 0, "audit.at": 0, "logs.msg": 1, "items.note": 1, "items.id": 0,
    "rls.id": 0, "hist0.ev.payload": 1, "hist1.ev.payload": 0, "s2.ev2.p": 1, "sp.spt.payload": 1,
    "public.spt.payload": 0, "public.lt.v": 1, "lk.lt.v": 1, "archive.users.email": 0, "notes.body": 0,
    "public.users.full": 1, "quirks.label": 0, "quirks.ghost": 1, "scratch.id": 1, "archive.moved.v": 0, "public.moved.v": 1,
}
SELF_PY = {
    "alembic/versions/001.py":
        "revision = '001'\ndown_revision = None\n"
        "def upgrade():\n"
        "    op.create_table('users', sa.Column('id', sa.Integer), sa.Column('email', sa.Text),"
        " sa.Column('phone', sa.Text), sa.Column('nick', sa.Text), sa.Column('zip', sa.Text))\n"
        "    # op.add_column('users', sa.Column('ghost', sa.Text))\n"
        "def downgrade():\n    op.drop_table('users')\n",
    "alembic/versions/002.py":
        "revision = '002'\ndown_revision = '001'\n"
        "def downgrade():\n    op.add_column('users', sa.Column('email', sa.Text))\n"
        "def upgrade():\n"
        "    op.drop_column(column_name='email', table_name='users')\n"
        "    op.add_column('users', sa.Column('name', sa.Text))\n"
        "    op.execute('ALTER TABLE users DROP COLUMN phone')\n"
        "    with op.batch_alter_table('users') as batch_op:\n"
        "        batch_op.drop_column('nick')\n",
}
SELF_PY_HELPER = {
    "alembic/versions/001.py":
        "revision = '001'\ndown_revision = None\n"
        "def remove_obsolete():\n    op.drop_column('users', 'email')\n"
        "def upgrade():\n"
        "    op.create_table('users', sa.Column('id', sa.Integer), sa.Column('email', sa.Text), sa.Column('tag', sa.Text))\n"
        "    remove_obsolete()\n"
        "    conn = op.get_bind()\n    conn.execute(text('ALTER TABLE users DROP COLUMN tag'))\n",
}
SELF_PY_ORDER = {
    "alembic/versions/f00_create.py":
        "revision = 'f00'\ndown_revision = None\n"
        "def upgrade():\n    op.create_table('users', sa.Column('id', sa.Integer), sa.Column('email', sa.Text))\n",
    "alembic/versions/a00_drop.py":
        "revision: str = 'a00'\ndown_revision = 'f00'\ndef upgrade():\n    op.drop_column('users', 'email')\n",
}
SELF_WITNESSES = [
    ("reset", {"migrations/001.sql": "create schema archive; create table public.orders (id integer, obsolete text);\n"
                                    "create table archive.orders (id integer, obsolete text);\n"
                                    "set search_path to archive; reset search_path;\nalter table orders drop column obsolete;\n"},
     "public.orders.obsolete"),
    ("driver", {"alembic/versions/001.py": "revision = '001'\ndown_revision = None\ndef upgrade():\n"
                "    op.create_table('orders', sa.Column('id', sa.Integer), sa.Column('obsolete', sa.Text))\n"
                "    conn = op.get_bind()\n    conn.exec_driver_sql('ALTER TABLE orders DROP COLUMN obsolete')\n"},
     "orders.obsolete"),
    ("computed", {"alembic/versions/001.py": "revision = '001'\ndown_revision = None\ndef upgrade():\n"
                  "    op.create_table('orders', sa.Column('id', sa.Integer), sa.Column('obsolete', sa.Text))\n"
                  "    sql = sa.text('ALTER TABLE orders DROP COLUMN obsolete')\n    op.get_bind().execute(sql)\n"},
     "orders.obsolete"),
    ("imported", {"alembic/versions/001.py": "from helpers import remove_obsolete\nrevision = '001'\ndown_revision = None\n"
                  "def upgrade():\n    op.create_table('orders', sa.Column('id', sa.Integer), sa.Column('obsolete', sa.Text))\n"
                  "    remove_obsolete()\n"},
     "orders.obsolete"),
    ("catalog", {"migrations/001.sql": "create table orders (id integer, obsolete text);\n"
                 "do $$ declare rec record; begin for rec in select tablename from pg_tables loop"
                 " execute format('alter table %I drop column if exists obsolete', rec.tablename); end loop; end $$;\n"},
     "orders.obsolete"),
    ("type-cascade", {"migrations/001.sql": "create type order_status as enum ('pending', 'paid');\n"
                      "create table orders (id integer, status order_status);\ndrop type order_status cascade;\n"},
     "orders.status"),
    ("extension-cascade", {"migrations/001.sql": "create extension vector;\ncreate table docs (id integer, emb vector(3));\n"
                           "drop extension vector cascade;\n"},
     "docs.emb"),
    ("conditional-sql", {"alembic/versions/001.py": "revision = '001'\ndown_revision = None\ndef upgrade():\n"
                         "    op.create_table('orders', sa.Column('id', sa.Integer))\n    if legacy:\n"
                         "        op.execute('ALTER TABLE orders ADD COLUMN obsolete text')\n"},
     "orders.obsolete"),
    ("conditional-helper", {"alembic/versions/001.py": "revision = '001'\ndown_revision = None\n"
                            "def add_legacy():\n    op.add_column('orders', sa.Column('obsolete', sa.Text))\n"
                            "def upgrade():\n    op.create_table('orders', sa.Column('id', sa.Integer))\n"
                            "    if legacy:\n        add_legacy()\n"},
     "orders.obsolete"),
]
SELF_PY_EXPECT = {"users.email": 1, "users.name": 0, "users.ghost": 1, "users.phone": 1, "users.nick": 1, "users.zip": 0}


def selfcheck() -> int:
    def run(argv: list[str]) -> int:
        try:
            return main(argv)
        except SystemExit as e:
            return int(e.code or 0)

    def repo_with(base: Path, name: str, files: dict[str, str]) -> str:
        r = base / name
        for rel, text in files.items():
            (r / rel).parent.mkdir(parents=True, exist_ok=True)
            (r / rel).write_text(text)
        return str(r)

    branches = 0
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        empty = base / "empty"; empty.mkdir()
        assert run(["locate", "--repo", str(empty)]) == 1, "no schema must FAIL"
        assert run(["check", "--repo", str(empty), "users.email"]) == 1, "nothing to replay must FAIL"
        branches += 2
        r = repo_with(base, "sql", SELF_SQL)
        for item, declared in SELF_SQL_EXPECT.items():
            code = 3 if declared == 0 else 1
            assert run(["check", "--repo", r, item]) == code, f"sql: {item} must exit {code}"
        a = repo_with(base, "alembic", SELF_PY)
        for item, declared in SELF_PY_EXPECT.items():
            code = 3 if declared == 0 else 1
            assert run(["check", "--repo", a, item]) == code, f"alembic: {item} must exit {code}"
        branches += len(SELF_SQL_EXPECT) + len(SELF_PY_EXPECT)
        blind = repo_with(base, "blind", {"alembic/versions/001.py":
                                          "def upgrade():\n    op.create_table('t', sa.Column('a', sa.Text))\n    op.execute(SQL)\n"})
        assert run(["check", "--repo", blind, "t.a"]) == 1, "non-constant op.execute must make the root BLIND"
        h = repo_with(base, "helper", SELF_PY_HELPER)
        assert run(["check", "--repo", h, "users.email"]) == 1, "a helper called by upgrade() must be replayed"
        assert run(["check", "--repo", h, "users.tag"]) == 1, "conn.execute with constant SQL must be replayed"
        assert run(["check", "--repo", h, "users.id"]) == 3, "helpers do not blind the root"
        o = repo_with(base, "order", SELF_PY_ORDER)
        assert run(["check", "--repo", o, "users.email"]) == 1, "alembic revisions run in graph order, not file order"
        u = repo_with(base, "unparsable", {"alembic/versions/001.py": "def upgrade(:\n    pass\n",
                                             "migrations/001.sql": ""})
        bad = repo_with(base, "badpy", {"alembic/versions/001.py":
                                        "revision = '1'\ndown_revision = None\ndef upgrade():\n    op.create_table('t', sa.Column('a', sa.Text))\n",
                                        "alembic/versions/002.py": "revision = '2'\ndown_revision = '1'\ndef upgrade():\n    op.add_column('t', sa.Column('b', sa.Text)\n"})
        assert run(["check", "--repo", bad, "t.a"]) == 1, "an unparsable alembic file must make the root BLIND"
        assert u and run(["check", "--repo", u, "t.a"]) == 1, "nothing replayable stays a FAIL"
        branches += 7
        assert run(["check", "--repo", r, "usersemail"]) == 2, "bad item is a usage error"
        assert run(["check", "--repo", r]) == 2, "no item is a usage error"
        ref = Path(r) / "docs" / "schema-reference.md"; ref.parent.mkdir()
        ref.write_text("| users | avatar |\n")
        assert run(["check", "--repo", r, "public.users.avatar"]) == 1, "a reference doc is never evidence"
        mig = Path(r) / "migrations/008_schemas.sql"
        now = mig.stat().st_mtime
        os.utime(ref, (now - 3600, now - 3600))
        assert run(["locate", "--repo", r]) == 3, "reference an hour older than a migration must be CONCERNS"
        os.utime(ref, (now + 60, now + 60))
        assert run(["locate", "--repo", r]) == 0, "reference newer than every migration must PASS"
        assert run(["locate", "--repo", str(base / "absent")]) == 2, "absent repo is a usage error"
        branches += 7
        g = Path(repo_with(base, "git", {"migrations/001.sql": "create table users (id uuid, email text);\n"}))
        git = ["git", "-C", str(g), "-c", "user.email=s@s", "-c", "user.name=s"]
        if subprocess.run([*git, "init", "-q"]).returncode != 0:
            raise AssertionError("git is required for the untracked-migration branch")
        subprocess.run([*git, "add", "."], check=True)
        subprocess.run([*git, "commit", "-qm", "init"], check=True)
        (g / "migrations/002.sql").write_text("alter table users drop column email;\n")
        assert run(["check", "--repo", str(g), "users.email"]) == 1, "an untracked migration must be replayed"
        branches += 1
        for name, files, item in SELF_WITNESSES:
            assert run(["check", "--repo", repo_with(base, name, files), item]) == 1, f"{name}: {item} must FAIL"
        branches += len(SELF_WITNESSES)
        stub = base / "psql_stub.py"
        stub.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "if 'default_transaction_read_only=on' not in os.environ.get('PGOPTIONS', ''):\n"
            "    sys.exit(9)\n"
            "if 'begin transaction read only' not in sys.argv or 'rollback' not in sys.argv:\n"
            "    sys.exit(8)\n"
            "if not any(a.startswith('--dbname=') for a in sys.argv[1:2]):\n"
            "    sys.exit(6)\n"
            "want = (\"select coalesce(json_agg(json_build_array(table_schema, table_name, column_name)), '[]'::json) \"\n"
            "        \"from information_schema.columns where table_name in (\")\n"
            "if (want + \"'users')\") not in sys.argv:\n    sys.exit(7)\n"
            "rc = int(os.environ.get('STUB_RC', '0'))\n"
            "if rc:\n    print('connection refused', file=sys.stderr); sys.exit(rc)\n"
            "raw = os.environ.get('STUB_JSON')\n"
            "rows = [r.split('\\t') for r in os.environ.get('STUB_ROWS', '').split(';') if r]\n"
            "print(raw if raw is not None else json.dumps(rows))\n"
            "if os.environ.get('STUB_EXTRA'):\n    print(os.environ['STUB_EXTRA'])\n")
        stub.chmod(0o755)
        live_repo = repo_with(base, "live", {"migrations/001.sql": "create table users (id uuid, email text);\n"})
        saved = {k: os.environ.get(k) for k in ("SCHEMA_SCAN_PSQL", "STUB_ROWS", "STUB_RC", "STUB_JSON", "STUB_EXTRA")}
        os.environ["SCHEMA_SCAN_PSQL"] = str(stub)
        try:
            os.environ["STUB_ROWS"] = "public\tusers\tid;public\tusers\temail;public\tusers\tnick"
            os.environ["STUB_RC"] = "0"
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 0, "declared and live must PASS"
            assert run(["check", "--repo", live_repo, "users.email"]) == 3, "declared but unproven is CONCERNS"
            assert run(["check", "--repo", live_repo, "users.nick", "--db", "postgresql://stub/db"]) == 3, "live but undeclared is DRIFT"
            os.environ["STUB_ROWS"] = "public\tusers\tid"
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 1, "declared but not live must FAIL"
            os.environ["STUB_ROWS"] = "public\tusers\temail;archive\tusers\temail"
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 1, "live in two schemas is AMBIGUOUS"
            os.environ["STUB_JSON"] = json.dumps([["public", "users", "id\npublic\tusers\temail"]])
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 1, "a name with tabs or newlines cannot forge a row"
            os.environ["STUB_JSON"] = "public\tusers\temail"
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 1, "non-JSON catalog output must FAIL"
            os.environ["STUB_JSON"] = '[["public", "users"]]'
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 1, "a malformed catalog row must FAIL"
            os.environ.pop("STUB_JSON", None)
            os.environ["STUB_ROWS"] = "public\tusers\temail"
            os.environ["STUB_EXTRA"] = '[["public", "users", "email"]]'
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 1, "extra output lines must FAIL"
            os.environ.pop("STUB_EXTRA")
            assert run(["check", "--repo", live_repo, "users.email", "--db", "-cBEGIN READ WRITE"]) == 2, \
                "a --db that looks like a psql option is a usage error"
            assert run(["check", "--repo", live_repo, "users.email", "--db", "nonsense"]) == 2, \
                "a --db that is neither a URL nor key=value is a usage error"
            os.environ.pop("STUB_JSON", None)
            assert run(["check", "--repo", live_repo, "users'); select 1; --.email", "--db", "postgresql://stub/db"]) == 2, "SQL in a name is a usage error"
            assert run(["check", "--repo", live_repo, "users\\'.email"]) == 2, "a backslash or quote in a name is a usage error"
            assert run(["check", "--repo", live_repo, "users.\u212a", "--db", "postgresql://stub/db"]) == 2, \
                "a non-ASCII look-alike that lowercases to ASCII is a usage error"
            os.environ["STUB_RC"] = "2"
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 1, "an unreachable --db must FAIL"
            os.environ["SCHEMA_SCAN_PSQL"] = str(base / "no-such-psql")
            assert run(["check", "--repo", live_repo, "users.email", "--db", "postgresql://stub/db"]) == 1, "a missing psql must FAIL"
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        branches += 16
    print(f"selfcheck: ok ({branches} branches)")
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None and "--selfcheck" in sys.argv[1:]:
        return selfcheck()
    p = argparse.ArgumentParser(description="Find a repository's schema truth before any database work.")
    sub = p.add_subparsers(dest="cmd", required=True)
    lo = sub.add_parser("locate"); lo.add_argument("--repo", required=True)
    ch = sub.add_parser("check"); ch.add_argument("--repo", required=True); ch.add_argument("items", nargs="*")
    ch.add_argument("--db", help="read-only connection URL; the only way to PASS")
    a = p.parse_args(argv)
    repo = Path(a.repo).resolve()
    if not repo.is_dir():
        print(f"usage: {repo} is not a directory", file=sys.stderr)
        return 2
    if a.cmd == "locate":
        return cmd_locate(repo)
    if not a.items:
        print("usage: check needs at least one [schema.]table.column", file=sys.stderr)
        return 2
    return cmd_check(repo, a.items, a.db)


if __name__ == "__main__":
    sys.exit(main())
