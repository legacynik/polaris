# Execution — exact commands & formats

Load this when you need the copy-pasteable detail behind the method in `SKILL.md`.

## RED / GREEN / VALIDATE per stack

**Node.js / TypeScript**
```bash
# RED — run tests, expect failures
npm test -- --grep "todo-description"
# GREEN — run tests, expect pass
npm test -- --grep "todo-description"
# VALIDATE — full quality check
npm run lint && npm run typecheck && npm test -- --coverage
```

**Python**
```bash
pytest -k "todo_description" -v                 # RED (fail) → GREEN (pass)
ruff check . && mypy . && pytest --cov --cov-fail-under=80   # VALIDATE
```

**React / Next.js**
```bash
npm test -- --testPathPattern="ComponentName"   # RED → GREEN
npm run lint && npm run typecheck && npm test -- --coverage --watchAll=false  # VALIDATE
```

**Blocking conditions — never mark done if:** tests weren't written first · tests
didn't fail initially (invalid tests) · any test failing · linter errors · type
errors · coverage dropped below threshold.

## Atomic todo format

Work is tracked as atomic, testable units. If larger than "M", break it down.

```markdown
## [TODO-001] Short descriptive title
**Status:** pending | in-progress | blocked | done
**Priority:** high | medium | low   **Estimate:** XS | S | M | L | XL

### Description
One paragraph: what needs to be done.

### Acceptance Criteria
- [ ] Specific, measurable criterion 1
- [ ] Specific, measurable criterion 2

### Validation
- Manual: [steps]   · Automated: [test file/command]

### Test Cases
| Input | Expected Output | Notes |
|-------|-----------------|-------|

### Dependencies
- Depends on: [TODO-xxx]   · Blocks: [TODO-yyy]

### TDD Execution Log
| Phase | Command | Result | Timestamp |
|-------|---------|--------|-----------|
| RED | `[test cmd]` | all fail ✓ | - |
| GREEN | `[test cmd]` | all pass ✓ | - |
| VALIDATE | `[lint && typecheck && test --coverage]` | pass, N% ✓ | - |
| COMPLETE | moved to completed.md | ✓ | - |
```

## Bug-report format

When a bug is reported, never jump to the fix — diagnose the test gap first.

```markdown
## [BUG-001] Short description
**Status:** pending   **Priority:** high
**Reported:** [reproduction steps]

### Reproduction Steps
1. … 2. … 3. Observe: [wrong] · Expected: [right]

### Test Gap Analysis
- Existing coverage: [files]  · Gap: [what tests missed]  · New test: [describe]

### Test Cases for Bug
| Input | Current (Bug) | Expected (Fixed) |
|-------|---------------|------------------|

### TDD Execution Log
| Phase | Command | Result |
|-------|---------|--------|
| DIAGNOSE | `[full suite]` | all pass (gap!) |
| RED | `[grep bug]` | 1 fail ✓ |
| GREEN | `[grep bug]` | 1 pass ✓ |
| VALIDATE | `[lint && typecheck && full suite --coverage]` | pass ✓ |
```
