#!/usr/bin/env python3
"""red_signatures.py — chi decide se un esito e' un ROSSO: la firma del runner.

#373, terzo giro. Un exit non-zero non prova niente. `cd nope && pytest` esce 1
dalla shell builtin; `( pytest` esce 2 con `bash: syntax error`; una directory
chiamata "parser error fixtures … failed passed" mette la parola `failed` dentro
il messaggio di `cd`. Cercare substring nudi nell'output ha lo stesso difetto di
leggerli nel comando: ogni firma qui e' ANCORATA a inizio riga e nomina il runner
che la stampa, e ogni riga d'esempio nel commento e' output catturato davvero
(vedi ../tests/fixtures/PROVENANCE.md).

Si registra ROSSO se e solo se una voce di RUNNER_SIGNATURES combacia sull'esito
misurato: il runner e' partito E ha riportato dei fallimenti. Il verde vuole la
stessa prova al contrario, perche' `verify` si appoggia anche a quello. Tutto il
resto e' un blocco con la causa, mai una riga nel log.

Exit: 0 selfcheck verde · 1 selfcheck rosso.
"""
import re
import sys
from pathlib import Path

# (runner, firme di FALLIMENTO, firme di PASSAGGIO). Dentro una voce le regex si
# SOMMANO — tutte devono comparire; le alternative stanno dentro la singola regex.
# Un runner nuovo si AGGIUNGE qui con la sua riga vera, non si deduce.
RUNNER_SIGNATURES = (
    # pytest   "FAILED t_fail.py::test_add - assert (1 + 1) == 3"
    #          "======== 1 failed in 0.01s ========"  ·  verde: "== 1 passed in 0.00s =="
    # `FAILED ` nudo non basta: buildkit scrive "FAILED [1/3] RUN npm ci", make
    # "FAILED build/step-3", un wrapper di git "FAILED to push some refs". Il node id
    # con `::` e' quello che solo pytest stampa (critic su d6c1694).
    ("pytest",
     (r"^(?:=+ )?(?:FAILED \S+::|\d+ failed\b.* in [\d.]+s)",),
     (r"^(?:=+ )?\d+ passed\b.* in [\d.]+s",)),
    # unittest "Ran 1 test in 0.000s" + "FAILED (failures=1)"  ·  verde: + "OK"
    ("unittest",
     (r"^Ran \d+ tests? in ", r"^FAILED \("),
     (r"^Ran \d+ tests? in ", r"^OK\b")),
    # vitest   " Test Files  1 failed (1)" / "      Tests  1 failed (1)"
    #          verde: "      Tests  1 passed (1)"
    ("vitest",
     (r"^\s*(?:Test Files|Tests)\s+\d+ failed\b",),
     (r"^\s*Tests\s+\d+ passed\b",)),
    # jest     "Tests:       1 failed, 1 total"  ·  verde: "Tests:       1 passed, 1 total"
    ("jest",
     (r"^Tests:.*\b\d+ failed\b",),
     (r"^Tests:.*\b\d+ passed\b",)),
    # go       "--- FAIL: TestAdd (0.00s)" + "FAIL\texample\t0.631s"  ·  verde: "ok  \texample"
    # Le due righe insieme: un build rotto stampa "FAIL\texample [setup failed]"
    # senza nessun "--- FAIL:", e non e' un test fallito.
    ("go",
     (r"^--- FAIL: ", r"^FAIL\t"),
     (r"^ok\s+\S",)),
    # cargo    "test result: FAILED. 0 passed; 1 failed; ..."  ·  verde: "test result: ok."
    ("cargo",
     (r"^test result: FAILED\.",),
     (r"^test result: ok\.",)),
)

# Il runner ha parlato ma non c'e' nessun test fallito da registrare: causa
# esplicita, non un rosso. Si controlla PRIMA delle firme.
_BLOCCO = (
    (r"^(?:=+ )?no tests ran\b", "pytest non ha raccolto nessun test"),
    (r"^Ran 0 tests?\b", "unittest non ha eseguito nessun test"),
    (r"^running 0 tests\b", "l'harness non ha eseguito nessun test"),
    (r"^\s*Tests\s+no tests\b", "vitest non ha eseguito nessun test"),
    (r"^(?:=+ )?\d+ errors? in [\d.]+s",
     "errore di collection: il runner non e' arrivato a eseguire i test"),
)
# Codici che il runner stesso riserva a "non ho eseguito niente".
_CODICI = {4: "errore d'uso del runner (exit 4): il comando non e' arrivato ai test",
           5: "pytest non ha raccolto nessun test (exit 5)"}
_IMPORT = re.compile(r"\b(?:ImportError|ModuleNotFoundError)\b")


def coda(out: str, n: int = 3) -> str:
    """Le ultime righe non vuote: li' sta cio' che ha ucciso il comando."""
    righe = [r.strip() for r in out.splitlines() if r.strip()]
    return " · ".join(righe[-n:]) if righe else "nessun output"


def _voce(voce, code: int):
    """Nome e regex della voce per l'esito misurato.

    Una voce-stringa e' una firma nuda: la usano solo i test di mutation, per
    provare che e' QUESTA costante a decidere e non il caso.
    """
    if isinstance(voce, str):
        return "mutante", (voce,)
    return voce[0], voce[1] if code else voce[2]


def firma(out: str, code: int) -> str:
    """Il runner la cui firma compare nell'output per questo esito, o ''."""
    for voce in RUNNER_SIGNATURES:
        nome, righe = _voce(voce, code)
        if all(re.search(rx, out, re.M) for rx in righe):
            return nome
    return ""


def _blocco(out: str, code: int) -> str:
    """La causa per cui questo esito non si registra, o '' se si puo' valutare."""
    if code >= 128 or code < 0:
        # Il processo e' morto di segnale (OOM killer, SIGSEGV, timeout che manda
        # SIGKILL): l'output puo' contenere la firma di un runner ed essere comunque
        # troncato a meta'. Negativo = shell assente, 128+n = riportato dalla shell.
        return f"KILLED_BY_SIGNAL {-code if code < 0 else code - 128}: il processo e' stato " \
               "ucciso, l'output non prova un fallimento di test"
    if code in _CODICI:
        return _CODICI[code]
    for rx, causa in _BLOCCO:
        if re.search(rx, out, re.M):
            return causa
    if _IMPORT.search(coda(out)):
        return f"import fallito prima dei test — {coda(out)}"
    return ""


def verdetto(out: str, code: int):
    """(True rosso | False verde | None blocco, causa).

    None e' l'unico esito che non si registra: la causa dice perche', e chi
    chiama esce 2 senza scrivere righe.
    """
    causa = _blocco(out, code)
    if causa:
        return None, causa
    if firma(out, code):
        return code != 0, ""
    return None, (f"nessuna firma di runner nell'output (exit {code}): l'esito e' "
                  f"dell'ambiente, non di un test — {coda(out)}")


def _fixtures():
    """(nome, runner, testo, code, atteso) da ../tests/fixtures. Il nome del file
    E' l'aspettativa: <runner>__<caso>__exit<N>__<rosso|verde|blocco>.txt"""
    d = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
    casi = sorted(d.glob("*__exit*__*.txt")) if d.is_dir() else []
    if not casi:
        raise SystemExit(f"corpus delle fixture assente o vuoto: {d} — senza output "
                         "veri questo selfcheck non prova niente")
    for p in casi:
        runner, _caso, code, atteso = p.stem.split("__")
        yield p.stem, runner, p.read_text(encoding="utf-8"), int(code[4:]), atteso


def _etichetta(rosso) -> str:
    return "blocco" if rosso is None else ("rosso" if rosso else "verde")


def _selfcheck() -> int:
    """AC1 (ogni firma su output vero) e AC2 (le firme sono portanti) del #373."""
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + msg)
        ok = ok and cond

    casi = list(_fixtures())
    for nome, _runner, testo, code, atteso in casi:
        rosso, causa = verdetto(testo, code)
        check(_etichetta(rosso) == atteso and bool(causa) is (rosso is None),
              f"{nome} -> {atteso}")
    globale = RUNNER_SIGNATURES
    for mutante in (("test",), (" failed",)):
        for runner in sorted({c[1] for c in casi}):
            caduti = _mutazione(casi, runner, mutante)
            check(caduti > 0, f"firme {mutante}: {runner} cade su {caduti} casi")
    check(RUNNER_SIGNATURES is globale, "la costante e' ripristinata dopo la mutation")
    check(len(RUNNER_SIGNATURES) <= 12, f"{len(RUNNER_SIGNATURES)} voci <= 12")
    print("SELFCHECK OK" if ok else "SELFCHECK ROSSO")
    return 0 if ok else 1


def _mutazione(casi, runner: str, mutante) -> int:
    """Quanti casi di questo runner cambiano verdetto con una firma generica."""
    global RUNNER_SIGNATURES
    vere, RUNNER_SIGNATURES = RUNNER_SIGNATURES, mutante
    try:
        return sum(1 for _n, r, testo, code, atteso in casi
                   if r == runner and _etichetta(verdetto(testo, code)[0]) != atteso)
    finally:
        RUNNER_SIGNATURES = vere


if __name__ == "__main__":
    if "--selfcheck" not in sys.argv[1:]:
        print(__doc__.strip().splitlines()[0])
        print("uso: red_signatures.py --selfcheck", file=sys.stderr)
        sys.exit(2)
    sys.exit(_selfcheck())
