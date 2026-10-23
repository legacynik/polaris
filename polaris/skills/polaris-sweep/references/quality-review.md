# Quality review (Phase 3a)

The reviewer reads the diff and the intent; never the implementing session's history.

## Inputs

- What the PR says it does (title, body) and the originating issue when there is one.
- The range: `git diff --stat <base>..<head>` and `git diff <base>..<head>`.

Read-only on the checkout: inspect with `git show`, `git diff`, `git log`; another revision goes in
a separate temporary worktree. Review the whole range yourself, in several passes if it is large,
and say so in the output.

## Checks — each gets a verdict

- **Intent:** the diff does what the PR claims; deviations are flagged as deliberate or not; nothing
  claimed is missing. Behaviour the intent is silent on is judged by what a reasonable user expects.
- **Code:** separation of concerns, error handling, types where the language has them, duplication
  without premature abstraction, edge cases.
- **Design:** decisions fit the surrounding code, scale and performance are reasonable, the change
  integrates cleanly.
- **Tests:** they exercise real behaviour rather than mocks, cover the edge cases, include an
  integration test where the risk sits, and pass.
- **Release:** a schema change carries its migration strategy, compatibility is preserved, docs that
  describe the changed behaviour are updated, no obvious bug remains.

Before the verdict, list every behaviour you considered and set aside as out of scope, one line
each with the reason; an empty list means nothing was set aside.

## Output

```
### Strengths
- <specific, with file:line>
### Findings
#### Critical  — bugs, security holes, data-loss risk, broken functionality
#### High      — design problems, missing behaviour, weak error handling, test gaps
#### Minor     — style, small optimisations, doc polish
  each: file:line · what is wrong · why it matters · the fix when not obvious
### Set aside
### Verdict: approve | approve-with-minor | request-changes — <1-2 sentence reason>
```

Severity is the real one: a nit is never Critical. A Critical or an unfixed High means
`request-changes`. Every finding names code you actually read.
