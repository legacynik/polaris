# Builder check

Before `critic`: a fresh-context agent reads the plan as the person who will build it. `critic`
attacks whether the plan is right; this asks whether it can be built without guessing. Give the
agent the plan path and nothing of your reasoning.

```
You are a capable software engineer. You have been handed the plan at <PLAN_PATH> and will
build it alone: you cannot talk to its author or its owner. Read it, and the files it names.

List only the questions you would still need answered before building: places where you would
have to guess and a wrong guess changes what gets built or how it behaves for a user. For each:
the question, the plan line it comes from, why the answer matters. Most important first.

Skip what the plan explicitly leaves to the builder, what a competent engineer decides alone,
and wording nitpicks. If nothing important is left, answer "nothing important left".
```

Sort every question:

| Kind | What you do |
|---|---|
| answered already (in the plan, the code or the owner's words) | put the answer where the builder will look for it |
| minor (any reasonable answer works) | decide, write it as `proposal (agent):` |
| the owner's (changes scope, cost or what a user sees) | one round of questions to him, options included |

One pass. If the owner's answers change the plan's shape, that is a new plan draft, not a loop.
