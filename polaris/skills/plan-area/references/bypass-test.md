# Bypass-test — must FAIL

Ways to get a feature step closed, or a plan closed, without the work the gate requires. Each one
must exit non-zero. The automated form of every case is in `tests/test_feature_gate.py` and
`tests/test_plan_close.py` (real `bd` on a throwaway db; sibling skills stubbed).

| # | Attempt | Expected |
|---|---|---|
| 1 | `check --stage plan` on a plan with empty `area:`, no DoD line, `status: proposed`, empty `tests:`, outside `open/`, or no `Beads epic:` | exit 1, the missing artifact named |
| 2 | `close` the `critic` step while `plan` is still open | exit 1 `blocked by open step(s)` — the gate's own check, before bd's |
| 3 | `bd dep remove <phase 1> <critic>`, then `close` any step of the molecule | exit 1 `missing edge: …` — `edges` names the phase |
| 4 | `close --step <critic>` with a report carrying a `critical` or `important` finding, or one `critic_gate.py` rejects | exit 1 |
| 5 | `close --step <phase>` with red tests or an open finding with `blocks:<phase>` | exit 1 |
| 6 | `close --step <task>` through the gate | exit 2 — tasks are plain beads; the phase is the gate |
| 7 | `check --stage implement` while a phase bead is open | exit 1 |
| 8 | `check --stage ship` on an open PR, or a merged PR with no real-test receipt for its head | exit 1 |
| 9 | `pour` with `.beads/formulas/feature.formula.toml` edited (a `needs` removed) | exit 1 `formula drift` |
| 10 | `pour` twice on the same plan | exit 1 `already poured` |
| 11 | a second actor `claim`s a step whose lease is live | exit 1 |
| 12 | `plan_close.py --merged` before the canonical doc names the plan | exit 1, nothing moved |
| 13 | `plan_close.py --merged` with a DEC in Links whose probe fails (NOT_DONE) | exit 1, DEC still `accepted`, nothing moved |
| 14 | `plan_close.py --merged` while `implement` is open (a skipped stage) | exit 1 `a skipped stage`, nothing promoted |
| 15 | `feature_gate.py finish --merged` on a molecule with an open step | exit 1 — a merge burns a complete molecule only |

What the gate does NOT block, declared: a person running `bd close <phase>` by hand (bd has no
judge hook — the rule lives in `references/beads.md` and the edge diff catches a removed edge,
not a hand close); an ADDED `blocks` edge (the diff looks for missing edges only, so an extra
edge that reorders steps passes `edges` — it can delay a step, never skip one); a metadata edit on a bead (`bd update --metadata`) that renames its step; a
`tests:` command that tests nothing. The crash proof (pour + lease, `kill -9`, reclaim after the
5-min TTL) needs 6 minutes of wall clock and runs by hand: the transcript is in the PR that
introduced this skill.
