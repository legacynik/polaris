# Writing the body — step details, proof, risk, voice, gotchas

Read by `pr` while running its steps. The steps here are the long form of `SKILL.md`'s.

## Steps in full

1. **Collect.** For each issue the PR touches, `gh issue view <n> --json body,comments` (without a
   terminal the plain command prints only the comments) and copy every checkbox of its acceptance
   criteria and adversarial verification, comments included, in order. Note the PR's head
   (`gh pr view <n> --json headRefOid`): the draft is written against it. Gather the
   real-test receipt, the screenshots, the decision records governing the changed files
   (`git grep -l <path>` over the repository's decision path: `outputs.decision` in its
   `_polaris/config.yml`, `docs/adr/`, or `decisions/`) and, when a production deploy
   follows, its cargo (`git log <served-in-prod>..<candidate> --oneline`).
   *Done when every checkbox is copied and each of the five sources is in hand or known absent.*
2. **Answer every criterion.** One row per checkbox: ✅ with a proof the owner can open, ❌ with the
   reason. An issue whose rows are all ✅ gets its own `Closes #<n>` line; any ❌ makes it
   `Refs #<n>`, and the remainder becomes a new issue named in the row.
   A PR that closes no issue says `No linked issue.` in «In short».
   The `#` column is the checkbox's number in the issue: 1 to k, each once. The checker reads
   that column and the mark, not the text: a missing or repeated number, or a mark that is not ✅ ❌
   🟡 ⚠, blocks `Closes`. **An issue with no checkbox:** its rows are the top-level numbered or
   bulleted points under its criteria or «Fix» heading, 1 to k in order, and the first line under
   `### #<n>` says so: `Issue without checkboxes: rows = «Fix» 1-k`. The checker counts the same points
   (lines in fenced code never count); when it finds none it warns, naming the issue. Prose under
   another heading («Gate») is not a row: to be one it needs its own checkbox in the issue. A pull
   request never goes after `Closes` or `Refs` (`Closes` on it is blocked, `Refs` warned): a
   superseded PR is named in the text, «Supersedes #<n>».
   A `|` inside a cell is written `\|`, in code too; a row with more or fewer cells than its header
   is blocked.
   *Done when rows equal checkboxes (or points) and every ✅ links a proof.*
3. **Draw what changes.** One visual from `references/visuals.md`, every label in the domain's words, the
   code names in a one-line legend under it; then one plain sentence per touched piece.
   *Done when the owner can read every label without knowing the code.*
4. **Write the top last.** «In short», «Decision» and the table, placed first.
   *Done when the top block alone says merge or not yet, and what must happen first.*
5. **Check, publish, reread.**
   `python3 <skill-dir>/scripts/controlla_pr.py --body body.md --pr <n> -R <owner>/<repo> --head <sha>`
   must exit 0 or 3; exit 2 means it could not check (tracker, PR or image unreadable): fix the
   cause, never publish on a 2. `--pr` gives the PR's own files (they decide whether screenshots are required)
   and its head; `--head` is the head the draft was written against, and a PR that moved since
   blocks: reread it and rewrite. Without `--pr` pass `--visuale` or `--no-visuale`, or the checker
   refuses (exit 2): the folder you run it from is not the PR. `--no-visuale` overrides the PR's
   files only for a change nothing shows; on a PR touching interface files it warns, naming them. Exit 3 lists warnings worth a look,
   never a stop: an image pinned to a commit that does not open, an image linked to a branch, a
   Mermaid label with `( ) { } :` unquoted, a receipt signed on a SHA that is not the head.
   Then `gh pr edit <n> --body-file body.md`, and
   `sleep 10 && python3 <skill-dir>/scripts/controlla_pr.py --verifica-pubblicato <n> -R <owner>/<repo>`:
   GitHub recomputes the issues a PR closes a few seconds after the edit, and this compares them
   with the published `Closes` lines (exit 1 on a difference: rerun once, then fix the lines).
   *Done when the checker passes on the current head and the published closing links match.*

## Proof

Screenshots carry a visible change, and then they are required: before and after, wide screen and phone
when the layout differs, each under a short title saying what the step does and what to look at,
one step after the other in the order of the walk. Link them from a commit
(`https://github.com/<owner>/<repo>/blob/<sha>/<path>?raw=true`) or upload them with
`gh pr edit --attach` (gh ≥2.99 rewrites `![…](./shot.png)`; attached videos render as players).
Screenshots are the strongest evidence of a visible change; next comes execution: the exact
test that failed and now passes, command output. The proof section
carries what CI cannot show (live behaviour, screenshots, the receipt), and the body describes only
the final squashed result.

## Risk

A two-way door is walked back cheaply; a one-way door is not (data written in a new shape,
migrations, destructive or hard-to-reverse choices). The radius is everything the merge touches:
layout, other consumers, phone, other work riding the same deploy. When order matters, write it:
«migration in production, then merge, then deploy».

## Voice

Plain sentences, one fact each; separate clauses with a comma, a colon or a new sentence, never an
em dash. Name things («the invoice prints the address») rather than praise them («robust», «seamless»).

## Gotchas

- `Closes #1, #2` closes only #1 → one `Closes #<n>` line per issue.
- `Closes` on an issue with a ❌ row closes unfinished work at merge → `Refs`, plus a new issue.
- An image linked by local path or branch name breaks or drifts → a commit SHA
  (`blob/<sha>/<path>?raw=true`, the checker opens each one), or `--attach`.
- Committing screenshots moves the head → a receipt bound to the old head must be signed again;
  `--attach` leaves the head where it is.
- Any commit after the real-test makes the receipt stale, code commits above all, not only
  screenshot commits → name the head and the commits after it in the Real-test row, or sign again.
- `Refs #<n>` on a superseded pull request reads it as an issue → «Supersedes #<n>» in the text.
- The head moves while you draft (CI fixes, a rebase) → `--head <sha>` makes the checker block it.
- GitHub renders Mermaid, but `( ) { } :` or «» inside a label break it → quote every label:
  `A["Customer picks (from the list)"]`.
- A top block that needs the rest to be understood buries the verdict → reread the top alone.
- `git diff origin/main..HEAD` shows what `main` gained since the branch as deletions → the PR's own
  change is `origin/main...HEAD` (three dots); a branch behind `main` goes in «Decision».
