# Documents

Where each kind of document lives, who writes it, and what happens to it when it stops being
true. The repository's `config.yml` `outputs:` map declares where each kind goes; skills read the
map and never invent a path.

## The map

| Kind | Path | Written by |
|---|---|---|
| plan | `docs/modules/<area>/plans/`, in `open/` or `done/` by status (see [plan-file.md](plan-file.md)) | `grill`, `plan-area` |
| spec | `docs/modules/<area>/specs/<date>-<slug>.md` | by hand, when a contract outgrows its plan; no skill owns it yet |
| audit · review | `docs/modules/<area>/audits/` · `reviews/` | `architecture audit`, `review` |
| validation | `docs/modules/<area>/validation/<date>-<scope>.md` | `real-testing`, field tests |
| diagram | `docs/modules/<area>/diagrams/<name>.<type>.json` (rendered `.html` beside it) | `architecture`, `archify` |
| decision | `decisions/DEC-<workspace>-<key>-NNN.md` | `/architecture decide` |
| architecture · domain · glossary | `ARCHITECTURE.md` · `DOMAIN.md` · `CONTEXT.md` at the root | `architecture doc`, `domain` |
| lesson | `records/` (fixed by the script, not by the map) | `scripts/lesson_record.py` only |
| superseded document | `docs/modules/<area>/archive/` | the skill that replaces it |

A repository may use `docs/areas/` instead of `docs/modules/`; the map says which.

## Areas

An area is a stable part of the system that outlives any one piece of work: a capability that spans
many sessions and pull requests. Each area folder has:

- `README.md`: the restart address: scope, where to start, what the area does not own;
- `<area>.md`: the area's main document, what is true now about the area;
- `module-context.json`: the exact files an agent loads by default for this area;
- `CHANGELOG.md`: accepted changes, linked to their evidence;
- `plans/`, `specs/`, `validation/`, `diagrams/`, `archive/`, only when they hold real material.

A bounded feature, a bug or a mechanical change does not get an area. Generic file names such as
`PRD.md` are not allowed, because they become ambiguous in search and in the context pack.

## The live documents

Three root documents describe the repository as it is now. They are loaded into every context pack.

| Document | Owns |
|---|---|
| `CONTEXT.md` | the language: every term with one meaning |
| `ARCHITECTURE.md` | a high-level map: the main components, their boundaries, the invariants, by name |
| `DOMAIN.md` | the domains and components, with stable ids that decisions refer to |

`ARCHITECTURE.md` is a map, not an inventory: it names files and boundaries, never every function.

## How a document ages

1. **Born** in its area, at the path the map gives.
2. **Absorbed.** When a plan closes, whatever it proved moves into the area's main document; the
   plan moves to `done/`. A spec whose content is absorbed goes to `archive/`.
3. **Archived, never deleted.** A document whose claims no longer hold moves to `archive/`. It
   stays listed in the area README, struck through, and is never loaded by default.

## What is checked

- A path a document cites must exist when the document is read. A missing path makes that row
  `STALE` in the context pack, and `check_context_backbone.py --check` exits 2 with
  `CITED_PATH_MISSING`. No hash is stored and nothing needs resealing.
- `skill_outputs_check.py` refuses a skill that writes a document kind the map does not declare.
