# Form constancy — the slice-0 proof, run 2026-08-18

Spec (plan slice 0): *"3 invocazioni sullo stesso fixture producono lo stesso scheletro di
artefatto."* Three independent Sonnet dispatches, same prompt, no shared state, read-only on
this worktree. Fixture: the real Acme case — quote generation hits the platform's 127s
ceiling; decide sync-edge-plus-heartbeat vs async pipeline (all callers in one repo, deployed
by us, no external consumer).

## Verdict: HOLDS — 3/3 identical skeletons

| Invariant | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Arm routed | architectural decision | architectural decision | architectural decision |
| Fields emitted, in order (`reversibilità → opzioni → costo per opzione → scelta → enforcement → verifica di chiusura → ASSUMED`) | all 7 | all 7 | all 7 |
| Reversibility verdict + which conditions decided it | `OWNED`, a+b+c | `OWNED`, a+b+c | `OWNED`, a+b+c |
| Options MECE (2, heartbeat vs async; third variants explicitly folded or excluded) | yes | yes | yes |
| Pick | B (async), argued least-worst | B, least-worst | B, least-worst |
| Enforcement red-plus-comment, never blocking, AFK carve-out named | yes | yes | yes |
| Closure check declared before work, executed not-by-founder | yes | yes | yes |
| Unclosed claims carried as per-item `ASSUMED` with owner/reason | 3 items | 3 items | 3 items |

All three also converged on the same pivotal `ASSUMED`: whether 127s is a hard execution cap
or an idle timeout — the fact the whole choice pivots on, which none invented an answer for.

## Divergences observed — none of them skeleton, all recorded

1. **Load discipline breach (run 2).** Loaded connascence/three-forces rules beyond the §J
   set the arm's `loads` names. The skeleton held anyway, but this is the exact failure the
   "load only what the step names" line exists to stop → SKILL.md wording hardened in the
   same commit ("never a rule the row does not name, however adjacent").
2. **Census depth varied.** Run 1 ran a real one-pass census on the live product tree
   (24 textual hits → 3 genuine callers) and still marked graph-closure `ASSUMED` (no symbol
   traversal); runs 2–3 took the fixture's caller claim and marked it `ASSUMED`. Correct
   behaviour in all three — the contract routes unverified counts to `ASSUMED` rather than
   forcing a census the run cannot close.
3. **Prose language varied** (1 English, 2 Italian) and run 3 added a title/qualification
   header. Neither is a contract field; record-language follows the vault's decisions/ADR
   voice by declared exception in SKILL.md.

Raw outputs: [`form-constancy-runs/`](form-constancy-runs/) (run1–run3, verbatim). Mechanical field check (run 2026-08-18, zero output = pass):

```bash
for f in run1 run2 run3; do
  for k in reversibilità opzioni "costo per opzione" scelta enforcement "verifica di chiusura" ASSUMED; do
    grep -q "$k" "$f" || echo "$f MISSING $k"
  done
done   # zero output on the three raw records = the table above
```
