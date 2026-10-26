---
name: pr
description: "◇ Polaris — Use when writing, retitling or rewriting a pull request body, before `gh pr create` or `gh pr ready`, so its owner judges it merge-ready on GitHub without reading code: the verdict on top, every issue criterion answered with proof, the smallest visual, before/after evidence and merge risk. Not the merge decision itself. Requires gh and python 3."
version: 1.4.2
user-invocable: true
auto: true
lifecycle: "produces the PR title and body on GitHub, drained by the merge (the squash commit keeps the title, the closed issues keep the links); the local body file is scratch, deleted after publishing"
invokes: []
invoked-by: [ship, babysit, human]
io: "issues the PR touches + real-test receipt and facts + screenshots + governing decision records -> a body that passes scripts/controlla_pr.py, published with gh pr edit; consumed by babysit and by the owner"
status: active
---

# pr

## What it does

Writes the PR title and body so the owner says «merge» or «not yet» from the PR alone. Inverted
pyramid: the verdict, then every criterion of every issue answered with proof, then what changes,
the decisions, the proof, what is open, the risk. Written in the owner's language with the
repository's domain words (`GLOSSARY.md`, else `CONTEXT.md`); a gate that did not run goes under
the merge risk, never marked passed.

## When

- Before `gh pr create` or `gh pr ready`, or when `ship` or `babysit` reach the body step.
- A body the checker refuses, a retitle, or a head that moved since the body was written.

## Steps

1. **Collect.** For each issue the PR touches, `gh issue view <n> --json body,comments` and copy
   every acceptance checkbox in order. Note the head (`gh pr view <n> --json headRefOid`). Gather
   the real-test receipt, screenshots, the decision records governing the changed files and, when
   a production deploy follows, its cargo. *Done when every checkbox is copied and each source is
   in hand or known absent.*
2. **Answer every criterion.** One row per checkbox: ✅ with a proof the owner can open, ❌ with
   the reason. All ✅ → its own `Closes #<n>` line; any ❌ → `Refs #<n>` and a new issue for the
   rest. Row numbering and the no-checkbox case: `references/writing.md`. *Done when rows equal
   checkboxes and every ✅ links a proof.*
3. **Draw what changes.** The smallest visual from `references/visuals.md`, labels in domain
   words, code names in a one-line legend. *Done when the owner reads every label without code.*
4. **Write the top last.** «In short», «Decision» and the table from `references/template.md`.
   *Done when the top block alone says merge or not yet, and what must happen first.*
5. **Check, publish, reread.**
   `python3 <skill-dir>/scripts/controlla_pr.py --body body.md --pr <n> -R <owner>/<repo> --head <sha>`
   exits 0 or 3 (3 = warnings worth a look); 2 = could not check, fix the cause and never publish.
   Then `gh pr edit <n> --body-file body.md` and, after ten seconds,
   `controlla_pr.py --verifica-pubblicato <n> -R <owner>/<repo>` (exit 1: the published closing
   links differ; rerun once, then fix the lines). *Done when the checker passes on the current
   head and the closing links match.*

## Output

The title (Conventional Commits naming the outcome) and the body, published on the PR. Template:
`references/template.md`; proof, risk, voice and gotchas: `references/writing.md`.
**Next:** `babysit`.

## Where this goes

This skill produces: **none (the body lives on the PR)**; a draft body is scratch, never a
document of the repository.

## Not for

- Reviewing someone else's diff: that is `review`.
- A draft opened only as a backup of local work: write the body when the PR is marked ready.
- Deciding whether the PR may merge: review, CI, `real-testing` and the owner decide that.
