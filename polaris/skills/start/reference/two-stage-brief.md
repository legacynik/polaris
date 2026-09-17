# The two-stage brief — how to read it

`brief_signals.py` returns this only where the host repository carries the typed backbone
(polaris-os#405). It replaces the single line `PACK=CTX-<id>`, which polaris-os#326 measured:
an opaque id is an id the agent ignores, so the resolver was invisible to the session it
exists for, and the founder kept being the index of his own repository out loud.

Read it once, in order, and act on it. Do not summarise it away.

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
