# `_polaris/` — Polaris Team OS root

Team-shared operating state for this repository: who owns which outcome, weekly plans and
reports, session handoffs, durable decisions and lessons. Markdown + git, no extra tooling —
written and read by the polaris-team-os commands (`/start`, `/update`, `/end`, `/plan-week`,
`/report`) and recalled by `polmem`.

## Structure (the contract)

| Path | What it is | Who writes it |
|---|---|---|
| `config.yml` | tracker + contributor roster (exact GitHub logins) | repo owner |
| `decisions.md` | durable decisions — append-only, newest on top | anyone, via `/end` proposal + human confirm |
| `lessons.md` | durable lessons — a real mistake + the rule that prevents it | anyone, via `/end` proposal + human confirm |
| `team/<login>/` | **your space** — created by your own first `/start` | only you |
| `team/<login>/profile.yml` | capacity, assignment mode, preferred/excluded areas | you |
| `team/<login>/weeks/YYYY-Www.md` | your weekly focus — yours to execute, not a permission request | you, via `/plan-week` |
| `team/<login>/reports/YYYY-Www.md` | weekly report — planned versus actual, with evidence | you, via `/report` |
| `team/<login>/sessions/` | daily session handoffs, committed shared history | you, via `/update` and `/end` |
| `team/<login>/handoff/` | optional: rich multi-session handoff docs | you |
| `state/current.md` | ephemeral live pointer — **gitignored**, per checkout | whoever sits at the checkout |

## Rules

- **One root: `_polaris/`.** Never `polaris/`, never both.
- Your folder name and the `github:` field are your **exact GitHub login**
  (`gh api user --jq .login`, case-sensitive). A nickname silently breaks every `gh` evidence query.
- **Never create another contributor's path** — everyone's own `/start` creates theirs.
- **Never write in someone else's `team/` space** — their path, their plan, their session log.
- **Your plan does not wait for a signature.** You own the outcome: decide and proceed on bounded,
  reversible work, recording `Decision / Why / Risk / Next step` as you go. The lead reads and may
  reorder your focus — that is priority alignment, not permission, and silence is not a block. Only
  **red** work waits for a **named** approver: access/RLS/auth expansion, personal-data
  use/retention/deletion, new processor/vendor, irreversible migration, legal/customer commitment,
  audited production promotion, or a material change of outcome/architecture. If this repo ships a
  workflow charter (`profile.yml` → `workflow:`), that charter's boundaries win.
- GitHub/Linear stays the source of execution truth. These files record ownership, proof and
  handoffs — they are not a second issue tracker.
- `polmem recall` before assuming context; a recalled page is assumed context to verify,
  never proof of what is true now.

## Privacy boundaries

- ❌ No personal capacity/time allocations of other people, no mentor/investor/pricing terms,
  no customer secrets — those live in the founder's personal vault, never in a product repo.
- ❌ No evaluative observations about teammates in files or commit messages — git log is permanent;
  keep commit messages neutral.
- ✅ Do put here: plans, reports, session handoffs, decisions, lessons, your own commitments.

Anything else in this directory is repo-specific legacy or archive. If a file has no reason to
exist, propose removing it — every file here must earn its place.
