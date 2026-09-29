# Bypass-test — skill-meta

Ten ways around the gate. Every one of them **must fail** now: exit ≠ 0, or the persisted
state left untouched. If one passes, the gate is declared, not armed.

## Contents

- [B1 — incomplete frontmatter (T1)](#b1--ship-a-skill-with-incomplete-frontmatter-t1)
- [B2 — colliding description, no donor (T2a)](#b2--a-colliding-description-with-no-declared-donor-t2a)
- [B3 — lower the floor after a regression (T2b)](#b3--lower-the-rank-1-floor-after-a-regression-t2b)
- [B4 — measure on TRAIN (T2b tripwire)](#b4--pick-the-description-by-measuring-on-train-t2b-filename-tripwire)
- [B5 — carry a green across a trigger edit](#b5--carry-a-green-rank-1-across-a-trigger-edit-the-modification-gate)
- [B6 — read a green from another tree (T1)](#b6--read-a-green-that-belongs-to-another-tree-t1)
- [B7 — a tier that always blocks (T2a)](#b7--a-tier-that-always-blocks-so-it-gets-skipped-t2a)
- [B8 — flip the mark with no receipt](#b8--flip-the-promotion-mark-with-no-receipt)
- [B9 — a pin that only computes by hand](#b9--a-pin-that-only-computes-when-the-script-is-run-by-hand)
- [B10 — a prose declaration that declares nothing](#b10--a-prose-declaration-that-declares-nothing)

B1-B4 arm the tiers. B5-B9 arm the modification gate, and all five **succeeded** against the
version named in each `fails_before` — the outputs are in
`docs/skill-refactor/2026-08-17-skill-meta-v1/EVIDENCE.md`. B10 arms the waiver list the gate
grew when the PROSE class became payable.

Run them all:

```bash
cd <skills-suite>/skill-meta/scripts
for f in *.py; do python3 "$f" --selfcheck || { echo "FAILED: $f"; exit 1; }; done
```

Each `--selfcheck` carries at least one of these as an automatic assertion: `new_skill.py`
proves B1 against the **real** T1, not a copy; `collision_check.py` proves B2;
`trigger_ratchet.py` proves B3 and B4; `eval_verdict.py` proves that a drop in pass-rate
gives `FAIL`, not a silent pass; `change_gate.py` proves B5 plus the thin-corpus branches.

## B1 — ship a skill with incomplete frontmatter (T1)

```bash
cd /tmp && rm -rf bp1 && mkdir bp1
python3 "<skills-suite>/skill-meta/scripts/new_skill.py" broken --root /tmp/bp1
python3 - <<'PY'
p = "/tmp/bp1/broken/SKILL.md"
open(p, "w").write(open(p).read().replace("lifecycle:", "# lifecycle removed\n"))
PY
python3 "<skills-suite>/skill-meta/scripts/new_skill.py" --check /tmp/bp1
echo "exit=$?"   # EXPECTED: 1 (or 2 outside a skills-suite checkout)
```

`_standard/validate_suite.py` must print `manca 'lifecycle'` and exit 1. If it exits 0, T1 is
broken: someone made `lifecycle` optional without changing `REQUIRED` in the shared gate.

## B2 — a colliding description with no declared donor (T2a)

Self-contained on purpose: it builds its own near-duplicate pair rather than depending on
what happens to be in the real catalogue while other jobs are under construction.

```bash
cd /tmp && rm -rf bp2 && mkdir -p bp2/review-fixture
cat > bp2/review-fixture/SKILL.md <<'EOF'
---
description: Use when reviewing a pull request for correctness before merge
---
EOF
python3 "<skills-suite>/skill-meta/scripts/collision_check.py" \
  --desc "Use when reviewing a pull request for correctness before merging code" \
  --catalog-dir /tmp/bp2
echo "exit=$?"   # EXPECTED: 1 — over 75% similar, no donor declared
python3 "<skills-suite>/skill-meta/scripts/collision_check.py" \
  --desc "Use when reviewing a pull request for correctness before merging code" \
  --catalog-dir /tmp/bp2 --donor review-fixture
echo "exit=$?"   # EXPECTED: 0 — same collision, declared donor
rm -rf /tmp/bp2
```

If the first exit is 0, the BLOCK threshold (0.75) was silently disabled.

## B3 — lower the rank-1 floor after a regression (T2b)

```bash
S=/tmp/bp3-state.json
M="--model demo --input-tokens 10 --output-tokens 2 --wall-ms 30 --valid-runs 3 --excluded-runs 0"
python3 "<skills-suite>/skill-meta/scripts/trigger_ratchet.py" --slug demo --rate 0.90 --state "$S" $M
cat "$S"                                    # floor: 0.90
python3 "<skills-suite>/skill-meta/scripts/trigger_ratchet.py" --slug demo --rate 0.60 --state "$S" $M
echo "exit=$?"                              # EXPECTED: 1
cat "$S"                                    # EXPECTED: floor STILL 0.90, not 0.60
```

If the second `cat` shows `0.60`, the ratchet was bypassed: someone made the state persist on
the failure branch too (`apply()` must return `ok=False` and the caller must not write).

## B4 — pick the description by measuring on TRAIN (T2b, filename tripwire)

```bash
python3 "<skills-suite>/skill-meta/scripts/trigger_ratchet.py" \
  --slug demo --rate 0.95 --state /tmp/bp4-state.json --measured-on data/train.json \
  --model demo --input-tokens 10 --output-tokens 2 --wall-ms 30 --valid-runs 3 --excluded-runs 0
echo "exit=$?"   # EXPECTED: 1 — a great rate measured on train must never pass
test -f /tmp/bp4-state.json && echo "BUG: state written despite the refusal" || echo "ok: no state written"
```

Declared limit (see "Known gaps"): this is a tripwire on the **name**, not on provenance — a
`test.json` actually holding the training queries slips past. Not solvable by an isolated
script; the underlying defence stays step 5 of the Flow, where `split_traintest.py` writes
two physically distinct files.

## B5 — carry a green rank-1 across a trigger edit (the modification gate)

`fails_before: skill-meta v0.1.0` — this one **worked**: T1 exited 0 on an edit that rewrote
the description itself, T2a exited 0, and nothing in the pipeline demanded a re-measurement
or noticed that no corpus existed to measure against.

```bash
cd /tmp && rm -rf bp5 && mkdir bp5 && cd bp5 && git init -q .
mkdir -p door/references door/eval
# ... a structurally valid skill, committed, with a measured rank-1 recorded ...
python3 "<skills-suite>/skill-meta/scripts/trigger_ratchet.py" --slug door --rate 0.90 \
  --state door/references/ratchet-state.json --skill door --model demo \
  --input-tokens 10 --output-tokens 2 --wall-ms 30 --valid-runs 3 --excluded-runs 0
git add -A && git -c user.email=a@b -c user.name=a commit -qm base
# now rewrite the trigger and try to ship on the old receipt
python3 - <<'PY'
p="door/SKILL.md"; s=open(p).read()
open(p,"w").write(s.replace('description: "old trigger"', 'description: "a much broader trigger"'))
PY
python3 "<skills-suite>/skill-meta/scripts/change_gate.py" --skill door \
  --state door/references/ratchet-state.json
echo "exit=$?"   # EXPECTED: 1 — "a green does not travel across a trigger edit"
```

The message must name the recorded pin, the current pin, and re-measurement. If it exits 0,
the pin was dropped: check that `trigger_ratchet.py --skill` still writes `desc_sha256` and
that `check_receipt` still compares it.

Two adjacent branches, same case: with the corpus **absent** the gate must fail before it
even reaches the pin (`prompts.json missing`), and with a corpus that is all-positive, under
ten cases, or full of placeholders it must fail too. A corpus that cannot catch trigger theft
is not a corpus.

## B6 — read a green that belongs to another tree (T1)

`fails_before: skill-meta v0.1.0` — this one **worked**. `new_skill.py --check <root>` is the
documented form, but the path landed in the `slug` positional and the check silently ran on
the current working directory. From inside `skills-suite` it printed `18/20 skill conformi`,
which an author reads as "my skill passed" while their skill was never looked at.

```bash
cd <skills-suite>
python3 skill-meta/scripts/new_skill.py --check /tmp/bp1
# EXPECTED: the report covers /tmp/bp1 only — "1/1 skill conformi", never the 20 of the suite
```

If the count matches the suite size, the argument is being ignored again.

## B7 — a tier that always blocks, so it gets skipped (T2a)

`fails_before: skill-meta v0.1.0` — this one **worked**, in the most expensive way a gate can
fail: `collision_check.py --skill <dir> --catalog-dir <root>` never removed the skill's own
entry from the catalogue, so every skill living inside the catalogue it is checked against
matched **itself at 100%** and BLOCKed. A tier that is red no matter what is a tier nobody
runs.

```bash
cd <skills-suite>
python3 skill-meta/scripts/collision_check.py --skill skill-meta --catalog-dir .
echo "exit=$?"   # EXPECTED: 0 with a real verdict over the siblings, never a 100% self-match
python3 skill-meta/scripts/collision_check.py --skill skill-meta --catalog-dir skill-meta
echo "exit=$?"   # EXPECTED: 2 — nothing to collide with is "not verifiable here", not a green
```

The second command is the guard against over-correcting: dropping the self-entry must not
turn an empty catalogue into a pass.

## B8 — flip the promotion mark with no receipt

`fails_before: skill-meta v0.2.0`. The `◇` → `✦` flip is a real modification — it declares the
door promoted by measured use — and nothing gated it. `_standard/SKILL-STANDARD.md` says a flip
without a receipt row is reverted on sight; that was a sentence, not a check.

```bash
# a mark flip and nothing else
python3 - <<'PY'
import pathlib
p = pathlib.Path("ship/SKILL.md")
p.write_text(p.read_text().replace("description: ◇ ", "description: ✦ "))
PY
python3 skill-meta/scripts/change_gate.py --skill ship
echo "exit=$?"   # EXPECTED: class MARK, owes "T1 RECEIPT", exit 1 while the CHANGELOG is silent
```

Two things must hold at once. The class must be **MARK**, not TRIGGER: the trigger text did not
move, so demanding a fresh 18-dispatch measurement for a status badge would be the noise that
gets a gate switched off. And the pin must still match — `desc_sha()` strips the mark — so the
recorded rate survives the promotion. What the flip owes is the receipt: a row in
`CHANGELOG.md` naming the slug, with the invocation count, the repos and the date.

The match is word-bounded. A plain substring test passed a changelog that never mentioned the
skill, because the slug `d` occurs inside `door`:

```bash
python3 skill-meta/scripts/change_gate.py --selfcheck
# asserts: "a slug matching inside another word is not a receipt"
```

## B9 — a pin that only computes when the script is run by hand

`fails_before: skill-meta v0.2.0`. `trigger_ratchet.py` imported `desc_sha` from its sibling
`change_gate.py` and relied on `sys.path[0]` being the script's own directory — true only when
the file is executed directly. Loaded **by path**, which is how a runner or another script
imports it, the pin could not be computed at all:

```bash
cd / && python3 -c "
import importlib.util
p='<skills-suite>/skill-meta/scripts/trigger_ratchet.py'
s=importlib.util.spec_from_file_location('tr',p); m=importlib.util.module_from_spec(s)
s.loader.exec_module(m); print('desc_sha present:', hasattr(m,'desc_sha'))"
# BEFORE: ModuleNotFoundError: No module named 'change_gate'
# EXPECTED NOW: desc_sha present: True
```

The defence is a selfcheck branch, not a comment: `trigger_ratchet.py --selfcheck` spawns that
exact by-path load from an unrelated cwd and fails if the sibling import does not resolve. The
alternative — copying the two hash lines into both scripts — would put the pin's definition in
two places, and a pin computed two ways is not a pin.

## B10 — a prose declaration that declares nothing

`fails_before: skill-meta v0.9.0` — the version that first made the PROSE class payable. Any
waiver list is one careless parser away from being a switch, and this one has three ways to
get there. All three must fail.

**a. A placeholder reason.** The row exists, the pin is right, and the justification is a full
stop:

```bash
printf 'bugfix %s: .\n' "$SHA" > <skills-suite>/_standard/prose.allow
python3 <skills-suite>/skill-meta/scripts/change_gate.py --skill <skills-suite>/bugfix
# EXPECTED: exit 3 — parse() rejects the row, so nothing is declared
python3 <skills-suite>/skill-meta/scripts/prose_declaration.py --check <skills-suite>
# EXPECTED: exit 1 — "a declaration without one is a switch"
```

This is SKILL-STANDARD.md's rule 5 — the one that cost 16 skills out of 16 — applied to the
newest field in the suite. The two scripts share one `PLACEHOLDER` in `_lib.py`, so the eval
corpus and this list cannot drift apart on what counts as an answer.

**b. A pin written ahead of the edit.** Add the row for the body you are *about* to write, land
it in an earlier PR, then change the body in a later one with the waiver already merged:

```bash
printf 'bugfix %s: pre-authorised\n' "$SHA_OF_THE_BODY_I_HAVE_NOT_WRITTEN_YET" >> prose.allow
python3 <skills-suite>/skill-meta/scripts/prose_declaration.py --check <skills-suite>
# EXPECTED: exit 1 — "the row excuses nothing, remove it": the pin does not match the body on
# disk, so the PR that adds the row is red before the PR that would use it exists
```

**c. A row that outlives its body.** The reverse, and the reason the list can only shrink: once
the body moves past a declared hash the row is dead, so reverting to an old wording cannot ride
an old row — `--check` reddened it long before, and it was removed.

The defence is `prose_declaration.py --selfcheck` (ten branches, run by suite-ci) plus a
`--check skills-suite` step that runs on **every** PR, not only those whose `SKILL.md` moved:
the `change_gate` loop is driven by changed skill files, so a PR touching nothing but
`prose.allow` would otherwise pass through no gate at all.
