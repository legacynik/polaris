# Credits

This skill was imported from the `prototype` skill of `mattpocock/skills`
(`skills/engineering/prototype`, folder hash `e41d92e171f074a2b6887d8f6faca4a15c83d1ca`, installed
locally 2026-07-25, updated 2026-09-18), used under the MIT License, Copyright (c) 2026 Matt Pocock.

Kept: the question decides the shape; the two branches (logic demo as one shareable HTML file,
UI variants behind `?variant=` with a floating switcher) — now `references/logic.md` and
`references/ui.md`, nearly verbatim; throwaway from day one, trivial to run, no persistence, no
polish, surface the state.

Changed: one named question per spike, tied to a plan assumption; the spike branch never merges
and the code is not folded into main — only a verdict block enters the plan file's section 4, and
the winner is rebuilt test-first in the build phase; a spike that answers nothing is deleted.
