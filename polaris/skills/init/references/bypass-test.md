# Bypass-test — init installed without a vault

## B1 — a collaborator who has only the installed skills

**Before** (`fails_before`, 2026-10-23). A skills-CLI install copies `init/` and `architecture/`
side by side and nothing else. Run from that layout, the scripts could not start, and once they
could, `apply` pointed the host repository at the skill folder:

```text
ImportError: check_context_backbone: the architecture skill's copy is missing; looked at
.../skills/init/skills-suite/architecture/scripts/check_context_backbone.py,
.../skills/init/skills/architecture/scripts/check_context_backbone.py
```

The skill body stopped earlier still: Step 1 required `git config polaris.vault` to name a vault
that the package never ships, so for a collaborator init did nothing at all.

**After.** The checker shim also looks for the sibling installed `architecture` skill. With no
vault, `VAULT_UNDECLARED` blocks nothing, `apply` writes no `polaris.vault`, and the result
reports `"vault": null`. Only the ContextPack check is skipped, with one line.

Proof: `scripts/test/test_polaris_init_installed.py` (red, then green, recorded by `red_check.py`
in `state/tdd/init-installed-no-vault.jsonl`). An installed copy proves the same path with
`polaris_init.py --selfcheck`, which runs a fixture repository through audit and apply when the
test battery is not there.
