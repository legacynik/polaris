# Context pack

What an agent receives about the repository before it acts: the decisions in force, the live
documents and the area's files, each row saying why it entered and whether it is known to be true.
It replaces "the agent reads whatever it finds" with a list that can be checked.

The pack is optional. It needs the resolver (`scripts/contextpack.py`); without it `start` prints
no `PACK:` lines and the session continues.

## What a row is

Every row carries `source_id`, `source_hash`, `freshness` and `reason`, and comes from one of four
layers:

| Layer | Where it comes from | Freshness | Trust it as |
|---|---|---|---|
| **sealed** | committed HEAD: the live documents (`CONTEXT.md`, `ARCHITECTURE.md`, `DOMAIN.md`), decision files in force (`accepted` or `executed`) whose domains match the work, and the area's `module-context.json` set | `CURRENT`, or `STALE` when a path it cites is gone | authority |
| **declared** | prose the repository already has: hand-written ADRs, a plain `CONTEXT.md`, plans, `decisions.md` | `UNKNOWN` | authority nobody proved fresh; check it against the code |
| **flight** | git and the tracker at a declared moment: open issues and PRs of the area, unmerged branches, other worktrees, recent handoffs from other people, uncommitted files | `UNKNOWN`, `landed: false` | news, never authority |
| **UNKNOWN** | an authority the work needs and the repository does not have | `UNKNOWN` | a gap, said out loud instead of left silent |

Superseded, deprecated and proposed decisions never enter; they are listed under `dropped` with the
reason.

## How it is built

1. **Domains first.** The work item names its area; the area names its domains; only decisions that
   govern those domains are selected.
2. **Freshness is read now.** Every path a row cites must exist at read time. Nothing is sealed in
   advance, so nothing goes stale between a write and a read.
3. **A budget, cut in a fixed order.** The pack has a token budget. When it overflows, flight rows go
   first, then declared rows; sealed and `UNKNOWN` rows are never cut. A handoff older than the
   flight window is history and does not enter.
4. **A receipt.** With a session id the resolver writes a receipt beside the session: which rows,
   which hashes, at which commit. The pack id (`CTX-<workspace>-<hash>`) names that exact set.

## When it loads

- `start` does **not** print the pack. It prints one line, `PACK: <n> rows held for lane entry`.
  The pack loads when work enters an area, because a measurement showed the full pack at session
  start changed no brief.
- After the conversation is compacted, a hook reprints the pack from the receipt
  (`session_gate.py reinsert`). If HEAD has not moved, nothing is recomputed and the tracker is not
  called. If HEAD moved, the pack is resolved again and the new receipt names the old one.

## Guided and autonomous

| Mode | A cited path is missing |
|---|---|
| guided (a person is reading) | a `STALE` row names the path; exit 0 |
| `--check` | exit 2, `CITED_PATH_MISSING`: citing a path that is not there is a false claim |
| `--autonomous` (nobody reads it) | the pack blocks |

## Why it is built this way

- **Rows, not recall.** A summary or a semantic search cannot prove what it left out. A list of rows
  with a reason each can be checked for omissions and conflicts.
- **An index, not everything.** A small resident core plus an index with the cost of each entry; the
  rest opens on request. Loading everything up front cost tens of thousands of tokens before the
  first useful action.
- **News is labelled as news.** Work in flight gets an address in the pack instead of loosening the
  seal: a flight row says `landed: false`, and a reader who treats it as truth has ignored the label.
