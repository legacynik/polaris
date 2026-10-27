---
name: init
description: "◇ Polaris — bring an existing repository into the harness: audit, propose, then write a typed CONTEXT/ARCHITECTURE/DOMAIN backbone; with --team required|optional, pin a Polaris release the whole team auto-installs. Use when a repo has none of those or the context pack emits nothing there. Not for refactors or repos already sealed READY. Requires git and python3; --team also gh and npx; scripts/install_deps.py sets up bd (Beads), browser-harness and the MCP servers the skills use."
version: 0.7.1
user-invocable: true
auto: false
lifecycle: one alignment plan per run → the repo owner signs the areas → apply seals the backbone once; --team writes a pin the team commits
invokes: []
invoked-by: [human]
io: receives a repository root → emits an audit JSON, an alignment plan, and (only on apply) a typed backbone plus its seal; with --team, a version pin, a session hook and an AGENTS.md section
status: active
---

# init

## What it does

Brings a repository with years of history into the harness without a template: it audits, says
what does not hold, proposes, and writes only after the repo owner answers. Minimal mode is
additive: existing prose stays, every line no path proves says `UNKNOWN`. With `--team`, it pins a
Polaris release in the repo so every teammate's sessions install and update it on their own.

## When

- A repo has no typed `CONTEXT.md`, `ARCHITECTURE.md` or `DOMAIN.md`, or the pack emits nothing.
- A team wants the same Polaris version for everyone: `--team required` blocks skills until it is
  installed, `--team optional` only nudges.
- First setup on a machine, or a skill reports a missing dependency: `python3 "$INIT/install_deps.py"
  deps` lists what it would install (`--apply` installs), `doctor` checks without writing.

## Steps

The scripts live in this skill's `scripts/` folder (`INIT`); never copy them into the host repo.
Before choosing, ask the agent memory if it is installed (`ai-memory-retrieval`) whether this repo
was initialised before; skip it if absent. Full procedure: `references/procedure.md`.

1. **Audit** (writes nothing): `python3 -I "$INIT/polaris_init.py" audit --root .` — read every
   `questions` entry; a blocker that needs a founder answer will not clear by re-running.
2. **Propose**: `python3 -I "$INIT/polaris_init.py" propose --root .` — put the plan and the areas
   table in front of the repo owner and **wait** for the signature and the answers.
3. **Apply**: `python3 -I "$INIT/polaris_init.py" apply --mode minimal --root .`, then
   `python3 -I "$INIT/check_context_backbone.py" --init .` must print `READY`.
4. **Commit before resolving**: `git add CONTEXT.md ARCHITECTURE.md DOMAIN.md decisions/` and commit;
   only then resolve the context pack, if the repo points at a vault.
5. **Team mode** (optional): `<owner>/<name>` is the repo Polaris was installed from (the `source`
   of `init` in `~/.agents/.skill-lock.json`); pick a released tag
   (`gh release view --repo <owner>/<name> --json tagName --jq .tagName`), then
   `python3 "$INIT/polaris_team.py" --team required|optional --ref <tag> --repo <owner>/<name> --root .` and commit
   `.polaris/`, `.claude/settings.json` and `AGENTS.md`. Details: `references/team-mode.md`.

## Where this goes

The host repo's `outputs:` map (`config.yml`) decides where. This skill produces: **audit** (the
alignment plan); the backbone documents and the team pin live at the repo root by contract.

## Output

- Audit JSON and a Markdown alignment plan; after apply, the typed backbone, `decisions/manifest.json`
  and one commit. Proof is in the values, not exit 0: `"verdict": "READY"`, and with a vault the
  pack, resolved after the commit, shows `documents: 3` (`CTX-UNKNOWN` with 0 documents is a failure).
- With `--team`: `.polaris/team.json` (the pin), `.polaris/session-start.sh` (hourly, silent,
  fail-open install of the pin), the session hook in `.claude/settings.json`, an `AGENTS.md` section.

## Not for

- Refactoring a repo, moving files or touching CI: minimal mode never does.
- Creating a documentation area or dossier: areas are proposed and signed, never derived.
- A repo whose backbone already seals `READY`: re-running writes nothing useful.
- Installing the skills themselves: that is `npx skills add`; this skill only wires their dependencies.
