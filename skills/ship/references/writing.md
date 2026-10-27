# Writing documents people read

READMEs, docs, plans, PR bodies, ADRs and area READMEs. A reader should get the point from the first
lines and be able to check every claim. `scripts/slop_check.py` catches the mechanical part; the rest
is judgement.

```bash
python3 scripts/slop_check.py $(git diff --name-only origin/<base>...HEAD -- '*.md')
```

Exit 0 clean, 1 findings (file:line and the reason), 2 unreadable. A deliberate exception carries
its reason on the line: `<!-- slop-ok: quoting the vendor's own claim -->`.

## Conclusion first

The first sentence says what the reader needs to know or do. Background comes after.

```text
Before: Over the last weeks we looked into several options for the export job and, after some tests, we decided on a queue.
After:  The export job moves to a queue: it stops timing out on files over 2 GB.
```

## Numbers with source and date

A number without where it came from and when cannot be checked.

```text
Before: The new index is much faster.
After:  p95 lookup fell from 840 ms to 95 ms (staging load test, 2026-03-04, 10k queries).
```

## One name per concept

Pick one word for a thing and keep it. Two names read as two things.

```text
Before: The worker claims a job. Later the runner releases the task.
After:  The worker claims a job. Later the worker releases the job.
```

## Plain words

Write the word a colleague would say aloud.

```text
Before: We leverage the cache to facilitate expedited retrieval.
After:  We read from the cache, so lookups are faster.
```

## Concrete over abstract

Name the case, the file, the value. An abstraction tells the reader nothing to check.

```text
Before: The change improves robustness in edge cases.
After:  An empty CSV no longer crashes the import; it returns "0 rows".
```

## A diagram for any flow

Three or more steps that hand off to each other get a diagram, not a paragraph.

```text
Before: The request goes to the gateway, which checks the token and then forwards it to the billing service, which writes the invoice.
After:  client → gateway (checks token) → billing → invoices table
```

## No filler, no hedging, no restating

Cut words that carry no fact. Say what you know; where you do not know, say "unknown" and how to find out.
Never open a section by announcing it or repeating its heading.

```text
Before: This section describes retries. It's worth noting that retries might potentially help.
After:  Retries: three attempts, 2 s apart; a fourth failure pages the on-call.
```

## Tables only when they compare

A table earns its place when rows share columns a reader compares. One-column or one-row tables are lists.

```text
Before: | Note |  then one row: | The job runs nightly |
After:  The job runs nightly.
```
