#!/usr/bin/env python3
"""Shim: the backbone checker lives in the architecture skill's `scripts/`.

This file stays so every `import check_context_backbone` and every
`python3 scripts/check_context_backbone.py ...` keeps working. It resolves the skill's copy in the
vault layout (`architecture/scripts/`), the package layout
(`skills/architecture/scripts/`) or, shipped inside another skill's `scripts/`, the sibling
installed skill (`<skills>/architecture/scripts/`), registers it under this module's name and runs it, so importers
get the real module object: private names and monkeypatching behave exactly as before. Run as a
script, the real file's own `__main__` block runs `main()`, `--selfcheck` included.
"""

import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CANDIDATES = tuple(base / "architecture" / "scripts" / "check_context_backbone.py"
                    for base in (_HERE.parent / "skills-suite", _HERE.parent / "skills",
                                 _HERE.parent.parent))
_SOURCE = next((path for path in _CANDIDATES if path.is_file()), None)
if _SOURCE is None:
    raise ImportError("check_context_backbone: the architecture skill's copy is missing; looked at "
                      + ", ".join(str(path) for path in _CANDIDATES))
_SPEC = importlib.util.spec_from_file_location(__name__, _SOURCE)
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[__name__] = _MODULE
_SPEC.loader.exec_module(_MODULE)
# A loader that kept this file's module object (spec_from_file_location under another name)
# still sees every name.
globals().update({k: v for k, v in vars(_MODULE).items() if not k.startswith("__")})
