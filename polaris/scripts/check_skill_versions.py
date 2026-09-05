#!/usr/bin/env python3
"""Una skill cambiata senza che la sua versione cambi e' una versione che mente.

`#20` e `#21` hanno toccato sette skill e non ne hanno alzata nessuna: il pacchetto dichiarava
`start 1.5.0` mentre spediva uno `start` diverso, e chi confronta due installazioni per versione
concludeva che fossero uguali.

    python3 polaris/scripts/check_skill_versions.py <base-ref>     # 0 pulito · 1 versioni ferme · 2 input inutilizzabile
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

VERSION = re.compile(r"^version:\s*(\S+)\s*$", re.M)


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], capture_output=True, text=True)
    if done.returncode:
        print(f"UNUSABLE: git {' '.join(args)}: {done.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    return done.stdout


def touched_skills(base: str) -> set[str]:
    names = set()
    for line in git("diff", "--name-only", f"{base}..HEAD", "--", "polaris/skills").splitlines():
        parts = line.split("/")
        if len(parts) > 2:
            names.add(parts[2])
    return names


def version_at(ref: str, skill: str) -> str | None:
    done = subprocess.run(["git", "show", f"{ref}:polaris/skills/{skill}/SKILL.md"],
                          capture_output=True, text=True)
    if done.returncode:
        return None                      # skill nuova: nessuna versione precedente da confrontare
    found = VERSION.search(done.stdout)
    return found.group(1) if found else None


def stale(base: str) -> list[str]:
    out = []
    for skill in sorted(touched_skills(base)):
        was, now = version_at(base, skill), version_at("HEAD", skill)
        if now is None:
            out.append(f"{skill}: nessun campo `version:`")
        elif was is not None and was == now:
            out.append(f"{skill}: toccata e ferma a {now}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base", help="ref di partenza, es. il tag dell'ultimo rilascio")
    args = ap.parse_args()
    frozen = stale(args.base)
    if frozen:
        print(f"FERME — {len(frozen)} skill cambiate senza alzare la versione:")
        for row in frozen:
            print(f"  - {row}")
        return 1
    print(f"OK — ogni skill toccata da {args.base} ha alzato la sua versione")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
