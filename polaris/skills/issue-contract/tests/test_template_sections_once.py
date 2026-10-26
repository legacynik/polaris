"""When the repo template carries the dedup and adversarial fields, the issue says each once.

Field report 2026-10-09: the builder also appended its own `## Not a duplicate because` and
`## Adversarial verification` blocks under a template that already asks for both, so every issue
created on that repo carried the two sections twice.
"""

from __future__ import annotations

import re

from test_template_contract_fields import run_builder


def test_dedup_and_adversarial_sections_appear_once():
    body = run_builder().stdout
    heads = re.findall(r"^#+ (Not a duplicate because|Adversarial verification.*)$", body, re.M)
    assert heads == ["Not a duplicate because", "Adversarial verification (run before merge/deploy)"], body
