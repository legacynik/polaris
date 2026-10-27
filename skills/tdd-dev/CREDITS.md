# Credits

- The interface-as-test-surface diagnostic: `codebase-design` from mattpocock/skills (pinned `49dd158`).
- The three laws of TDD, the volatility rule for ports and the humble object: Robert C. Martin,
  *Clean Architecture* and his writing on test-driven development, paraphrased.
- `references/writing-tests.md` absorbs, rewritten and merged, material from three MIT-licensed
  sources: Jesse Vincent, superpowers (`test-driven-development`, `writing-good-tests.md`: name the
  break, no change detectors, the mock earns no assertions, mock at the right level, the mutation
  check); Addy Osmani, agent-skills (`test-driven-development` and `references/testing-patterns.md`:
  test sizes, state over interactions, DAMP over DRY, Arrange-Act-Assert, the double preference
  order, query by role); Matt Pocock, skills (`tdd`, `tests.md` and `mocking.md`: tautological
  tests, mock at system boundaries, dependency injection, SDK-style interfaces).
- The purpose of unit tests (design, not regression catching), configuration is not a unit, one
  behaviour asserted once, no shared preconditions and subject-scenario-result names: Steve
  Sanderson, "Writing Great Unit Tests: Best and Worst Practices" (2009,
  blog.stevensanderson.com; the copy the founder shared is gist `vadymhimself/763e96dd8495bb77325efd082e63c9f5`),
  paraphrased in the first section of `SKILL.md` and in `references/writing-tests.md`.
