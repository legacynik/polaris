# Work tracking

Work has two homes and nothing is copied between them.

| Home | What goes there | Who writes it |
|---|---|---|
| **GitHub issue** | deliveries a person schedules or approves, or a customer sees: few, organised, readable by a human | only `issue-contract` |
| **Beads** (`bd`) | everything operational: plan phases and tasks, Tiny work, bugs found while testing, review and real-test findings, follow-ups, spikes, ideas waiting for an area slot | `plan-area`, `implement-plan`, the gates, the loop, and `issue-contract` when it routes |

## The filter

`issue-contract` is the only door to the tracker. It opens a GitHub issue only when **all** of
these hold; otherwise it creates a bead and says why in one line.

1. A person must schedule or approve the work.
2. It will not be done inside the current pull request or phase.
3. It says how to prove it is done ("Come si prova" in Italian repositories, "How to test" in
   English ones) and it names an area.
4. No open issue already covers it.

A bead that grows into a delivery is promoted through the same door: the issue is created and the
bead keeps `external_ref: gh#N`.

## Why Beads for operational work

- **Real dependencies.** `blocks` edges between beads; `bd ready` lists only what nothing blocks.
- **Claims and leases.** A worker claims a bead; a crashed worker's lease expires and the work
  becomes ready again.
- **Gated formulas.** A plan's phases are poured from a formula, and `feature_gate.py` refuses to
  close a phase whose tests fail or that an open finding blocks.
- **Cleanup at the end.** At merge the epic is burned and the PR comment is the record. An abandoned
  epic leaves one closed `kind:digest` bead first.

Labels categorise the noise: `kind:` (phase, stage, task, finding, idea, followup, digest), `src:` (who found it)
and `area:`.

## What is not allowed

- **A mirror between GitHub and Beads**, in either direction. A previous trial imported every
  GitHub issue into Beads on a timer and produced hundreds of beads nobody read.
- **Markdown checklists as task lists.** A plan's tasks live in its epic, not in the plan file.
- **Closing a phase bead by hand** (`bd close`) or removing a `blocks` edge to unblock it. Phases
  close through `feature_gate.py close --step <phase>`.

## Ownership of fields

GitHub owns an issue's title, priority and labels. Beads owns phase state. Neither reads the other
to stay in sync; a finding that belongs to a delivery carries `gh#N` (or the plan name) in its own
description, because squashing and burning an epic deletes its edges.
