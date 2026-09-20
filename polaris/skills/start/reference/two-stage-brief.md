# The two-stage brief — how to read it

`brief_signals.py` returns this only where the host repository carries the typed backbone
(polaris-os#405). It replaces the single line `PACK=CTX-<id>`, which polaris-os#326 measured:
an opaque id is an id the agent ignores, so the resolver was invisible to the session it
exists for, and the founder kept being the index of his own repository out loud.

Read it once, in order, and act on it. Do not summarise it away.

## Where the resolver lives — the host, then the vault the repo declares

A product repository carries the **contract** (`_polaris/`) and never the harness, so looking for
the compiler only inside the host is why `/start` stayed silent in repositories whose vault
already answers with a full pack. Two places are tried, first one wins, and nothing else:

1. `<root>/scripts/contextpack_dashboard.py` — a host that ships its own compiler owns it.
2. `<vault>/scripts/contextpack_dashboard.py`, where `<vault>` is `$POLARIS_VAULT` if it is set
   and a directory, else what the repository declares with
   `git config polaris.vault <path>` — a LOCAL declaration, so it never travels in a commit.

Neither present is still SILENCE (contract #155): a repository with no backbone within reach must
not learn the feature exists. A declared vault that no longer holds the script is that same case,
never an error.

The pack is compiled against the **checkout** (`git rev-parse --show-toplevel`), not against
`$ROOT`: the typed documents — `CONTEXT.md`, `DOMAIN.md`, `decisions/` — live at the root of the
repository, beside the `_polaris/` contract directory, not inside it.

And a **prose pack is a pack**. No `decisions/manifest.json` is required: the `declared` layer,
with `freshness: UNKNOWN` stated on every row, is valid by contract (polaris-os#403). Requiring a
manifest is what kept every product repository silent, since none of them has one. The resolver
still refuses out loud when it must — `PACK: blocked — <CODE>` — and that refusal is the gate,
not a precondition the package checks for it.

## Stage one — the index of the areas

```
AREA: <slug>  issues: N  prs: N  last_decision: <id> (<date>)
ISSUES_UNLABELLED: <n> open issue(s) carry no area label
PRS_UNLABELLED: <n> open PR(s) carry no area label
PRIORITY1: <the cockpit's first active priority>
```

One row per area: where the open work actually is. Three things matter about the counts:

- `UNKNOWN` is a count **nobody could read** — no `gh`, no auth, a refusal, a timeout. It is
  never a zero. A zero means *this area has no open work*, and inventing one sends the
  session to the quiet area.
- `ISSUES_UNLABELLED` and `PRS_UNLABELLED` say the per-area zeros are not the whole story:
  that many open issues or pull requests carry no area label, so they are counted nowhere. A
  label like `P1` or `task` is not an area.
- `last_decision: none` means the area has no accepted Decision; `UNKNOWN` means the
  register could not be read. Different answers, never merged.

`UNKNOWN: no area map` replaces the whole index when the repository declares no areas, which
is the normal case outside this workspace: the map is a repository's own issue labels crossed
with the domains its `DOMAIN.md` declares, and a repository that has just adopted the harness
declares none of them. **That is not a reason to withhold the pack.** There is nothing to ask
about and nothing to filter by, so the brief says `UNKNOWN: no area map — unfiltered pack`
and hands over the whole pack. Read the rows; there is simply no area column to trust.

## Stage two — the pack of the chosen area

```
AREA_CHOSEN: <slug>
layer: <sealed|declared|flight|unknown>  source_id: <id>  path: <path>  freshness: <CURRENT|UNKNOWN>
```

The area is resolved by the signals of plan section 3, in order, first answer wins: the area
named outright, then the branch's own name, then the issue the branch names (`fix/1234-…` →
issue #1234 → its area label), then this contributor's open issues, then the cockpit's
priority 1. **A signal that answers twice does not answer**: a branch called
`feat/gates-memoria` names no area, and the brief asks instead of picking one.

Those rows ARE the area's context. Act on them; open only what the work needs; never paste in
a document the pack merely pointed at. `freshness: UNKNOWN` is a claim nothing proved current
— treat it as a claim and resolve state against the code, not against the row.

## When the brief cannot answer

- `QUESTION: which area? candidates: …` — no signal answered. Ask exactly that one question,
  with the index already in front of the reader, and stop. Never guess an area, and never
  resolve a second one to compare.
- `PACK: blocked — <CODE>: <detail>` — the resolver refused. The index above it is still
  good: name the cause in the brief, use the index, and do not work around the refusal.
- `RECEIPT: none — no open session` — the rows are real, and nothing recorded that they were
  handed over. It appears when no session receipt is open and younger than a day, which is
  the normal case until `/start` itself opens one.
- No line at all — the repository has no resolver. It must not learn the feature exists
  (contract #155), so there is nothing to report.

## After a compaction — the pack comes back from the receipt

The brief above is resolved once. A compaction throws it out of the context window and changes
nothing on disk, so the repair is a READ, not a second resolution (polaris-os#406):
`contextpack_reinsert.py reinsert` reads the newest receipt of the open session and, when `HEAD`
is where the receipt says it was, prints its rows again with **zero** tracker calls. Only a moved
`HEAD` is a reason to pay for a new emission.

```
REINSERT: HEAD unchanged <sha12> — 0 tracker calls
PACK: CTX-<id> seal=<sha12> (reused from area-<slug>.json)
CHAIN: prev=<sha12>
<layer>   <source_id>  <source_hash12>
```

Two things the rows are NOT. They are not the documents: a receipt keeps an address, a layer and
a hash per row, which is what progressive delivery hands over anyway — open what the work needs.
And they are not a fresh claim: the hash is what the row was worth at `sealed_commit`, so state
still resolves against the code.

Six lines say the receipt could not be trusted and the pack was resolved instead:
`RECEIPT_MISSING` (none), `RECEIPT_UNREADABLE` (one that no longer parses — kept, never
overwritten), `RECEIPT_TAMPERED` (it does not hash to its own claims), `SID_MISMATCH` (it was
written for another session), `AREA_MISMATCH` (no receipt for this area) and `CHAIN_BROKEN`.
Each is a cost, not a failure, and none of them leaves the agent without a pack.

`CHAIN: prev=` is what ties a pack receipt to the session that received it. The first receipt of
a session names its `start.json`; each later one names the receipt it superseded, and none of
them replaces the one before — after a compaction at a moved `HEAD` the session keeps both, so
what the agent had BEFORE the compaction is still auditable. `contextpack_reinsert.py chain
--root <root> --sid <sid>` verifies those links. It reports `CHAIN_BROKEN` for a predecessor
no receipt of the session can show, and for a `prev` walk that loops instead of reaching the
start receipt — a receipt naming itself, or two naming each other, make every link resolve
while the chain terminates nowhere. `CHAIN_UNANCHORED` is the third and weakest: every link
is there and the oldest names no predecessor, which is also what a session looks like until
`/start` opens one, so it is reported, blocks no reinsertion and fails no exit code.

Chains are **per area** — a receipt's predecessor is the one it superseded in its own area,
and the first of each area reaches the `start.json`. So `chain` takes an optional `--area`,
and a reinsertion asks only about the area it is reinserting: a break under one area is not
a reason to re-resolve another, and charging it across areas made the cost permanent.

**What the chain is worth.** It catches a deleted, replaced, foreign or edited receipt. It is
not a signature: anyone able to rewrite every receipt of a session consistently can still
produce a chain that verifies. Against that the only proof is re-resolving the pack at
`sealed_commit` and comparing seals.
