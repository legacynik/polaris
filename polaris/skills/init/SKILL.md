---
name: init
description: ◇ Use to bring a repository that already exists into the harness — the first time a repo has no typed CONTEXT.md, ARCHITECTURE.md or DOMAIN.md, or when the context pack emits nothing there. Audits before it writes, asks one question per unprovable choice, and applies only the minimal mode. Do NOT use to refactor a repository, to create documentation areas, or on a repo already sealed READY.
version: 0.2.0
user-invocable: true
auto: false
lifecycle: one alignment plan per run → the founder signs the areas → apply seals the backbone once
invokes: []
invoked-by: [human]
io: receives a repository root → emits an audit JSON, an alignment plan, and (only on apply) a typed backbone plus its seal
status: active
---

# init

Brings a repository that already has years of history into the harness. It does not copy a
template: it looks at the repository, says what does not hold, proposes, and only then writes.

The first pass **does no work**. Audit and propose write zero files; that is the contract, not a
courtesy. Minimal mode is additive: existing prose stays, and every line no path proves says
`UNKNOWN`.

## Where this goes (host repository decides)

A skill decides **how**, never **where**. Before writing, read the host repository's output map.

```bash
sed -n '/^outputs:/,/^[^ ]/p' _polaris/config.yml 2>/dev/null || sed -n '/^outputs:/,/^[^ ]/p' config.yml
```

This skill produces: **audit** (the alignment plan). The backbone documents it writes are fixed by
the contract and live at the repository root; they are not a choice this map governs.

## When not to use it

- To refactor a repository, move files, or touch its CI — minimal mode never does, and the full
  mode does not exist yet.
- To create a documentation area or a module dossier. Areas are **proposed and signed**, never
  derived: a dossier without a manifest the founder signed blocks the seal by design.
- On a repository whose backbone already seals `READY` — re-running writes nothing useful.

## Step 1 — Resolve the harness, or stop

The package ships the skill, never the harness. The scripts live in the vault, declared per
repository the same way `polaris.login` is.

```bash
VAULT="$(git config --get polaris.vault || true)"
[ -n "$VAULT" ] && [ -f "$VAULT/scripts/polaris_init.py" ] || {
  echo "no harness declared here: git config polaris.vault <path>"; exit 0; }
```

Empty or missing: say that one line and **stop**. Never guess a path, never vendor a copy of the
scripts into the host repository.

## Step 2 — Audit, and read the questions

```bash
python3 -I "$VAULT/scripts/polaris_init.py" audit --root .
```

JSON: each live document as `absent`, `prose` or `typed`; every blocking finding with the remedy
`apply` would apply; the prose ADR and `decisions.md` counts; and `questions` — one per choice this
run cannot prove. Read them. A blocker whose remedy says *founder answer required* will not clear
by re-running.

The `vault` field says what `polaris.vault` currently points at and whether it still resolves.
Re-read it every run: the pointer lives in the shared `.git/config`, so a parallel session
rewrites it under you, and a dead pointer means the pack stops emitting with no error.

## Step 3 — Propose, and get the areas signed

```bash
python3 -I "$VAULT/scripts/polaris_init.py" propose --root .
```

A Markdown plan: what `apply` would do, the candidate areas as a table to sign, and the questions
numbered. Put it in front of the founder and **wait**. The areas table is the signature request;
candidates come from a declared map or from the folders that exist, never from the domain.

A cockpit with no `## Active Priorities` heading is listed here as a question, because the brief
then reads `no priority 1`. It is never written: which priorities, in which order, is the
founder's to state.

## Step 4 — Apply the minimal mode, then check the pack

Only after the answers. Minimal is the only mode.

```bash
python3 -I "$VAULT/scripts/polaris_init.py" apply --mode minimal --root .
python3 -I "$VAULT/scripts/check_context_backbone.py" --init .
python3 -I "$VAULT/scripts/contextpack.py" resolve --root . | head -20
```

`apply` adds the typed frontmatter around the prose, writes the two missing documents with their
unproven lines as `UNKNOWN`, declares every shadow copy derived, records one accepted Decision for
the adoption, and points the repository at the vault. It refuses **whole rather than half**: if a
dossier has no signed manifest, nothing is written at all and the codes are printed.

Then `--init` must say `READY` and the pack must emit an identifier. If `--init` still blocks, the
audit's questions are the work, not a re-run.

## Proof it worked

- `--init` prints `"verdict": "READY"` and `decisions/manifest.json` exists.
- `contextpack.py resolve` exits 0 and prints a `context_pack_id`, where it printed none before.
- The prose that was in `CONTEXT.md` is still in `CONTEXT.md`.
