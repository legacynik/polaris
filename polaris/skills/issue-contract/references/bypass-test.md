---
title: bypass-test — issue-contract
description: The cases that must fail if the AFK decision can be skipped. Each was observed or reproduced before the fix; the executed proof is tests/test_afk_label.py.
status: active
---

# Bypass cases — the AFK label

The defect: work the owner asked to keep for a person was filed with no human label, so an
unattended agent could claim it. Three ways it happened, each now refused by
`scripts/afk_label.py` and proved by `tests/test_afk_label.py`.

## B1 — the decision was never made

`fails_before:` issue-contract 2.2.1. The only AFK line sat under "When NOT to use" and step 3
said "infer the AFK label from repository conventions" with no label name and no completion
criterion. Nothing read the created issue back.

After: step 3 decides person or agent before the ticket is written, and "Before returning" runs
`afk_label.py verify`, which exits 1 when the issue lacks the label.

```bash
printf '[{"name":"afk:human"},{"name":"afk:eligible"}]' > labels.json
printf '{"labels":[{"name":"bug"}]}' > issue.json
python3 scripts/afk_label.py verify --human yes --issue issue.json --labels labels.json; echo "exit=$?"
# expected: FAIL issue lacks 'afk:human': add it · exit=1
```

## B2 — look-alike labels, wrong one chosen

A repository can hold `afk:human`, `ready-for-human`, `afk:eligible` and `agent-ready` at once.
Inferring from conventions picked whichever the model saw first. After: the product
repository's `_polaris/config.yml` (`tracker.afk_human`, `tracker.afk_agent`) names them; without
it a fixed order applies; a configured label the repository lacks refuses rather than
substituting a look-alike.

```bash
mkdir -p _polaris && printf 'tracker:\n  afk_human: needs-a-person\n' > _polaris/config.yml
python3 scripts/afk_label.py pick --human yes --labels labels.json; echo "exit=$?"
# expected: names needs-a-person on stderr · exit=2
```

## B3 — the label did not exist, so it was dropped

`gh issue create --label afk:human` fails on a repository without that label, and the retry
went out without it. After: `pick` exits 2 naming the label to create, and the skill files
nothing until it exists.

```bash
printf '[{"name":"bug"}]' > labels.json && rm -rf _polaris
python3 scripts/afk_label.py pick --human yes --labels labels.json; echo "exit=$?"
# expected: "create one (gh label create afk:human)" on stderr · exit=2
```

## Not closed — declared

The person-or-agent judgement in step 3 is the model's; the script makes the label exact and
checks it landed, but cannot tell that a request meant "leave it to me".
