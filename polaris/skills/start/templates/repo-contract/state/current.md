Updated: YYYY-MM-DD — @<login>

## Active Priorities

1. <the work that comes first — this is the order of the day, not an archive>

## Open

- `<branch>` (<repo>) — <state in one line> · since YYYY-MM-DD

## Recent Context

<!-- Last 5 session summaries, newest first -->
<!-- Written by /end only — /update never touches this section -->

---
*Contract — this file is the CURRENT state: it is overwritten, never stacked. ONE `Updated:` line,
date and owner only. `/update` adds and flags one line per thread and removes only what the tracker
proves closed; `/end` is the only command that closes by judgment. The history lives in `team/<login>/sessions/`, never here.*

*Section names — the three headings above ARE the contract, and the package reads them from one
registry. A heading may QUALIFY one of them with a SPACE and then a separator — a dash, a middot, a
parenthesis, a colon — so `## Open — thread vivi` is the `## Open` section, while a glued separator
or another word is not (`## Open-source backlog` and `## Active Priorities` are their own sections).
Every script the package ships reads that one registry, so `/update`, `/start`, `plan-week` and
`/end` can never disagree about which section a heading names. A renamed or translated heading
is a different contract: `/start` reports it as `SECTIONS_MISSING`, and `/update` refuses with exit
2 and leaves the file byte-identical rather than inventing a place to write.*
