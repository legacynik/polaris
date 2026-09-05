# First run — set POL up with the contributor, do not guess for them

Read this ONLY when Step 0 of `/start` said setup is needed. If it did not, this file costs nothing
because it was never opened. Written for someone who is not a systems engineer: explain each command
in one plain sentence BEFORE running it, and say what it will and will not touch.

Never run the whole thing silently and report at the end. Onboarding is a conversation; the values
below belong to the person in the chair, and a value you invented is a value they will find wrong in
three days and never trust again.

## What to say first

Say what Polaris is, in four lines, and what you are about to create:

> POL keeps the thread between sessions: what you are working on, what you decided, what is still
> open. It lives in `_polaris/` inside this repo — plain Markdown, committed with your code, no
> service and no database.
> I am going to create **your** folder only. I will not touch anyone else's files, and I will not
> commit anything without asking.

Then confirm before proceeding. A person who does not know what is about to be written cannot
consent to it.

## Step 1 — Identity

Polaris keys everything to the GitHub login, so ownership is never guessed from a name.

```bash
gh auth status            # already logged in?
gh api user --jq .login   # the exact login, case-sensitive
```

Explain first: *"This reads who you are on GitHub. It changes nothing."* If `gh auth status` fails,
the contributor has to run `gh auth login` themselves — it opens a browser and asks for a code, and
an agent cannot do it for them. Say that plainly, and say the session can continue right after.

**If the login requires a restart of the harness to take effect**, write a one-line sentinel at
`<root>/state/.onboarding-pending` naming the step that was reached, tell the contributor what to
run when they come back, and stop. On the next `/start`, that file is the resume point — read it,
continue from the named step, and delete it when the flow completes. A setup that cannot survive a
restart is a setup that strands people halfway.

```bash
git config --local polaris.login "<login>"   # cached per repo, so this is asked once
```

## Step 2 — The profile, asked and not assumed

Provision **only** this contributor's path, from the template:

```bash
mkdir -p "_polaris/team/$LOGIN/weeks" "_polaris/team/$LOGIN/reports" "_polaris/team/$LOGIN/sessions"
cp "<plugin>/templates/repo-contract/profile.yml" "_polaris/team/$LOGIN/profile.yml"
```

Then ask — one question at a time, with the default named so a shrug is a valid answer:

| Field | Ask it like this | Default if they shrug |
|---|---|---|
| `language` | "Which language do you want the conversation in? Code, commits and technical docs stay English either way." | `en` |
| `voice` | "How do you want the briefs delivered — `cynical` (direct, no preamble, assumes broken until proven) or `plain` (same facts, softer)? You can also write your own line." | `cynical` |
| `explain_as` | "Should I explain things as a developer would, or in plain language with analogies?" | `dev` |
| `push_back` | "Do you want me to pressure-test your decisions before executing, or just execute?" | `true` |
| `weekly_capacity` | "Roughly how many work items a week is realistic for you here?" | `3` |
| `preferred_areas` | "Any area you want to be routed toward — backend, infra, frontend?" | `[]`, derive from repo evidence |

Write the answers into the profile, then prove the identity gate passes:

```bash
grep -q "^github: $LOGIN$" "_polaris/team/$LOGIN/profile.yml" || echo "STOP: profile does not match the login"
```

## Step 3 — The two state files, seeded with real content

`state/current.md` and `state/goals.md` are where the work lives between sessions. Seed them from
what the contributor actually tells you — **never with placeholder text**. A file full of
`[your priority here]` teaches the reader that the file is decorative, and that lesson sticks.

Ask: *"What are you actually working on here right now, in order?"* and write those lines. Then:
*"And what are you trying to reach — the outcome behind the work?"* If they do not know yet, write
that honestly (`# Priorità attive` with one line saying setup just happened) rather than inventing
three fake priorities. An empty-but-true file beats a full-but-false one.

Both files carry their own contract in the footer, so whoever opens them next knows the rules
without needing this guide:

```markdown
*Questo file è lo stato di sessione: si sovrascrive, non si accumula. Una sola riga `Updated:`.
`/update` aggiunge e flagga, `/end` è l'unico che chiude. Se `Updated:` ha più di 3 giorni, POL
propone una ricostruzione.*
```

`current.md` is gitignored — it is local to this checkout. Say so, or the contributor will expect a
teammate to see it and be surprised when they do not.

## Step 4 — Say what happens from now on

Close with the loop, in three lines and no jargon:

> `/start` picks the thread back up. `/update` saves a checkpoint mid-session. `/end` closes the day,
> writes the handoff and offers a commit. Everything else is just working.

Then delete the sentinel if one exists, and run the normal `/start` resume flow — the contributor
came here to work, not to be onboarded.

## Never, in this flow

Create `team/<login>/` for anyone but the contributor in the chair · commit anything without an
explicit yes · write `goals.md` from your own guesses · fill a state file with placeholders · run a
command you have not explained · continue past a failed identity gate.
