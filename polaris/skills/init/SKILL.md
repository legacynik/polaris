---
name: init
description: ◇ Use to bring a repository that already exists into the harness — the first time a repo has no typed CONTEXT.md, ARCHITECTURE.md or DOMAIN.md, or when the context pack emits nothing there. Audits before it writes, asks one question per unprovable choice, and applies only the minimal mode. Do NOT use to refactor a repository, to create documentation areas, or on a repo already sealed READY.
version: 0.4.0
user-invocable: true
auto: false
lifecycle: one alignment plan per run → the repo owner signs the areas → apply seals the backbone once
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
  derived: a dossier without a manifest the repo owner signed blocks the seal by design.
- On a repository whose backbone already seals `READY` — re-running writes nothing useful.

## Step 1 — Resolve the scripts

The scripts ship in this skill's own `scripts/`; the backbone checker comes from the installed
`architecture` skill next to it. Nothing else is needed.

```bash
INIT="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/init/scripts"
[ -f "$INIT/polaris_init.py" ] || { echo "init is not installed: $INIT"; exit 1; }
```

Never copy the scripts into the host repository. A Polaris vault is optional: when the scripts
run from one, `apply` also points the repository at it; installed without one, that step is
skipped and nothing is pointed anywhere.

## Step 2 — Audit, and read the questions

```bash
python3 -I "$INIT/polaris_init.py" audit --root .
```

JSON: each live document as `absent`, `prose` or `typed`; every blocking finding with the remedy
`apply` would apply; the prose ADR and `decisions.md` counts; and `questions` — one per choice this
run cannot prove. Read them. A blocker whose remedy says *founder answer required* will not clear
by re-running: it is a question for the repo owner.

The `vault` field says what `polaris.vault` currently points at and whether it still resolves.
Re-read it every run: the pointer lives in the shared `.git/config`, so a parallel session
rewrites it under you. `VAULT_UNDECLARED` appears only when the scripts run from a vault.

## Step 3 — Propose, and get the areas signed

```bash
python3 -I "$INIT/polaris_init.py" propose --root .
```

A Markdown plan: what `apply` would do, the candidate areas as a table to sign, and the questions
numbered. Put it in front of the repo owner and **wait**. The areas table is the signature request;
candidates come from a declared map or from the folders that exist, never from the domain.

A cockpit with no `## Active Priorities` heading is listed here as a question, because the brief
then reads `no priority 1`. It is never written: which priorities, in which order, is the
repo owner's to state.

## Step 4 — Apply the minimal mode, then check the pack

Only after the answers. Minimal is the only mode.

```bash
python3 -I "$INIT/polaris_init.py" apply --mode minimal --root .
python3 -I "$INIT/check_context_backbone.py" --init .
git add CONTEXT.md ARCHITECTURE.md DOMAIN.md decisions/
git commit -m "chore(polaris): init minimal — typed backbone with UNKNOWN, prose kept"
VAULT="$(git config --get polaris.vault || true)"
if [ -f "$VAULT/scripts/contextpack.py" ]; then
  python3 -I "$VAULT/scripts/contextpack.py" resolve --root . | head -20
else echo "no vault: ContextPack check skipped (the resolver ships with the vault only)"; fi
```

The commit is **not** optional and **not** last. The pack seals against the committed tree,
so resolving before the commit reads a HEAD that has none of this: it exits 0 and prints
`CTX-UNKNOWN` with `documents: 0`, which looks like success and is not.

`apply` adds the typed frontmatter around the prose, writes the two missing documents with their
unproven lines as `UNKNOWN`, declares every shadow copy derived, records one accepted Decision for
the adoption, and, only when run from a vault, points the repository at it. It refuses **whole rather than half**: if a
dossier has no signed manifest, nothing is written at all and the codes are printed.

Then `--init` must say `READY`, and with a vault the pack must emit an identifier. If `--init` still blocks, the
audit's questions are the work, not a re-run.

## Proof it worked

Exit 0 proves nothing here — read the values.

- `--init` prints `"verdict": "READY"` and `decisions/manifest.json` exists.
- With a vault: `contextpack.py resolve`, **after the commit**, prints `workspace` that is not
  `UNKNOWN` and `documents: 3`. A `CTX-UNKNOWN` id with `documents: 0` is the failure that exits 0.
  Without one, the skip line is the expected output, not a failure.
- The prose that was in `CONTEXT.md` is still in `CONTEXT.md`, line for line.

If `audit` reported `VAULT_UNDECLARED`, the scripts run from a vault the repository does not
point at yet: `apply` sets the pointer, so it clears on the same run.
