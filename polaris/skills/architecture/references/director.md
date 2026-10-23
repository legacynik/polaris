# Director — portable multi-lane execution

Load this leaf only when a run has more than one independent evidence lane or landing packet, a
missing result, background work, or resume. It is a contract over harness-native agents and Git
worktrees, not a new runtime.

## State and receipt

Advance in order and persist the current row in the issue or existing work item, never only in the
transcript:

`route -> intake -> evidence -> reduce -> crux -> commitment -> landing_map -> handoff_and_verify`

Every selected stage returns `closed | blocked | non_observable` plus `reason`, `source_id` and
`source_hash`. `blocked` stops its descendants. `non_observable` is preserved as missing evidence;
it is never zero, clean, absent or majority-completed.

On resume, load the latest sealed receipt cited by the current issue or work item and continue from
the first non-closed stage. When its source hashes still match, do not reopen closed stages, reload
their rule files or mine raw traces. The open stage may inspect only new artifact paths explicitly named
by the current work item. If none are named, preserve its recorded `blocked` or `non_observable`
state and stop; never scan directories for possible arrivals. A missing/stale receipt is `BLOCK`;
the transcript is not a fallback state store.

A receipt matches only when **every** declared source still resolves and its current SHA-256 equals
the sealed `source_hash`; an old Git commit remaining reachable proves history, not freshness. One
mismatch makes the whole receipt stale and the top-level verdict `BLOCK`, never `REPLAN`.
`REPLAN` is reserved for a matching current receipt whose explicit prerequisite, collision boundary
or legacy authority remains open.

## Read-only waves

Declare worker IDs and expected cardinality before dispatch. Each worker receives one bounded axis,
the same snapshot, an output schema and a source seal. Dispatch independent axes with the harness's
native subagents; without them, use `degraded_sequential` and keep the same receipts.

The reducer emits exactly one row per declared worker. Missing results become one
`non_observable` row with the worker ID and reason. It may deduplicate the same mechanism, while
preserving independent convergence as evidence. It must not rerun, infer or silently drop a row.
Worker and packet IDs are opaque: copy each declared ID exactly and never add a role or lane prefix.
Evidence waves leave write-wave selection, deferral and merger-ownership fields empty; their state
is carried by declared cardinality plus the exact worker rows.

For write-wave planning, each packet row records its planning disposition: `closed` when ownership,
collision status and scheduling are resolved, `blocked` when it is deferred or its scope is unknown.
Do not mark a selected packet `non_observable` merely because execution has not started; missing
execution evidence belongs to `handoff_and_verify` and to the later packet receipt, not the landing
map.

## Write waves

Each packet declares `packet_id`, base SHA, exclusive worktree, exact write set, prerequisites and
closure check. Before dispatch, compute intersections across both:

1. declared file/symbol write sets;
2. derived shared surfaces such as generated maps and downstream reports.

Any remaining intersection is a collision. Shared generated surfaces are merger-owned: remove
them from worker write sets before scheduling, and reject a packet that still claims them. They do
not serialize otherwise disjoint packets. When a generated region sits inside an authored file,
remove only that region; the worker still owns the remaining authored body.
A surface is derived only when its deterministic regeneration command is declared; otherwise it is
authored. Select a maximal provably disjoint wave; if several have the same cardinality, choose the
first tuple in declared packet order. Unknown ownership or scope serializes the packets.

The merger accepts a packet only when its receipt exists, its diff is contained in the declared
write set, its base is the inspected SHA or a reviewed descendant, and its closure check passes.
After integrating the wave, the merger alone regenerates shared projections and runs the
repository closure check. Conflict, scope escape, stale base, missing receipt or failed closure is
`REJECT`, never a hand-merged success.

## Stop states

- `PASS`: every selected stage closed and the final closure check was observed on the integrated SHA.
- `REPLAN`: the target remains plausible but a prerequisite probe, collision boundary or legacy
  authority prevents promotion.
- `BLOCK`: missing/unknown/stale/conflicting evidence prevents safe continuation.
- `NOOP`: the public command proved the requested current state without mutation.

Do not report `PASS` beside an open `REPLAN`, `BLOCK` or `non_observable` prerequisite.
