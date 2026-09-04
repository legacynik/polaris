#!/usr/bin/env python3
"""polaris#11 — ONE registry of the section names this package expects, and one rule for matching
them. Before this, `state_upsert`, `_brief_parts` and `recent_context` each compiled a heading of
their own, so they disagreed about the live cockpit: the writer appended a thread below the
section's `Owner:` line while the brief reported the section missing.

A host heads its own sections. A heading QUALIFIES a declared name when it continues after a dash,
a colon or a parenthesis — never after a bare space. So `## Open — thread vivi` IS `## Open`,
`## Active Priorities` is NOT `## Active`, and a renamed or translated heading (`# Priorità
attive`) is a different contract: reported missing, never silently aliased.

The template `templates/repo-contract/state/current.md` writes exactly these names and states the
same rule in its own contract footer, so the file a host copies and the code that reads it cannot
drift apart.
"""
from __future__ import annotations

import functools
import re

SECTIONS = {"current.md": ("## Active Priorities", "## Open", "## Recent Context"),
            "todos.md": ("## Active", "## Completed", "## Follow-ups")}
QUALIFIER = r"(?:[ \t]*[—–:(-].*)?[ \t]*$"


@functools.lru_cache(maxsize=None)
def heading(name: str) -> re.Pattern:
    """The matcher for one declared name, at any heading level.

    Cached, so two callers asking for the same section hold the SAME object: that identity is
    what proves there is one registry and not four copies that happen to agree today.
    """
    return re.compile(rf"^#{{1,6}}[ \t]+{re.escape(name.lstrip('# ').strip())}{QUALIFIER}", re.I)


def _selfcheck() -> int:
    """The qualifier rule, both ways, plus the identity the readers assert on."""
    ok = [bool(heading("## Open").match("## Open — thread vivi")),
          bool(heading("## Open").match("# Open (repo)")),
          bool(heading("## Open").match("## Open")),
          heading("## Open").match("## Opening moves") is None,
          heading("## Active").match("## Active Priorities") is None,
          heading("## Active Priorities").match("# Priorità attive") is None,
          heading("## Open") is heading("## Open"),
          set(SECTIONS) == {"current.md", "todos.md"}]
    print(f"state_sections selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selfcheck())
