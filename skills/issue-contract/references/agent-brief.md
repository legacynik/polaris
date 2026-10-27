# Writing agent briefs

Compressed from the `triage` donor (kept: every principle, the template, one full worked example
each way; cut: 3 of the 4 duplicate worked examples — same lesson, less paper).

Posted when an item moves to `ready-for-agent` (or `ready-for-human`, same shape, plus why it
can't be delegated). It's the contract an AFK agent works from — the original body/discussion is
context, the brief is the spec.

## Principles

**Durability over precision.** The item may sit for days/weeks; the codebase will drift. Describe
interfaces, types, behavioral contracts, specific signatures/config shapes to look for. Never
reference file paths or line numbers — they go stale.

**Behavioral, not procedural.** Say what the system should do, not how to implement it — the
agent explores fresh and decides its own implementation.
- Good: "`SkillConfig` should accept an optional `schedule: CronExpression` field"
- Bad: "Open `src/types/skill.ts`, add a field on line 42"

**Complete acceptance criteria.** Every criterion concrete, testable, independently verifiable.
- Good: "`gh issue list --label needs-triage` returns issues past initial classification"
- Bad: "Triage should work correctly"

**Explicit scope boundaries.** State what's out of scope, so the agent doesn't gold-plate.

## Template

```markdown
## Agent Brief
**Category:** bug / enhancement
**Summary:** one line

**Current behavior:** what happens now (bug: the broken behavior; enhancement: the status quo)
**Desired behavior:** what should happen after, specific about edge cases/errors

**Key interfaces:**
- `TypeName` — what changes and why
- `functionName()` — current return vs desired
- Config shape — new options, if any

**Acceptance criteria:**
- [ ] specific, testable criterion

**Out of scope:**
- thing that should NOT be touched here
```

## Worked example (bug)

```markdown
**Category:** bug
**Summary:** Skill description truncation drops mid-word

**Current behavior:** descriptions over 1024 chars are cut at exactly 1024, mid-word
("...wants to confi").
**Desired behavior:** truncate at the last word boundary before 1024 and append "...".

**Key interfaces:**
- `SkillMetadata.description` — no type change; the logic that populates it must respect
  word boundaries.

**Acceptance criteria:**
- [ ] under 1024 chars: unchanged
- [ ] over 1024 chars: truncated at the last word boundary + "..."
- [ ] total length incl. "..." never exceeds 1024

**Out of scope:** changing the 1024 limit itself, multi-line descriptions.
```

For a PR, "Current behavior" describes the diff's state, and the brief asks the agent to finish or
fix it — not build from scratch. Everything else (interfaces, acceptance criteria, out-of-scope)
works the same.

## Bad brief (what NOT to do)

```markdown
**Summary:** Fix the triage bug
**What to do:** The triage thing is broken. Look at the main file, line 150.
**Files:** src/triage/handler.ts (line 150), src/types.ts (line 42)
```
No category, vague description, stale line references, no acceptance criteria, no scope, no
current-vs-desired. Every one of these is the reason the durable-brief discipline exists.
