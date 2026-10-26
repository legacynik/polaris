# PR title and body template

Read by `pr` step 4. The checker (`scripts/controlla_pr.py`) reads these English headings and
their Italian twins (`In breve`, `Decisione richiesta`, `Criteri delle issue`, `Cosa cambia`,
`Decisioni`, `Prove`, `Cosa resta aperto`, `Rischio del merge`) alike.

## Title

Conventional Commits, matching `git log`, naming the outcome:
`fix(checkout): «Cancel» closes at one click with the list open`. Squash-merge makes the title
the commit; a contract or API break carries `!`.

## Body

```markdown
## In short

<2-3 plain sentences: what changes for whoever uses the product>

**Decision:** <merge / not yet> · <what must happen first, in order>

| Check | Result |
|---|---|
| Issues | #<n> <k>/<k> criteria ✅ · #<m> <j>/<l> (2 ❌ → #<new>) |
| Real-test | <verdict> · <environment> · receipt on `<served sha>` (when it is not the head: head `<head sha>`, <n> commits after) · <who attacked it> |
| CI | <green/red> · tests seen red first: <count> |
| Door · radius | <one-way/two-way> · <one word> |
| Open | <count, or «nothing»> |

Closes #<n>
Refs #<m>

## Issue criteria

### #<n> <issue title>

| # | Criterion (from the issue) | Result | Proof |
|---|---|---|---|
| 1 | <criterion, shortened, same order as the issue> | ✅ | <link: screenshot / test / receipt line> |

**Every criterion of #<n> is closed.** (or: **Open: 3, 5 → #<new>**)

## What changes

<the visual, domain words; legend of code names under it>

| Piece | What it does |
|---|---|
| <name in the code> | <one plain sentence> |

## Decisions

- **Decision record:** <path §section> · <followed / changed> (or «no decision record governs these files»)
- **Choice:** <X> over <Y>, because <reason>

## Proof

Tried live: <yes, where and on which SHA / no, why>

**1. <what this step does, what to look at>**

<img src="<link>" width="640">

**2. <next step>**

<img src="<link>" width="640">

- **Before → after:** <output or the test that failed and now passes, in pseudocode>
- **Real-test:** <environment, served SHA, who attacked it, what it found, what was fixed, verdict>

## Still open

- <gap> · <who closes it> · <when> (or «nothing»)

## Merge risk

**Door:** <one-way or two-way> · **Radius:** <one word>

<consequences; the release order when it matters; what a production deploy carries besides this PR>
```

