# Slug normalization

`slug(text)` lowercases ASCII letters, preserves ASCII digits and replaces each maximal run
of other characters with one hyphen. Strip end hyphens; return `item` if nothing remains.
