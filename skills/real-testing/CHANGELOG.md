# Changelog — real-testing

## 4.2.1 — 2026-10-26

- The `per-phase local` mode is renamed `local`: real-testing never gates a Beads phase (4.2.0); the local run is the PR's own check.

## 4.2.0 — 2026-10-26

- No longer a phase gate: `feature_gate.py` closes a Beads phase on green tests; real-testing runs
  once, on the PR (merge mode). Per-phase mode stays, only when asked; dropped from the trigger. Founder: per-phase gates on Beads were
  rigid and made small phases drift (operating model §10).

## 4.1.1 — 2026-10-25

- Public-package clean (C5): `references/teardown.md`, one eval prompt and the CHANGELOG name "a product repo" instead of the real one.

## 4.1.0 — 2026-10-25

- New step 7, **Close what you opened**: lent test data goes back through the repo's release command with its residue report in the receipt; a repo with a pool gets no throwaway tenants; the validation document is committed on the PR branch and the PR stays draft; own worktrees, servers and browsers removed, leftovers listed. Founder 2026-10-25 («non deve lasciare schifezze… finisce con commit e pr bozza sempre»), after the #2186 real-test left 4 sandbox tenants and two worktrees behind. The product repo's pool is `backend/scripts/ops/tenant_pool.py`.
- Version bump: minor, from 4.0.4.

## 4.0.4 — 2026-10-25

- Follows the rename `implement` → `implement-plan` (references, `invoked-by`, eval tuples). Text only.
- Version bump: patch, from 4.0.3.

## 4.0.3 — 2026-10-25

- Output ends with a **Next:** line: the next skill, or STOP with who decides and the options to offer. Text only.
- Version bump: patch, from 4.0.2.

## 4.0.2 — 2026-10-25

- `invoked-by` gains `implement`: its phase gate runs the per-phase mode. No behaviour change.
- Version bump: patch, from 4.0.1.

## 4.0.1 — 2026-10-25

- Per-phase rewrite beads carry `--parent <epic>`: the feature gate's own blocked-step check and `bd ready --mol` only see beads in the epic's molecule (measured by B2 on the merged gate); never `--parent <phase>`, since bd keeps one dependency per pair.

## 4.0.0 — 2026-10-24

- Major: three modes. **Per-phase local** (behaviour against the phase DoD on this machine, fresh breaker; a misaligned DoD line becomes a rewrite bead blocking the phase; a local receipt in the merge format, bound to the phase diff with `--base <phase-start> --head HEAD`, is required and read by the feature gate). **Merge** (unchanged: staging, receipt `.real-test/verdicts/<hash>.json` bound to the tree, PR comment marker). **Production check** (the customer journey against production with no diff, read from the product repo's `real_test:` block plus a journey doc; replaces the per-product "test the app" skills such as a product-specific realtest skill; removing that skill and routing its trigger to this mode is unit B10's, in the agent box and product repos).
- Logged-in browser profiles: `real_test.browser_profile` and `real_test.account`; browser-harness over CDP on that profile; agents never type a password; an expired session stops the run and asks a human to log in again.
- Receipt format, verdict values, JSON keys and the PR marker are unchanged: other repos' CI and the copy vendored in hermes-agent-os read them.
- 60-line form; the merge walk moved unchanged to `references/merge.md`, the new modes in `references/modes.md`. The harness-neutral breaker step of #592 kept. Scripts' comments and messages translated to English (no behaviour change; the installed-hook marker line stays as is because installed hooks are detected by it).
- Description names its hard deps (git, python3, gh, bd). Production-check defects are handed to `issue-contract` by the caller, not declared as an `invokes` edge: issue-contract → bugfix → real-testing would close a cycle.
- Evals: 5 new trigger cases; checks c6–c8 rewritten for the English body, c9–c10 behavioural cases for the new modes.
- Plan: operating model §3, §10, §11 (DEC-polaris-operating-model-001), Wave B unit B4b.

## 3.2.4 — 2026-10-24

- Dropped `flow-cli` from `invoked-by`: that skill moved to `skills-suite/_archived/` (unused since 2026-08-09, cut approved 2026-10-24).
