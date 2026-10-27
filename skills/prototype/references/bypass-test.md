# Bypass-test — what prototype must catch, and what fails without it

## The baseline (`fails_before`)

The donor (`mattpocock/skills` prototype, installed in `~/.agents/skills`) ran in 12 of about 798
sessions since 2026-08-09 (operating model §1, from `~/.claude/skill-usage.jsonl`). Its capture
step folded the validated decision "into the real code" and left the answer "in the issue or a
commit": nothing tied a spike to a plan assumption, and nothing put the answer where the plan is
read. Two questions could share one prototype, and a spike that answered nothing had no exit.

## The tests that must fail without the gates

| # | Bypass | What catches it |
|---|---|---|
| 1 | The skill is not in the suite, or breaks its form | `tests/test_prototype.py::test_passes_the_suite_gate` |
| 2 | The upstream and its license are not credited | `tests/test_prototype.py::test_credits_name_the_upstream_and_its_license` |
| 3 | Code starts before one named question is written | `eval/checks.json` c1 |
| 4 | Spike code reaches main | `eval/checks.json` c2 |
| 5 | The verdict lands anywhere but plan file section 4, or leaves the assumption untouched | `eval/checks.json` c3 |
| 6 | A spike that answered nothing leaves a verdict or a branch behind | `eval/checks.json` c4 |
