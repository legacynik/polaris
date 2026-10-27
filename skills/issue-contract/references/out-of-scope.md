# The `.out-of-scope/` knowledge base

Compressed from the `triage` donor. Persistent record of rejected **enhancement** requests, one
file per **concept** (not per issue) — kept for two reasons: institutional memory (why it was
rejected, so the reasoning survives issue closure) and dedup (a new issue matching a prior
rejection surfaces the old decision instead of re-litigating it).

## Structure

```
.out-of-scope/
├── dark-mode.md
└── plugin-system.md
```
Kebab-case, one concept per file, name recognizable without opening it.

## File format

Readable prose, not a database row — enough for a stranger to understand the reasoning.

```markdown
# Dark Mode
This project does not support dark mode or user-facing theming.

## Why this is out of scope
[the actual technical/scope/strategic reason — not "we don't want this", but WHY: a
constraint, a scope boundary, a decision already made]

## Prior requests
- #42 — "Add dark mode support"
- #87 — "Night theme for accessibility"
```
Required fields the gate checks for: a `**Decision:**`-shaped line (or equivalent, e.g. the `#`
heading + a why-section) and a `**Prior requests:**` list. Reason must be durable — never "we're
too busy right now" (that's a deferral, not a rejection).

## When to check

Step 1 of every triage pass ("gather context"): read all `.out-of-scope/*.md`. Match by concept
similarity, not keyword — "night theme" matches `dark-mode.md`. Surface a match: "similar to
`dark-mode.md`, rejected before because [reason] — still feel the same way?" Maintainer can
**confirm** (append to Prior requests, close), **reconsider** (delete/update the file, proceed
normal triage), or **disagree** (related but distinct, proceed normal triage).

## When to write — and when NOT to

Only when an **enhancement** (issue or PR) is *rejected* as `wontfix`. **Never** when something is
closed `wontfix` because it's **already implemented** — that's a built feature, not a rejection;
recording it here poisons the dedup checks with false rejections (`transition_gate.py` refuses
this combination outright — see [bypass-test-update.md](bypass-test-update.md)). For an already-implemented
close, the comment points to where the feature lives instead.

Flow: maintainer decides out of scope → check for a matching file → append if it exists, else
create one with concept name + decision + reason + first prior request → comment on the issue
linking it → close `wontfix`.

## Updating or removing

Maintainer changes their mind → delete the file. No need to reopen old issues (historical
records); the new issue that triggered the reconsideration goes through normal triage.
