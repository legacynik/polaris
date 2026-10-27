---
title: start — after a compaction
description: Step 3b of the pre-form start body, kept verbatim: the SessionStart hook puts the pack back from the receipt, and what each line it prints means.
status: active
---

## Step 3b — After a compaction, put the pack back (never rebuild it)

A compaction empties the context window and leaves the receipt on disk. **Do not run `start`
again and do not re-read the resume set**: the pack was already resolved, and re-resolving it
walks the tracker over the network for an answer that has not changed.

Step 2 installs a `SessionStart` hook with the `compact` matcher, so on Claude Code this runs
by itself. On a host with no compaction event, or before that hook's first session, run it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" \
  reinsert --root "$ROOT"
```

The door finds the reinserter where it finds everything else — this repository first, then
the vault it declares — and asks it for the CHECKOUT, which is where the session and the pack
receipt both live. Asking for `$ROOT` (`<repo>/_polaris`) answered `NO_OPEN_SESSION` in every
product repository, on the one path that runs by itself.

No output at all: no reinserter here and none in the declared vault, so there is nothing to
put back. Otherwise read what it prints:

- `REINSERT: HEAD unchanged … — 0 tracker calls` followed by `PACK:` and the rows — the same
  pack, reprinted from the receipt. Nothing was recomputed and nothing was fetched.
- `REINSERT: HEAD moved <a> -> <b>` — commits landed under the session, so the pack was
  resolved again and a second receipt now sits beside the first, naming it in `CHAIN: prev=`.
- `RECEIPT_MISSING:`, `RECEIPT_UNREADABLE:`, `RECEIPT_TAMPERED:`, `SID_MISMATCH:`,
  `AREA_MISMATCH:` or `CHAIN_BROKEN:` — the receipt on disk could not be trusted, so the pack
  was resolved instead of reused. All are costs, not failures; the command still exits 0, and
  nothing on disk is overwritten. Report the line: it says something about the session.
- `NO_OPEN_SESSION:` — no session receipt is open, so there is no pack to put back. Since
  Step 5b opens one, this now means the session was closed by `end`, or
  this repository carries no engine at all.

`CHAIN_UNANCHORED:` may appear beside any of these. It is a report, not a refusal: every
link is there and nothing ties that area's packs to a start receipt.

The session id is not a flag anybody has to fill: the command resolves the session open today.
The same door verifies the receipt chain on demand — exit 1 on a `CHAIN_BROKEN`, 0 on anything
it merely reports:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" \
  chain --root "$ROOT"
```

`--sid` and `--area` narrow it to one session or one area; without them it asks about the
session open today, the same one everything else here is about.
