---
title: methods — problem-solver
description: An open list of approaches to a stuck problem, each with when it fits, the move and the question it forces, plus optional tools — the problem worksheet, the crux tree with more than one cut, the systems loop, traps and leverage ladder, heuristics before big models, prior-art lenses, the knock-out test, bias counters. None is mandatory.
status: active
---

# Methods

Nothing here is a checklist. The approaches are an open list to choose three from, or to invent a
fourth; the tools are there when a problem calls for one.

## Why a team stays stuck

- **Same frame, new attempt.** Every attempt shares one assumption nobody wrote down.
- **The wrong problem.** The symptom in front of you is not the problem someone needs solved:
  whose problem is it, and what would they see if it were solved?
- **Judging too early.** The first plausible idea gets evaluated and the search stops.
- **Local fix in a loop.** A feedback loop in the system recreates the problem after each fix.

## Approaches — an open list

An approach is a way of looking, not a fix. Choose three that pull in opposite directions and that
the attempts so far did not use; invent a fourth when none fits. Each forces one question.

| Approach | Fits when | The move | The question it forces |
|---|---|---|---|
| Invert it | out of solution ideas; the goal is fuzzy but failure is easy to picture | solve the opposite problem, the more extreme the better ("make customers avoid buying"); then avoid each part | is something we do today already causing it? |
| Drop the fixed constraint | every attempt worked inside the same boundary | name the constraint treated as given and solve without it; "how would we do it in a day?" | is it a constraint, or only custom? |
| Decompose to the crux | the problem has many parts and effort is spread thin | a tree whose branches neither overlap nor leave gaps; keep the big branch we can move | which one branch, if moved, makes the others follow? |
| Dig to the first cause | symptoms keep moving, the cause is never named | ask why until the answer is a cause we can act on; map contributing causes when there are several | what would still be broken if this symptom vanished? |
| See it as a system | each fix holds a while, then the problem returns | the loop that keeps it alive (tool below) | what fills it, what drains it, and where is the delay? |
| Borrow from another field | the shape is common even if the domain is not | who solves a problem with the same structure (queues, caches, markets, biology, logistics); or force an analogy with a random object | how would *they* solve it, and what transfers? |
| Shift the perspective | everyone describes it from the same chair | look through the user's, the attacker's, the newcomer's, the competitor's, the operator's eyes | whose problem is this, and what would they see if it were solved? |
| Combine attributes | the obvious options are exhausted | two lists of attributes as a grid; scan for the unusual combinations | which cell has nobody tried? |
| Work backwards | the end state is clear, the path is not | start from "solved" and ask what had to be true just before, step by step | what is the first step we cannot yet explain? |
| State the contradiction | every fix for one case breaks another | "improving X worsens Y"; separate them in time, space, condition or scale | must X and Y really be the same thing at the same moment? |
| Solve a smaller problem | the whole is too tangled to hold | a special case, one input, one constraint dropped; then generalise | what is the simplest version we cannot solve either? |
| Look at the blind side | the team agrees too quickly | sort what we know, what we know we don't, what we have but don't use, and what we don't know we don't know | what would someone outside see that we can't? |
| Do nothing, or the opposite | effort keeps rising and results do not | what happens if we stop fixing it, or make it worse on purpose | who notices, and what does that tell us? |
| Attack the central assumption | flipping a plan | name the premise the plan rests on and suppose it false | if this premise were wrong, would we still want any of the plan? |

## Questions that push the thinking

- What would you have to believe for this to work? Which of those is cheapest to check?
- What result would prove it wrong? A test every option predicts the same way teaches nothing.
- What did every attempt so far take for granted?
- What is the strongest case for the opposite answer? It failed a month from now — why?

## Optional tools

**Problem worksheet**, when the statement is vague: outcome (not an activity), measure, deadline,
what is off limits, who decides and by which values, who already knows something. Write the
problem three ways — as the user meets it, as the system produces it, as a goal — and keep the one
that suggests the most testable ideas.

**Crux tree**, for decomposing: a component tree when little is known, turned into testable
statements as soon as possible ("the cache is cold after each deploy", not "performance").
Deductive when the parts add up (latency = queue + compute + I/O), inductive when you only have
cases. **If the first cut feels obvious, try two more** (input/processing/output, supply/demand,
frequency/severity, build/run time, ours/theirs) and keep the one a quick number shows to be
revealing. Score branches on impact and on whether we can move them; the crux is the big, movable
branch the others depend on. If none stands out, it is several problems.

**Systems loop**, for the system approach — the structure that keeps the problem alive, not a
culprit (new people in the same seat behave the same way):
1. Write the symptom as a stock, something that accumulates (open bugs, stale entries, queue depth).
2. What fills it and what drains it (the flows), and the decision behind each.
3. What the stock feeds back into those decisions: balancing (pulls toward a goal) or reinforcing
   (amplifies). Where the delay is — real delays run about three times the first guess.
4. What each actor sees, is paid for and is constrained by; "irrational" behaviour usually isn't.

Behaviour tells you the structure: oscillation = a balancing loop with a delay (slow the response
before speeding anything up); settling short of the goal = a drain fighting the loop; rise then
crash = a reinforcing loop hitting a limit; steady output with shrinking slack = resilience eroding.

| Trap | Tell | Way out |
|---|---|---|
| Policy resistance | harder push, same result; everyone exhausted holding the status quo | let go; bring every actor in; find a larger goal they share |
| Tragedy of the commons | a shared resource (CI minutes, staging, a quota) erodes while each user acts rationally | restore the feedback: give each user the cost, or regulate access |
| Drift to low performance | "it's not that bad"; the bar slides with the results | absolute standards; let the best past performance set the bar |
| Escalation | two sides each trying to exceed the other: arms race, price war | don't enter, step down unilaterally, or negotiate a balancing loop |
| Success to the successful | winners gain the means to win again; concentration | level the field; cap the share; rewards that don't bias the next round |
| Shifting the burden | more and more of the fix needed; withdrawing it hurts | rebuild the system's own capacity, then withdraw the crutch |
| Rule beating | the letter obeyed, the purpose defeated | redesign the rule toward its purpose |
| Seeking the wrong goal | the indicator hits target while things get worse; effort taken for result | measure the outcome, not the effort |

**Leverage, weakest to strongest** — if a fix doesn't hold, climb a rung: numbers (timeouts,
TTLs, budgets: most attention, least change) · buffers · the structure of stocks and flows ·
delays · balancing loops · reinforcing loops · information flows (who sees what: missing feedback
is a common cause and cheap to fix) · rules (and who makes them) · the power to change the
structure · the goal (every lower point bends to serve it) · the mindset the goal comes from.
Check the direction too: the lever is often found, then pushed the wrong way.

**Heuristics before big models**: order of magnitude with min, likely and max; which fifth of
the cases produces most failures; independent assumptions multiply (four at 80% hold together
about 41% of the time); expected value read with its range; marginal cost, not average. A big
model only when the rough numbers say it matters.

**Prior art**, for the borrow approach: fresh-context scouts, one lens each — same symptom (issues
and discussions, the error text verbatim), same job (products and projects that do it), research
(primary sources), neighbouring domain. Each with a link, or "found nothing".

**The knock-out test**, for the experiment: the cheapest one whose result could make other work
unnecessary. Before running it, sketch the result it should give if the answer is right and if it
is wrong; a test that comes out the same either way teaches nothing. Time-box it; a spike that
answers nothing is deleted.

## Bias counters

In love with the first answer, anchored on the first number, unwilling to drop sunk work, using
the model nearest to hand: argue the antithesis on purpose, run a pre-mortem, look at the worst
case, not only the expected one.
