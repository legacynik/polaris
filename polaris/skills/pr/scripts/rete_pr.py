"""rete_pr — every read controlla_pr makes on GitHub, through one `gh` runner (used by controlla_pr)."""
from __future__ import annotations

import json
import re
import subprocess

IMMAGINE = re.compile(r"(?:github\.com/([\w.-]+/[\w.-]+)/(?:blob|raw)|raw\.githubusercontent\.com/([\w.-]+/[\w.-]+))"
                      r"/([0-9a-f]{7,40})/([^\s)\"'?#]+)")
RICEVUTA = re.compile(r"(?mi)^\|\s*real[- ]?test\s*\|(.*)$")
SHA = re.compile(r"(?i)(?<![0-9a-z])[0-9a-f]{7,40}(?![0-9a-z])")
LETTURA = (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError, KeyError,
           TypeError, AttributeError)  # a null or wrongly shaped reply: «cannot check», never a traceback


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def issue(n: int, repo: str | None) -> dict:
    """`{testo, pr}`: body and comments in order, and whether `#n` is a pull request (its URL says so)."""
    dati = intero(gh("issue", "view", str(n), "--json", "body,comments,url", *(["--repo", repo] if repo else [])),
                  "comments,url")
    testo = "\n".join([dati["body"] or "", *(c.get("body") or "" for c in dati["comments"])])
    return {"testo": testo, "pr": "/pull/" in dati.get("url", "")}


def intero(uscita: str, campi: str) -> dict:
    """The JSON object gh printed, with every field asked for present: else KeyError, «cannot check»."""
    dati = json.loads(uscita)
    mancano = [c for c in campi.split(",") if not isinstance(dati, dict) or dati.get(c) is None]
    if mancano:
        raise KeyError(f"gh non ha restituito {', '.join(mancano)}")
    return dati


def pr(n: str, repo: str | None, campi: str) -> dict:
    # ponytail: `--json files` stops at 100 files; a wider PR is judged on its first 100
    return intero(gh("pr", "view", str(n), "--json", campi, *(["--repo", repo] if repo else [])), campi)


def immagini_mancanti(corpo: str) -> list[str]:
    """Every image pinned to a commit must open. A failed read is «not found» only when the repository
    itself answers; when it does not either, the error propagates: the network, not the link."""
    out = []
    for blob, raw, sha, path in dict.fromkeys(IMMAGINE.findall(corpo)):
        try:
            gh("api", "--silent", f"repos/{blob or raw}/contents/{path}?ref={sha}")
        except subprocess.CalledProcessError:
            gh("api", "--silent", f"repos/{blob or raw}")
            out.append(f"immagine {path} non trovata su {blob or raw} al commit {sha[:7]}: il link non si apre")
    return out


def avviso_ricevuta(corpo: str, head: str) -> list[str]:
    """The control table's Real-test row names its SHA; one that is not the head must say the head."""
    m = RICEVUTA.search(corpo)
    shas = [s.lower() for s in SHA.findall(m.group(1))] if m else []
    if not shas or any(head.startswith(s) for s in shas):
        return []
    return [f"Real-test: ricevuta su {shas[0]}, la head è {head[:7]}: scrivi nella riga "
            f"«head `{head[:7]}`, N commit dopo», o firma di nuovo sulla head"]


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:  # the offline half; the gh reads are exercised by test_controlla_pr_gh
        riga = "| Real-test | verde · `bbbbbbb` |\n"
        ok = avviso_ricevuta(riga, "a" * 40) != [] and avviso_ricevuta(riga, "bbbbbbb" + "0" * 33) == []
        print(f"rete_pr selfcheck: {'ok' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)
