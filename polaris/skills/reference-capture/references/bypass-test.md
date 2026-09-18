---
title: Bypass test — reference-capture
description: Cases that must block before a reference can enter the generated catalog.
status: draft
---

# Bypass test — reference-capture

Gate: `../scripts/reference_catalog.py`. Run the bundled self-check:

```bash
python3 reference-capture/scripts/reference_catalog.py --selfcheck
```

It must exit `0` only after proving all of these branches:

1. three valid `note|study|deep` dossiers across two repo paths generate one catalog;
2. duplicate normalized `source_url` across repos exits `1` and names both files;
3. `reference_status: verified` without `source_version` exits `1`;
4. `reference_status: verified` without `last_verified_at` exits `1`;
5. an unknown relevance value exits `1`;
6. a repository path containing spaces produces a resolvable Markdown link;
7. a Markdown file without `catalog: true` is ignored;
8. any validation failure leaves the prior catalog unchanged.
9. `--lookup` finds a legacy `source:` owner before a new dossier is written;
10. `--lookup` returns collision when legacy and admitted pages claim the same source.

If any of cases 2–5 writes a catalog or exits `0`, the gate is bypassable. If case 8 truncates the
old catalog before reporting failure, the generator can destroy the last usable index and is not
safe to install. If cases 9–10 fail, legacy pages can be duplicated during migration.
