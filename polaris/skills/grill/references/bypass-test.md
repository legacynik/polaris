# Bypass-test — what grill must catch, and what fails without it

## The baseline (`fails_before`)

Before 2.0.0, `grill` was a read-only interview that ended with a handoff in chat. Nothing it
produced survived the session in the repository, and nothing gave the work a size. The operating
model (2026-10-24, §1) measured what that left behind:

- Discovery happened as audits, not as a phase: learning-loop accumulated 30 audits and 40
  validation files in six weeks; one product epic had 4 plans in 6 weeks.
- About 60% of plans carry no `status:`; one product repo holds 341 plans, 24 of 27 "active" untouched for
  more than 21 days.
- Prototype ran in about 1.5% of sessions: no step named an assumption and the test that settles it.

## The tests that must fail without the gates

| # | Bypass | What catches it |
|---|---|---|
| 1 | The plan file is written without `status:` or with a status outside the lifecycle | `tests/test_grill.py` runs the vault's `check_plan_files.py` on the skeleton; the checker reports `status-missing` / `status-invalid` |
| 2 | A second plan opens in an area whose `plans/open/` is taken | `check_plan_files.py` `open-crowded`; step 1 stops before writing |
| 3 | The skeleton drifts from the nine sections of operating model §5 | `tests/test_grill.py::test_skeleton_carries_the_nine_sections_in_order` |
| 4 | A Tiny or Bug request gets a plan file | `eval/checks.json` c3 |
| 5 | Several questions in one turn, or a question with no recommended default | `eval/checks.json` c2 |
| 6 | An assumption with no way to test it | `eval/checks.json` c4 |
| 7 | grill implements, or opens an issue, branch or pull request | `eval/checks.json` c5 |
