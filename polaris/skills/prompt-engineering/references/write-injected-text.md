# Write: injected text (hooks, reminders, denials, prompt overrides)

Injected text reaches the model mid-session, without the task in view, often hundreds of times.
It competes with ~16k tokens of built-in tool descriptions. Sources: Serena's `claude-code`
context and `cc-system-prompt-override` (a tool-mapping table plus a "disallowed reasoning"
list); the vault's `serena-code-discovery-gate` hook (deny with the exact alternative);
Anthropic best practices ("Tool usage", "Optimize parallel tool calling", "Overeagerness").

## Anatomy

1. **Trigger named in the first words**, so the model knows why this appeared: "Symbol search
   blocked:", "Session start:".
2. **The alternative, exact and runnable**: tool name and arguments, not "consider using".
   A denial without the replacement is friction with no yield.
3. **Mapping table when several tools compete**: `intent → use this, not that`, one line each.
4. **Disallowed reasoning, listed**: the sentences the model uses to route around the rule ("I
   already know the path", "grep is faster here"), each with the one-line answer.
5. **Escape hatch, stated**: when raw text search is legitimate (a string literal, a non-code
   file), and how to do it so the gate passes.
6. **No personality, no history**: stateless, same text every time, under 120 words for a
   reminder and under 60 for a denial.

## Rules

- Measure before and after: count the tool calls the text is meant to shift (claude-mem
  `tool_uses`) for a week; a reminder that does not move the count is deleted.
- Fail-open: a hook that cannot parse its input exits silently. A gate that blocks work while
  offering a tool that is not installed is how guard-hooks die.
- One event, one message. Do not stack reminders on the same event.
- Overrides replace the harness prompt: pin the harness version the override was tested on.

## Checklist (binary)

- [ ] Trigger named first
- [ ] Runnable alternative with tool name and arguments
- [ ] Disallowed-reasoning list present
- [ ] Escape hatch stated
- [ ] Length within budget, stateless
- [ ] Measurement plan named (which count, which window)
