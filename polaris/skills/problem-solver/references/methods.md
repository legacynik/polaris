---
title: methods — problem-solver
description: The moves behind each step — restating, the crux, divergence techniques, prior-art lenses, systems loops, discriminating experiments — and the blocks that keep a team stuck.
status: active
---

# Methods

## Why a team stays stuck

- **Same frame, new attempt.** Every attempt shares one assumption nobody wrote down. Listing the
  attempts side by side shows it.
- **The wrong problem.** The symptom in front of you is not the problem someone needs solved.
  Asking "whose problem is this, and what would they see if it were solved?" often moves it.
- **Judging too early.** The first plausible idea gets evaluated and the search stops. Generate
  first, judge later: a count (ten) keeps the two apart.
- **Local fix in a loop.** A feedback loop in the system recreates the problem after each fix.

## Restating — the problem worksheet

One sentence cannot hold a problem. Fill these, and refill them after every round of evidence:

| Field | Write |
|---|---|
| Problem statement | an outcome, not an activity; measurable; with a deadline; at the highest level we can influence (the whole flow, not one component) |
| Context | what is happening and why it matters now |
| Criteria for success | the observable result, and the accuracy that is good enough |
| Scope and constraints | what is in, what is off limits |
| Decision maker and their values | who decides, and by which filters they judge a solution |
| Sources of insight | who and what already knows something about it |

Then test it: flip one premise (what if the user, the input or the dependency behaved the
opposite way?) and relax one constraint at a time to see whether the solution space opens enough
to be worth it. Write the problem three ways — as the user meets it, as the system produces it,
as a goal — and keep the one that suggests the most testable hypotheses.

## Break it down, then find the crux

**A tree of the problem.** Start with a component tree when little is known (the parts and
levers of the problem), and turn its branches into testable statements (a hypothesis tree) as
soon as you can — a branch labelled "performance" drives no action, "the cache is cold after
each deploy" does. Use a deductive tree when the structure is known (the branches add up to the
whole: latency = queue + compute + I/O), an inductive one when you only have cases.

**Mutually exclusive, collectively exhaustive.** No branch overlaps another, nothing relevant is
missing. A factor that touches every branch (a config, a dependency) is not a branch of its own.

**Cut it more than one way.** The first cut is a habit. Try two or three frames — input/processing/
output, supply/demand, frequency/severity, build-time/run-time, ours/theirs — and keep the one a
back-of-the-envelope number shows to be revealing.

**Prune: impact × ability to move.** Score every branch on how much it would change the outcome
and on whether we can actually move it. Big and movable: work. Small, or big but immovable:
cut, and say so. A branch pruned only because it is hard comes back when a constraint is relaxed.

**The crux** is the big, movable branch the others depend on. If none stands out, the problem
is several problems: split it and solve one first.

## Divergence — at least ten, then judge

| Move | Ask |
|---|---|
| Invert an assumption | For each assumption the attempts shared: what if the opposite were true? |
| State the contradiction | "Improving X makes Y worse." Separate them in time (X now, Y later), in space (X here, Y there), by condition (X when …), or by scale (X for the part, Y for the whole). |
| Smaller or related problem | Solve a special case, drop a constraint, solve it for one input; then generalise. |
| Work backwards | Start from "solved" and ask what had to be true just before. |
| Another domain | Who faces the same shape of problem (queues, caches, markets, biology, logistics) and what do they do? |
| Do nothing, or the opposite | What happens if we stop trying to fix it? If we made it worse on purpose? |
| Absurd on purpose | Three ideas that cannot work; ask what would make each almost work. |

Write each as one line; evaluate none until there are ten.

## Prior art — one lens per scout

| Lens | Where | Returns |
|---|---|---|
| Same symptom | GitHub code search, issues and discussions of the libraries involved, error text verbatim | the thread where it was solved, with the fix |
| Same job | products and open-source projects that do what we are trying to do | how they structured it |
| Research | papers and engineering blogs from primary sources | the method and its measured result |
| Neighbouring domain | the domain named in divergence | the analogue and what transfers |

Each scout starts from fresh context with the restated problem, not with our failed attempts, so
it is not anchored on them.

## Is it a loop?

**Draw the loop.** 1. Write the symptom as something that accumulates (stale entries, open bugs,
queue depth). 2. What fills it and what drains it, and the decision behind each. 3. What the
symptom feeds back into those decisions — balancing (pulls back) or reinforcing (amplifies).
4. Where the delay is, and how long: real delays usually run about three times the first guess.
5. Who else pulls on it.

**Read the behaviour over time.** Rise then collapse: a reinforcing loop with a balancing one too
slow. Oscillation: a balancing loop with a delay. Steady but unwanted: balancing loops fighting
each other. Slightly off target: a leak the goal never accounts for.

**Recognise the trap.**

| You see | Trap | First move |
|---|---|---|
| a hard push, no lasting change, others pull back | policy resistance | stop pushing; align the actors on a larger goal |
| a shared resource (CI minutes, a staging box, a quota) degrading as each user takes a bit more | tragedy of the commons | restore the feedback: give each user the cost, or a rule |
| the bar slides with the results ("that's about what we get") | drift to low performance | an absolute standard, or anchor to the best past result |
| each fix makes the next fix necessary; the system's own ability weakens | shifting the burden | rebuild the system's own capacity, then withdraw the crutch |
| the rule is obeyed and its purpose missed | rule beating | treat it as feedback; redesign the rule toward its purpose |
| the indicator hits its target and the real aim is missed | seeking the wrong goal | measure the outcome, not the effort |

**Act where a small change moves the loop.** Changing a number (a timeout, a retry count, a
cache TTL) rarely moves a loop; stronger levers, in increasing order: buffers, the structure of
what flows, delays, the strength of balancing and reinforcing loops, who gets which information,
the rules, who can change the system, the goal itself. A jumpy reaction calls for a longer
response time, not a shorter one. Missing feedback: add the information before rebuilding
anything. Tempted to blame a person: swap the person and expect the same result — look for the loop.

## Sizing before testing

Rough numbers first; a big model only when they say it matters.
- **Order of magnitude**: what would a 10% change in each lever be worth? Give minimum, likely and
  maximum, not only the maximum.
- **80:20**: which fifth of the cases or inputs produces most of the failures?
- **Fewest assumptions first**: independent assumptions multiply — four at 80% hold together
  about 41% of the time, two hold 64%. Drop the simplest hypothesis when the facts disagree.
- **Expected value**: outcome × probability, read with its range; on a skewed distribution the
  mean misleads. Run it backwards to the break-even probability.
- **Marginal, not average**: the cost of the next unit decides, not the average cost.
- **Analogy**: "we've seen this" holds only after each assumption of the reference case is checked.
- **Root cause**: ask why until the answer is a cause you can act on; map contributing causes
  (people, process, tools, inputs, environment) when there is more than one.

## Converging

1. **The one-day answer.** At any point, write the best current answer in three lines: the
   situation, the complication (what changed or fails), the resolution (what we would do). It is
   a target to attack, not a conclusion.
2. **What would you have to believe?** For each top hypothesis, list what must be true for it to
   hold; the cheapest of those to check is usually the test.
3. **The knock-out test first.** Pick the analysis or experiment whose result could make the
   others unnecessary. Before running it, sketch the chart or output it should produce under each
   top hypothesis; a test every hypothesis predicts the same way teaches nothing.
4. **Plan each test in one row**: hypothesis · test · expected output · owner · by when.

| Hypothesis | Assumption flipped | What you'd have to believe | Knock-out test | Expected result per hypothesis | Cost |
|---|---|---|---|---|---|

Time-box it; a spike that answers nothing is deleted.

## Bias counter-measures

The loop is often a bias: in love with the first answer, anchored on the first number, unwilling to
drop sunk work, using the model nearest to hand, assuming the base case. Counter them on purpose:
someone has the obligation to dissent; write the antithesis of the current answer and argue it;
run a pre-mortem ("it failed — why?"); vote on hypotheses before the most senior voice speaks;
and look at the worst case, not only the expected one.
