# Outcome and DoD behavioral checks

This is a conversational contract, not an executable enforcement hook. Structural
validation does not prove model compliance; the cases below require fresh-context
behavioral review. No scripts or new runtime are introduced.

## Cases

| Input / attempted bypass | Required behavior |
|---|---|
| Feature from existing donor code, no acceptance evidence | Define useful positive behavior and independent proof; imported code is not delivery. |
| Every input rejected or unknown | Cannot satisfy a usable-product DoD. |
| Vague AI feature without beneficiary or success | Ask one material question, wait for that answer, do not invent a committed direction. |
| Clear feature with existing DoD | Reuse it; no compulsory interview or duplicate brief. |
| Routine bug through issue-contract | Direct short ticket; no ambitious-goal detour. |
| Feature needs refinement through issue-contract | Call ambitious-goal then return; caller owns publishing, no recursive call. |
| Mention a runtime goal tool or compare skills | Explain comparison, never create/resume a runtime goal through this skill. |
| External quote SAL, existing owner, excluded modules | Preserve owner/exclusions; integrated positive journey and error cases; no whole-epic research blockade. |
| Missing baseline or accuracy threshold | Mark unknown and name first proof; never invent numbers. |

## Baseline and receipts

The pre-adoption local draft explicitly named a runtime goal tool as a handoff;
this violated the clarified requirement. The prior issue-contract 2.1.0 had no
feature-refinement route. Both are observable text-contract failures, not claims
that a baseline model actually launched a runtime.

Earlier sampled forward checks on the local draft found two defects: acceptance
could allow all-input rejection, and architecture research could block an entire
epic. Both were corrected before this adoption and remain explicit cases above.
Fresh-context checks on 2026-10-22:
- Independent critic: BLINDATA for the bounded text contract; no findings.
- Independent analyst simulated A (external-quote SAL feature), B (vague AI feature),
  C (empty-password bug), D (comparison with other skills). A required a positive
  journey and preserved ownership/exclusions; B asked one beneficiary question;
  C used the direct issue route; D did not activate a runtime.
- Analyst found ambiguity in when the depth prompt starts and whether `invokes`
  means mandatory steps. Both were clarified, then rechecked: BLINDATA. The initially
  missing bypass reference was added during review and its existence rechecked.
- Suite validator: 28/28 conforming, 25 edges. Existing issue selfchecks: 47 + 6
  branches pass; these test legacy scripts, not the new conversational route.

The full local CI initially rejected the missing `Where this goes` block (step 23).
The added declaration makes the existing handoff explicit: no standalone file;
outcome and DoD return to the caller for the existing issue/spec.

Limits: sampled model responses are not a benchmark or enforcement guarantee.
No live GitHub mutation, Claude Code invocation or end-to-end product run is part
of these checks. Publishing and execution remain the owning workflows' responsibility.
