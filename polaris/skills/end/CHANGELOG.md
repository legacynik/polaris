# Changelog — end

## 1.26.0 — 2026-10-26 — the session rake

- New `scripts/session_rake.py` (founder, 2026-10-26: every day's session log reaches the default
  branch the same day). `plan` lists, read-only, the session-only commits on any local branch that
  origin/<default> lacks, the newest version of each path and the commits that are `mixed — not
  raked`, and never a version older than origin's last change to that path; `apply` writes those versions in a throwaway worktree on origin/<default>, pushes
  `chore/sessions-<login>-<date>` and opens or updates one docs PR, merged only with `--merge`
  and `session.rake_merge: true` in config.yml (default false); `sync` puts the local default
  branch back on origin/<default> with `reset --keep` (or `branch -f`) only when its extra commits
  are session-only and identical upstream, and changes nothing otherwise.
- A session log is combined by entry, never chosen: the raked file is the union of origin's and
  every branch's `## HH:MM — ` entries, each once, in time order, so two branches appending to one
  day's log both survive; `sync` counts a log whose entries are all upstream as upstream. Files
  without entries (handoffs) keep newest-wins. The rake PR adds `merge=union` for
  `team/*/sessions/*.md` and `team/*/handoff/*.md` to the contract root's `.gitattributes`, so the
  feature branch that merges after its log was raked does not conflict.
- The close runs `apply --merge` then `sync` after landing the handoff (`references/close.md`,
  Step 5b). Checkpoints still commit where you are: `session_commit.sh` carries the dated
  amendment under the 2026-09-04 note.

## 1.25.2 — 2026-10-26

- `references/bypass-test.md` runs `session_gate.py` from the installed skill, not from the lab path `skills-suite/`, which an installed package does not have.

## 1.25.1 — 2026-10-26

- A `- Decision:` pointer may name a DEC record (`decisions/<DEC-id>.md`) that `/architecture decide`
  wrote: verify passes when that file is committed and clean, before it only looked for a heading
  of `decisions.md`.
- `prepare` refusing a dirty ledger now says what to do: commit what `/architecture decide` or
  `lesson_record.py` just wrote, pathspec-only, then run again.
- The `NO_SUCH_ROW` message names `/end checkpoint`, no longer `/update`.

## 1.25.0 — 2026-10-25 — absorbed `update`

- One skill saves the session (founder, 2026-10-25: «if the lane is closed, end leaves no handoff;
  if there is still work, it also leaves the handoff»). Default `/end` closes; "checkpoint / save
  progress / salva" or `/end checkpoint` is a mid-session checkpoint that keeps the session open.
- Every call: one session-log entry, your one lane line rewritten in the cockpit
  (`state_upsert.py thread`), lessons only through `lesson_record.py`, the session's decisions
  listed with their homes, a pathspec-only commit. The close adds the gate, the prune against git
  and the tracker, and finalize on `READY_FINALIZE`.
- Handoff file only while the lane has open work: closed = `lane_phase.sh` printed `READY_FINALIZE`
  and In progress, Next session and Blocker are `none`; every other answer writes it.
- Decisions are never written by `end`: each goes through `/architecture decide` (a hook refuses a
  hand-written ADR, DEC, `decisions.md` or `ARCHITECTURE.md`). `## Where this goes` is now `none`.
- Moved from `update` unchanged in behaviour: `scripts/` (`checkpoint.sh`, `session_commit.sh`,
  `state_upsert.py`, `state_close.py`, `state_priorities.py`, `recent_context.py`, `todos_roll.py`,
  `state_lines.py`, `state_lock.py`, `state_sections.py` and the selfchecks), `tests/`, the full
  procedure as `references/checkpoint.md`, its bypass cases as B7–B11. `prune_threads.py` imports
  its siblings from its own directory. Eval: update's checkpoint triggers are positives here, its
  read-intent and meta negatives come with them (22 cases, 12 checks). Output ends with `**Next:**`.

## 1.24.1 — 2026-10-25

- Public-package clean (C5): CHANGELOG provenance names the public package repo, not its owner login.

## 1.24.0 — 2026-10-24

- Rewritten to the 60-line form with `lifecycle`, `io`, `status: active`, the ◇ description; the
  full procedure lives in `references/close.md`.
- Lessons are written only through `scripts/lesson_record.py` into `records/` (never
  `lessons.md`); a recurrence (`OCCURRENCE`, or a family that already holds another lesson) or an
  incident opens one bead
  `kind:followup src:lesson` naming the check to build (operating model §7). Decisions follow §6:
  ledger entry, or a DEC file with a probe when it must be enacted. `end` does not close plans:
  `plan close` runs from `ship`.
- Scripts: real `--selfcheck` on `merge_truth.py`; `lane_phase.sh` messages in English; `wt_sweep.sh` selfcheck assertion can now fail
  and a branch `git branch -d` refuses is named (RED `.rosso/b6a-wt-sweep.jsonl`).
- New: `references/bypass-test.md`, `eval/` (11 trigger cases, 5 checks, split), `tests/`. Plan unit B6a.

## 1.23.5 — 2026-10-24

- Imported into polaris-os `skills-suite/` from the public package repo at 8fdfee9 (`polaris/skills/end`).
- Version bump: patch (import), from 1.23.4. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.

## Absorbed history — update

### 3.4.1 — 2026-10-25

- Public-package clean (C5): CHANGELOG provenance names the public package repo, not its owner login.

### 3.4.0 — 2026-10-24

- Rewritten to the 60-line form with `lifecycle`, `io`, `status: active`, the ◇ description;
  `model:` removed (a skill names no model). Details in `references/procedure.md`.
- Lessons: recorded through `scripts/lesson_record.py`, and `- Lesson:` names the record id it
  printed; `checkpoint.sh verify` checks that id in `records/` (lessons.md is a retired pointer the
  vault gate refuses). Decision pointers unchanged.
- Scripts: real `--selfcheck` everywhere; `session_commit.sh` names paths it could not unstage
  (`STILL STAGED`) instead of claiming the index was restored, and never claims it when the
  index cannot be read, and the forbidden-file abort
  unstages every session path (RED `.rosso/b6a-session-commit.jsonl`); `checkpoint.sh verify`
  names an unreadable cockpit (RED `.rosso/b6a-checkpoint-verify.jsonl`); `--end` refuses a
  pre-staged `occurrences.jsonl`; `plan-week` → `week` in the state writers.
- New: `references/bypass-test.md`, `tests/`; `eval/` kept. Plan unit B6a.

### 3.3.4 — 2026-10-24

- Imported into polaris-os `skills-suite/` from the public package repo at 8fdfee9 (`polaris/skills/update`).
- Version bump: patch (import), from 3.3.3. Plan: `docs/modules/polaris-harness/plans/open/2026-10-24-skills-lab-and-public-repo.md`.
- 2026-10-25: removed — absorbed into `end` 1.25.0.
