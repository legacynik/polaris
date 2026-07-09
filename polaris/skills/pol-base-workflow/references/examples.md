# Worked examples

Concrete walkthroughs of the method. Read when you want a model to copy.

## Example A — a feature, end-to-end

**Task:** add email validation to the signup form.

1. **Understand** — code-graph the signup form + where submit is handled; the
   validation belongs in the domain (pure), not the component.
2. **Spec** — happy: valid email passes. Errors: no `@`, no domain, no local part →
   inline error that clears on fix; form can't submit while invalid. Fallback: if
   the validator throws, block submit (fail-closed) and log. Clean-arch: a pure
   `isValidEmail(email)` in domain, the component only renders the result.
3. **Build (TDD)** — RED first:

   ```markdown
   ### Test Cases
   | Input | Expected | Notes |
   | user@example.com | valid | standard |
   | user@sub.example.com | valid | subdomain |
   | notanemail | invalid | no @ |
   | user@ | invalid | no domain |
   | @example.com | invalid | no local part |
   ```
   5 tests → all fail (RED) → implement `isValidEmail` (≤20 lines) → all pass (GREEN).
4. **Verify** — VALIDATE: `lint && typecheck && test --coverage` (≥80%). Fresh-eyes
   review on the regex (the classic place to be subtly wrong). Real test: type a bad
   email in staging, see the inline error.

## Example B — a bug, with durability

**Bug:** the nightly batch crashes; the error log shows an empty message.

1. **Diagnose the gap** — the existing tests pass, so they never exercised the
   path that throws. The real cause: an external SDK raises a `ValueError` on a
   malformed response that the guard didn't catch.
2. **RED** — a test feeding the malformed response → reproduces the crash, fails.
3. **GREEN** — fix. But **don't patch the instance**: the same batch already came
   back twice for different exception types. Root-fix the boundary: a guard around
   the SDK call that fails soft for the whole **failure class** (network / timeout /
   parse / null), not just this one `ValueError`. Add a fail-first eval covering the
   class so it can't recur.
4. **VALIDATE** — full suite (no regression) + lint + typecheck. Mark the error log
   resolved with the PR link.

> The tell that you patched instead of root-fixed: **the same file/area keeps
> coming back for bugs**. When it does, fix the mechanism, not the next symptom.
