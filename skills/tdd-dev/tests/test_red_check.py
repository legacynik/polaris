"""Un RED vale solo se la FIRMA del runner e' nell'output (#373).

`cd does-not-exist && pytest` esce 1 dalla shell builtin e pytest non parte mai; una
directory chiamata "parser error fixtures … failed passed" mette `failed` dentro
l'errore di `cd`; buildkit e make scrivono `FAILED ` a inizio riga senza essere runner.
Si registra ROSSO se e solo se una riga ANCORATA del runner prova che e' partito e che
ha riportato fallimenti. Le fixture sotto `fixtures/` sono output veri (cargo e le tre
forme ostili simulati, vedi PROVENANCE.md): il nome porta exit code e verdetto atteso.
"""
import argparse
import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
import pytest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "red_check.py"
_spec = importlib.util.spec_from_file_location("red_check", SCRIPT)
if _spec is None or _spec.loader is None:
    raise AssertionError(f"red_check.py non si risolve a {SCRIPT} — il gate sotto test "
                         "manca, e questo si riporta, non si ignora")
red_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(red_check)
# LO STESSO modulo che usa red_check: il monkeypatch deve colpire la costante viva.
red_signatures = red_check.red_signatures

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ROSSO = "python3 -m pytest t.py"        # un test che fallisce davvero
VERDE = "python3 -m pytest ok.py"       # un test che passa davvero
VUOTO = "python3 -m pytest vuoto.py"    # nessun test raccolto, exit 5
# L'oracolo: una riga che stampa SOLO pytest quando parte davvero, e che non e'
# fra le firme sotto test — altrimenti il test misurerebbe se stesso.
PARTITO = "test session starts"

# Negativi condivisi, mai una riga: dal contratto, dal critic (buildkit/make/git push)
# e dal breaker (output di runner vero, processo ucciso).
NEGATIVI = (
    ("syntax error della shell", '( python3 -m pytest t.py'),
    ("dir con 'failed passed' nel nome", 'cd "parser error fixtures … failed passed" && pytest'),
    ("errore in stile compilatore", 'echo "1 error generated." && exit 1'),
    ("npm ci in docker", 'printf "FAILED [1/3] RUN npm ci\\nERROR: failed to solve\\n"; exit 1'),
    ("target di make", 'printf "FAILED build/step-3\\n"; exit 2'),
    ("git push rifiutato", 'printf "FAILED to push some refs\\n"; exit 1'),
    ("ucciso da segnale", 'printf "FAILED t.py::a\\n1 failed in 0.01s\\n"; exit 137'),
)


def _casi():
    """Ogni fixture: (runner, testo, exit code, verdetto atteso) dal suo NOME."""
    for p in sorted(FIXTURES.glob("*__exit*__*.txt")):
        runner, _caso, code, atteso = p.stem.split("__")
        yield runner, p.read_text(encoding="utf-8"), int(code[4:]), atteso


def _param(filtro=None):
    return [pytest.param(*c[1:], id=f"{c[0]}-{i}") for i, c in enumerate(_casi())
            if filtro in (None, c[0])]


RUNNER = sorted({c[0] for c in _casi()})


def _etichetta(rosso):
    return "blocco" if rosso is None else ("rosso" if rosso else "verde")


@pytest.fixture
def lab(tmp_path, monkeypatch):
    """Una cartella con un rosso vero, un verde vero e un file senza test."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "t.py").write_text("def test_a():\n    assert False\n", encoding="utf-8")
    (tmp_path / "ok.py").write_text("def test_b():\n    pass\n", encoding="utf-8")
    (tmp_path / "vuoto.py").write_text("", encoding="utf-8")
    return tmp_path


def _record(lab, cmd, out="r.jsonl"):
    ns = argparse.Namespace(test="t.py::a", cmd=cmd, out=str(lab / out))
    return red_check.cmd_record(ns), lab / out


def _last(log):
    return json.loads(log.read_text(encoding="utf-8").splitlines()[-1])


# --- AC1 · ogni firma su output vero, piu' i tre negativi condivisi -----------
@pytest.mark.parametrize("testo,code,atteso", _param())
def test_il_verdetto_e_quello_del_runner(testo, code, atteso):
    rosso, causa = red_signatures.verdetto(testo, code)
    assert _etichetta(rosso) == atteso
    assert bool(causa) is (rosso is None), "un blocco senza causa non si diagnostica"


@pytest.mark.parametrize("etichetta,cmd", NEGATIVI)
def test_i_negativi_condivisi_non_lasciano_righe(lab, etichetta, cmd):
    rc, log = _record(lab, cmd)
    assert rc == 2, f"{etichetta}: un guasto d'ambiente non e' un rosso"
    assert not log.is_file(), f"{etichetta}: il log non deve avere righe"


# --- AC2 · la costante delle firme e' portante, non decorativa ----------------
@pytest.mark.parametrize("mutante", [("test",), (" failed",)])
@pytest.mark.parametrize("runner", RUNNER)
def test_una_firma_generica_fa_cadere_ogni_runner(monkeypatch, runner, mutante):
    """Con un substring nudo al posto delle firme deve cadere almeno un caso per
    runner: e' la prova che il giro 2 non aveva (con `_AVVIO = ("test",)` restavano
    verdi 15 test su 16)."""
    monkeypatch.setattr(red_signatures, "RUNNER_SIGNATURES", mutante)
    caduti = [p for p in _param(runner)
              if _etichetta(red_signatures.verdetto(p.values[0], p.values[1])[0])
              != p.values[2]]
    assert caduti, f"{runner}: con firme {mutante} nessun caso cambia verdetto"


# --- AC3 · la verita' e' la shell misurata, non il dialetto ipotizzato --------
@pytest.mark.parametrize("etichetta,forma", [
    ("dir creata dal comando", f"mkdir -p d && cd d && python3 -m pytest ../t.py"),
    ("cd fallito ma separato da ;", f"cd nope; {ROSSO}"),
    ("sottoshell", f"( cd nope && {ROSSO} )"),
    ("pushd", f"pushd nope && {ROSSO}"),
    ("cd - senza OLDPWD", f"unset OLDPWD; cd - && {ROSSO}"),
])
@pytest.mark.parametrize("shell", [x for x in ("bash", "dash", "sh") if shutil.which(x)])
def test_il_verdetto_concorda_con_l_oracolo(lab, shell, etichetta, forma):
    cmd = f"{shell} -c {shlex.quote(forma)}"
    prova = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=lab)
    partito = PARTITO in prova.stdout + prova.stderr
    rc, log = _record(lab, cmd, out=f"{shell}-{etichetta}.jsonl")
    assert (rc == 0) is partito, f"{shell}/{etichetta}: verdetto contro output reale"
    assert log.is_file() is partito, f"{shell}/{etichetta}: righe senza il runner"
    if partito:
        assert _last(log)["rosso"] is True


def test_il_messaggio_nomina_la_causa(lab, capsys):
    # la diagnostica esatta cambia con la shell; la riga che l'ha uccisa no
    _record(lab, f"cd non-esiste-mai && {ROSSO}")
    err = capsys.readouterr().err
    assert "non-esiste-mai" in err


def test_pytest_parte_ma_non_raccoglie_test(lab):
    rc, log = _record(lab, VUOTO)  # ha parlato, ma un rosso senza test non prova nulla
    assert rc == 2 and not log.is_file()


@pytest.mark.parametrize("etichetta,cmd", [
    ("pytest nudo", ROSSO),
    ("pytest -q", f"{ROSSO} -q"),
    ("cd verso una dir reale", f"cd . && {ROSSO}"),
    ("path quotato con spazi", 'mkdir -p "con spazi" && cd "con spazi" && '
                              'python3 -m pytest ../t.py'),
])
def test_un_rosso_vero_resta_rosso(lab, etichetta, cmd):
    rc, log = _record(lab, cmd)
    assert rc == 0, etichetta
    assert _last(log)["rosso"] is True and _last(log)["exit"] != 0, etichetta


def test_un_verde_vero_si_registra(lab):
    """Il gate serve anche il GREEN: bloccarlo romperebbe verify a meta' ciclo."""
    rc, log = _record(lab, VERDE)
    assert rc == 0 and _last(log)["rosso"] is False


@pytest.mark.parametrize("caso", json.loads(
    (FIXTURES / "verify_casi.json").read_text(encoding="utf-8")), ids=lambda c: c["nome"])
def test_verify_boccia_ogni_log_che_non_prova_il_ciclo(tmp_path, caso):
    """Le forme di log su cui verify dice FAIL, e le due su cui dice PASS. Stavano
    nel --selfcheck, che il contratto tiene sotto le 200 righe: la tabella e' in
    fixtures/, il ramo lo esercita qui."""
    log = tmp_path / "v.jsonl"
    if caso.get("raw") is not None:
        log.write_text(caso["raw"], encoding="utf-8")
    elif caso.get("log") is not None:
        log.write_text("".join(json.dumps(x) + "\n" for x in caso["log"]), encoding="utf-8")
    ns = argparse.Namespace(log=str(log), test="t.py::a", suite_cmd=caso.get("suite_cmd"))
    assert red_check.cmd_verify(ns) == caso["atteso"], caso["nome"]


def test_la_cli_registra_davvero(lab):
    """B1: la collisione argparse su dest='cmd' era invisibile al Namespace a mano."""
    out = lab / "cli.jsonl"
    for azione, cmd, campo in (("record", ROSSO, "rosso"), ("suite", VERDE, "suite")):
        r = subprocess.run([sys.executable, str(SCRIPT), azione, "--test", "t.py::a",
                            "--cmd", cmd, "--out", str(out)],
                           capture_output=True, text=True, cwd=lab)
        assert r.returncode == 0, f"{azione}: {r.stderr}"
        assert _last(out)[campo] is True, azione


def test_suite_eredita_lo_stesso_guard(lab):
    """cmd_suite passa dallo stesso _run: l'invariante vale per tutti i chiamanti."""
    ns = argparse.Namespace(test="t.py::a", cmd=f"cd non-esiste-mai && {VERDE}",
                            out=str(lab / "s.jsonl"))
    assert red_check.cmd_suite(ns) == 2
    assert not (lab / "s.jsonl").is_file()
