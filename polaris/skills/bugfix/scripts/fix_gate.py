#!/usr/bin/env python3
"""fix_gate.py — il gate per-tappa del workflow FIX.

Exit: 0 PASS · 1 FAIL · 2 errore d'uso · 3 CONCERNS. Fail-closed ovunque:
input assente, vuoto o illeggibile non produce MAI 0.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SORGENTI = {"issue", "log", "segnalazione"}
CECITA = {"bassa", "media", "alta"}
STATI = {"aperto", "fixato", "staging-provato", "prod-verified",
         "sorvegliato", "bloccato", "chiuso"}
CLASSI = {"logica", "frontend", "dati", "integrazione", "infra", "osservabilita",
          "llm", "performance", "concorrenza", "sicurezza", "regressione"}

# Un valore che "c'e' ma non dice niente" e' assente. Senza questo, `dominio: .`
# passa il controllo di presenza — e' il bypass misurato su piano-spec.
VUOTI = {"", ".", "-", "--", "?", "tbd", "todo", "n/a", "na", "none", "null", "<>"}

# Il raggio si vede col GRAPH, sempre (founder 2026-08-17): i chiamanti li
# produce un verbo del code-graph, mai grep — grep trova testo, non riferimenti.
GRAPH_VERBS = re.compile(
    r"find_referencing_symbols|find_symbol|find_implementations|find_declaration"
    r"|trace_path|references|call_hierarchy")


def _flat_yaml(block: str) -> dict:
    """Chiavi scalari e liste. Un livello di annidamento diventa 'padre.figlio'
    — il contratto scrive `test:\\n  suite: ...` e il gate legge `test.suite`.
    Senza questo un contratto che DICHIARA il comando risultava muto (difetto
    trovato il 2026-08-11 facendo giudicare il gate al proprio lavoro)."""
    out, parent = {}, None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        annidata = line.startswith((" ", "\t"))
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.split(" #", 1)[0].strip().strip('"').strip("'")
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
        if annidata:
            if parent:
                out[f"{parent}.{k}"] = v
            continue
        parent = k if v == "" else None   # `test:` senza valore apre un blocco
        out[k] = v
    return out


def read_record(path: Path) -> dict:
    """Frontmatter YAML -> dict. File senza delimitatori: si legge tutto
    (e' il caso di contract.yml). Chiavi assenti restano assenti, mai default."""
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
    return _flat_yaml(m.group(1) if m else text)


def load_contract(repo: Path) -> dict:
    """Contratto per-repo. Assente = {}: la cerimonia non si improvvisa, e
    ogni tappa che ne dipende deve fallire esplicitamente."""
    c = read_record(repo / ".fix" / "contract.yml")
    # `dominii_da` punta a un vocabolario che la repo GIA' mantiene, invece di
    # copiarne i nomi qui: una lista duplicata diverge al primo componente nuovo.
    src = c.get("dominii_da")
    if src and not c.get("dominii"):
        c["dominii"] = _dominii_da_file(repo / str(src))
    return c


def _dominii_da_file(p: Path) -> list:
    """Estrae i nomi da un catalogo JSON. Forma attesa: {"components":[{"name":...}]}
    (il release-component catalog). Illeggibile o vuoto -> [], che fa fallire
    la tappa d'ingresso: meglio nessun vocabolario che uno inventato."""
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    items = data.get("components") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [str(i["name"]) for i in items if isinstance(i, dict) and i.get("name")]


def _sh(cmd, timeout: int) -> subprocess.CompletedProcess:
    """Comandi del CONTRATTO (fiducia = Makefile del repo): shell=True e' deliberato.
    shlex.split senza shell eseguiva /usr/bin/cd (exit 0, ignora tutto) su
    'cd x && pytest' → verde farlocco, fail-open trovato dall'eval 2026-08-17."""
    return subprocess.run(str(cmd), shell=True, capture_output=True, text=True, timeout=timeout)


def _has(rec: dict, key: str) -> bool:
    v = rec.get(key)
    if isinstance(v, list):
        return len(v) > 0
    return v is not None and str(v).strip().lower() not in VUOTI


def _fail(msgs: list) -> int:
    for m in msgs:
        print(f"FAIL: {m}", file=sys.stderr)
    return 1


def stage_ingresso(rec: dict, contract: dict) -> int:
    campi = ("id", "repo", "dominio", "classe", "cecita", "sorgente", "stato")
    missing = [k for k in campi if not _has(rec, k)]
    if missing:
        return _fail([f"campi mancanti o vuoti nel record: {', '.join(missing)}"])
    bad = []
    for key, enum in (("sorgente", SORGENTI), ("cecita", CECITA),
                      ("stato", STATI), ("classe", CLASSI)):
        if rec[key] not in enum:
            bad.append(f"{key} '{rec[key]}' non in {sorted(enum)}")
    dom = contract.get("dominii")
    if isinstance(dom, list) and dom:
        if rec["dominio"] not in dom:
            bad.append(f"dominio '{rec['dominio']}' non nel vocabolario della repo: {dom}")
    else:
        bad.append("contratto senza 'dominii': il vocabolario di dominio non si improvvisa "
                   "(atteso in <repo>/.fix/contract.yml)")
    return _fail(bad) if bad else 0


def stage_riproduzione(rec: dict, contract: dict) -> int:
    """Un comando che PRODUCE il sintomo. Una frase non riproduce niente."""
    if rec.get("cecita") == "bassa":
        return 0  # profilo: la tappa non si accende
    cmd = rec.get("riproduzione")
    if not _has(rec, "riproduzione"):
        return _fail(["'riproduzione' assente: senza un comando non si fixa"])
    if " " not in str(cmd) and "/" not in str(cmd):
        return _fail([f"'riproduzione' non sembra un comando: {cmd!r}"])
    try:
        r = _sh(cmd, 300)
    except subprocess.TimeoutExpired:
        return _fail([f"riproduzione oltre 300s: {cmd!r}"])
    if r.returncode == 127:
        return _fail([f"il comando di riproduzione non esiste (exit 127): {cmd!r} — "
                      "un rosso d'ambiente non riproduce niente"])
    if r.returncode == 0:
        return _fail([f"il comando esce 0: NON riproduce il sintomo ({cmd!r})"])
    return 0


def stage_causa(rec: dict, contract: dict) -> int:
    """La causa e' una riga di codice, non un'opinione. E l'archivio si consulta
    PRIMA (acme-web backend-debug): una recidiva non e' un bug nuovo."""
    if not _has(rec, "ricorrenza"):
        return _fail(["'ricorrenza' assente: l'archivio bug si interroga PRIMA di indagare "
                      "(modulo+eccezione); dichiara l'esito, anche '0 match'"])
    if not _has(rec, "causa_in"):
        return _fail(["la causa deve indicare path:riga in 'causa_in', non solo a parole"])
    loc = str(rec["causa_in"])
    m = re.match(r"^(.+?):(\d+)$", loc)
    if not m:
        return _fail([f"'causa_in' non e' path:riga: {loc!r}"])
    f, n = Path(m.group(1)), int(m.group(2))
    if not f.is_file():
        return _fail([f"'causa_in' punta a un file inesistente: {f}"])
    righe = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
    if n < 1 or n > righe:
        return _fail([f"'causa_in' punta alla riga {n} di un file che ne ha {righe}: {loc}"])
    return 0


def stage_raggio(rec: dict, contract: dict) -> int:
    """Due assi: i chiamanti nel codice, e il lavoro aperto che li interseca.
    I chiamanti si dichiarano COL comando che li ha prodotti (bug-protocol,
    incidente #107: fix al sito primario coi chiamanti mai guardati = fix muto)."""
    errs = []
    chiamanti = rec.get("chiamanti")
    if not _has(rec, "chiamanti"):
        errs.append("'chiamanti' assente: si prendono da Serena, non a occhio. "
                    "Zero chiamanti si dichiara esplicitamente con 'chiamanti: [nessuno]'")
    elif chiamanti != ["nessuno"] and chiamanti != "nessuno":
        if not _has(rec, "chiamanti_cmd"):
            errs.append("'chiamanti_cmd' assente: i chiamanti si PROVANO col comando che li ha "
                        "prodotti (find_referencing_symbols/trace_path), non si elencano a memoria")
        elif not GRAPH_VERBS.search(str(rec["chiamanti_cmd"])):
            errs.append(f"'chiamanti_cmd' non e' un verbo del code-graph: {rec['chiamanti_cmd']!r}"
                        " — il raggio si vede col graph (Serena), MAI a grep: grep trova testo, "
                        "non riferimenti")
    if "issue_prese" not in rec and "issue_lasciate" not in rec:
        errs.append("il raggio ha due assi: dichiara 'issue_prese' e 'issue_lasciate' "
                    "(anche vuote, ma dichiarate)")
    return _fail(errs) if errs else 0


def stage_deposito(rec: dict, contract: dict) -> int:
    """Senza rilevatore, una finestra di sorveglianza e' attesa, non sorveglianza."""
    NON_DETERMINISTICHE = {"llm", "osservabilita", "concorrenza", "performance", "integrazione"}
    if rec.get("classe") not in NON_DETERMINISTICHE:
        return 0
    errs = []
    if not _has(rec, "osserva_fino_a"):
        errs.append(f"classe '{rec.get('classe')}' e' non deterministica: "
                    "'osserva_fino_a' e' obbligatorio")
    if not _has(rec, "segnale") and not _has(rec, "blocca_su"):
        errs.append("senza 'segnale' la finestra e' vietata: dichiara il COMANDO rilevatore, "
                    "oppure 'blocca_su' con la ragione")
    return _fail(errs) if errs else 0


def stage_rosso(rec: dict, contract: dict) -> int:
    """Il rosso si REGISTRA, non si dichiara. Lo verifica la porta tdd-dev."""
    errs = []
    if not _has(rec, "test"):
        errs.append("'test' assente: il rosso si prova su un test nominato (node id)")
    if not _has(rec, "rosso_log"):
        errs.append("'rosso_log' assente: il rosso si registra con red_check.py record")
    if errs:
        return _fail(errs)
    tr = contract.get("tdd_dev") or contract.get("tdd_red")  # compat: old product contracts
    if not tr:
        return _fail(["contratto senza 'tdd_dev': il verificatore del rosso non si improvvisa"])
    checker = Path(str(tr)) / "scripts" / "red_check.py"
    if not checker.is_file():
        return _fail([f"tdd-dev non trovato in {tr} (atteso scripts/red_check.py)"])
    r = subprocess.run([sys.executable, str(checker), "verify",
                        "--log", str(rec["rosso_log"]), "--test", str(rec["test"])],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return _fail([r.stderr.strip() or "red_check verify ha rifiutato"])
    return 0


def stage_raccolto(rec: dict, contract: dict) -> int:
    """R5: un test committato che nessun workflow CI raccoglie e' ORFANO — protegge
    solo chi lo lancia a mano. Il raccolto si prova col comando di raccolta della CI."""
    if not _has(rec, "test"):
        return _fail(["'test' assente: il raccolto si prova su un test nominato (node id)"])
    collect = contract.get("ci.collect")
    if not collect:
        return _fail(["contratto senza 'ci.collect': il comando con cui la CI raccoglie "
                      "i test non si improvvisa"])
    try:
        r = _sh(collect, 600)
    except subprocess.TimeoutExpired:
        return _fail([f"raccolta oltre 600s: {collect!r}"])
    if r.returncode == 127:
        return _fail([f"il comando di raccolta non esiste (exit 127): {collect!r}"])
    if r.returncode != 0:
        return _fail([f"la raccolta CI fallisce (exit {r.returncode}): il raccolto non si prova"])
    nodeid, out = str(rec["test"]), r.stdout + r.stderr
    if nodeid not in out and nodeid.split("::")[0] not in out:
        return _fail([f"test ORFANO: {nodeid} non e' raccolto da 'ci.collect' — "
                      "committato, ma la CI non lo eseguira' mai"])
    return 0


def stage_mutazione(rec: dict, contract: dict) -> int:
    """Col bug rimesso i test devono tornare rossi. Altrimenti non valgono niente."""
    if not _has(rec, "mutation_log"):
        return _fail(["'mutation_log' assente: la mutazione si esegue con mutation.py, "
                      "non si dichiara"])
    p = Path(str(rec["mutation_log"]))
    if not p.is_file():
        return _fail([f"'mutation_log' punta a un file inesistente: {p}"])
    try:
        log = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _fail([f"mutation_log illeggibile: {exc}"])
    if not _has(rec, "fix_sha"):
        return _fail(["'fix_sha' assente nel record: senza, il log non e' attribuibile"])
    if log.get("fix_sha") != rec.get("fix_sha"):
        return _fail([f"il mutation_log si riferisce a un altro fix "
                      f"({log.get('fix_sha')} != {rec.get('fix_sha')})"])
    if not log.get("tornato_rosso"):
        return _fail(["col bug rimesso i test restano verdi: non provano niente, riscrivili"])
    return 0


def _thrashing(rec: dict) -> bool:
    """Circuit breaker (superpowers systematic-debugging): >=4 run rossi dello
    stesso test nel rosso_log = stai insistendo su un fix che non regge —
    fermati e questiona l'architettura, non tentare il fix n.4."""
    log = Path(str(rec.get("rosso_log", "")))
    if not log.is_file():
        return False
    reds = 0
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("test") == rec.get("test") and e.get("rosso"):
            reds += 1
    return reds >= 4


def stage_verde(rec: dict, contract: dict) -> int:
    """Il test passa E la suite del modulo pure: nessun danno collaterale."""
    if not _has(rec, "test"):
        return _fail(["'test' assente: il verde si prova su un test nominato"])
    if _thrashing(rec) and not _has(rec, "architettura_riesaminata"):
        return _fail(["CIRCUIT BREAKER: >=4 run rossi dello stesso test — 3+ fix falliti "
                      "non chiedono il fix n.4, chiedono di questionare l'architettura. "
                      "Dichiara 'architettura_riesaminata: <cosa hai concluso>' per procedere"])
    suite = contract.get("test.suite") or contract.get("suite")
    if not suite:
        return _fail(["contratto senza 'test.suite': il comando dei test non si improvvisa"])
    r = _sh(suite, 3600)
    if r.returncode == 127:
        return _fail([f"il comando della suite non esiste (exit 127): {suite!r}"])
    if r.returncode != 0:
        return _fail([f"la suite non passa (exit {r.returncode}): danno collaterale o fix incompleto"])
    return 0


def stage_realtest(rec: dict, contract: dict) -> int:
    """Il verdetto lo da' real-test, che esiste gia'. Qui si propaga il suo rifiuto."""
    rt = contract.get("real_test")
    if not rt:
        return _fail(["contratto senza 'real_test': il perimetro del real-test non si improvvisa"])
    verdict = Path(rt) / "scripts" / "verdict.py"
    if not verdict.is_file():
        return _fail([f"real-test non trovato in {rt} (atteso scripts/verdict.py)"])
    if not _has(rec, "verdict_path"):
        return _fail(["'verdict_path' assente: il real-test si esegue, non si dichiara"])
    vp = Path(str(rec["verdict_path"]))
    if not vp.is_file():
        return _fail([f"'verdict_path' punta a un file inesistente: {vp}"])
    r = subprocess.run([sys.executable, str(verdict), "validate", str(vp),
                        "--repo", str(rec.get("repo_path") or ".")],
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        return _fail([f"verdetto non valido (exit {r.returncode}): "
                      f"{(r.stdout + r.stderr).strip()[:300]}"])
    return 0


def stage_firma(rec: dict, contract: dict) -> int:
    """Una richiesta senza evidenza non e' una richiesta. La firma e' un campo, non un ok a voce."""
    errs = []
    if not _has(rec, "verdict_path"):
        errs.append("'verdict_path' assente: si chiede il deploy portando l'evidenza del real-test, "
                    "non dicendo «e' pronto»")
    elif not Path(str(rec["verdict_path"])).is_file():
        errs.append(f"'verdict_path' punta a un file inesistente: {rec['verdict_path']}")
    if rec.get("firma") != "founder" or not _has(rec, "firmato_il"):
        errs.append("non firmata: servono 'firma: founder' e 'firmato_il'. "
                    "Un ok a voce non e' leggibile da uno script")
    return _fail(errs) if errs else 0


def stage_prod(rec: dict, contract: dict) -> int:
    """«Ho deployato» non e' una prova. L'osservazione ha un exit code."""
    if not _has(rec, "prod_il"):
        return _fail(["'prod_il' assente: prod-verified richiede la data dell'osservazione"])
    osserva = contract.get("prod.osserva") or contract.get("osserva")
    if not osserva:
        return _fail(["contratto senza 'prod.osserva': senza un comando, «ho deployato» "
                      "non e' una prova che il comportamento sia cambiato"])
    r = _sh(osserva, 600)
    if r.returncode == 127:
        return _fail([f"il comando di osservazione non esiste (exit 127): {osserva!r}"])
    if r.returncode != 0:
        return _fail([f"l'osservazione in prod fallisce (exit {r.returncode}): "
                      f"{(r.stderr or r.stdout).strip()[:200]}"])
    return 0


STAGES = {
    "ingresso": stage_ingresso,
    "riproduzione": stage_riproduzione,
    "causa": stage_causa,
    "raggio": stage_raggio,
    "rosso": stage_rosso,
    "verde": stage_verde,
    "raccolto": stage_raccolto,
    "mutazione": stage_mutazione,
    "realtest": stage_realtest,
    "firma": stage_firma,
    "prod": stage_prod,
    "deposito": stage_deposito,
}


def cmd_check(a) -> int:
    if a.stage not in STAGES:
        print(f"stage sconosciuto: {a.stage} (noti: {', '.join(sorted(STAGES))})",
              file=sys.stderr)
        return 2
    p = Path(a.record)
    if not p.is_file():
        print(f"record inesistente: {a.record}", file=sys.stderr)
        return 2
    rec = read_record(p)
    if not rec:
        print(f"record vuoto o senza chiavi leggibili: {a.record}", file=sys.stderr)
        return 2
    return STAGES[a.stage](rec, load_contract(Path(a.repo)))


def _selfcheck() -> int:
    import tempfile
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + msg)
        ok = ok and cond

    def run(record, repo):
        return cmd_check(argparse.Namespace(stage="ingresso", record=str(record), repo=str(repo)))

    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        (repo / ".fix").mkdir()
        (repo / ".fix" / "contract.yml").write_text("dominii: [auth, billing]\n", encoding="utf-8")
        full = ("---\nid: t\nrepo: r\ndominio: auth\nclasse: logica\n"
                "cecita: bassa\nsorgente: log\nstato: aperto\n---\n")
        p = repo / "r.md"
        p.write_text(full, encoding="utf-8")
        check(run(p, repo) == 0, "record completo -> PASS")
        p.write_text(full.replace("dominio: auth\n", ""), encoding="utf-8")
        check(run(p, repo) == 1, "campo mancante -> FAIL")
        p.write_text(full.replace("dominio: auth", "dominio: ."), encoding="utf-8")
        check(run(p, repo) == 1, "valore-placeholder '.' -> FAIL (non basta esserci)")
        p.write_text(full.replace("classe: logica", "classe: inventata"), encoding="utf-8")
        check(run(p, repo) == 1, "classe fuori enum -> FAIL")
        p.write_text(full.replace("dominio: auth", "dominio: sconosciuto"), encoding="utf-8")
        check(run(p, repo) == 1, "dominio fuori vocabolario -> FAIL")
        # rami dell'ignoranza: mai PASS quando non si sa
        check(run(repo / "nope.md", repo) == 2, "record assente -> errore d'uso, mai PASS")
        (repo / "vuoto.md").write_text("", encoding="utf-8")
        check(run(repo / "vuoto.md", repo) == 2, "record vuoto -> errore d'uso, mai PASS")
        senza = Path(d) / "senza"
        senza.mkdir()
        p.write_text(full, encoding="utf-8")
        check(run(p, senza) == 1, "contratto assente -> FAIL, mai PASS silenzioso")

        # --- dominii_da: il vocabolario si legge dove la repo lo mantiene gia'
        (repo / "cat.json").write_text(
            '{"components":[{"name":"auth"},{"name":"pipeline-preventivo"}]}', encoding="utf-8")
        (repo / ".fix" / "contract.yml").write_text(
            "dominii_da: cat.json\n", encoding="utf-8")
        p.write_text(full.replace("dominio: auth", "dominio: pipeline-preventivo"),
                     encoding="utf-8")
        check(run(p, repo) == 0, "dominii_da: nome presente nel catalogo -> PASS")
        p.write_text(full.replace("dominio: auth", "dominio: billing"), encoding="utf-8")
        check(run(p, repo) == 1, "dominii_da: nome assente dal catalogo -> FAIL")
        (repo / ".fix" / "contract.yml").write_text(
            "dominii_da: manca.json\n", encoding="utf-8")
        p.write_text(full, encoding="utf-8")
        check(run(p, repo) == 1, "dominii_da: catalogo inesistente -> FAIL, mai PASS")
        (repo / "rotto.json").write_text("{non json", encoding="utf-8")
        (repo / ".fix" / "contract.yml").write_text(
            "dominii_da: rotto.json\n", encoding="utf-8")
        check(run(p, repo) == 1, "dominii_da: catalogo illeggibile -> FAIL, mai PASS")
        (repo / ".fix" / "contract.yml").write_text(
            "dominii: [auth, billing]\n", encoding="utf-8")

        def st(stage, extra="", base=full):
            body = base.replace("---\n", "", 1).rsplit("---", 1)[0]
            p.write_text(f"---\n{body}{extra}---\n", encoding="utf-8")
            return cmd_check(argparse.Namespace(stage=stage, record=str(p), repo=str(repo)))

        # --- riproduzione: un COMANDO che esce != 0, non una frase
        check(st("riproduzione") == 0, "riproduzione: cecita bassa -> tappa spenta, PASS")
        alta = full.replace("cecita: bassa", "cecita: alta")
        check(st("riproduzione", base=alta) == 1, "riproduzione: cecita alta senza comando -> FAIL")
        check(st("riproduzione", "riproduzione: ho visto che si rompe\n", alta) == 1,
              "riproduzione: una frase non e' un comando -> FAIL")
        check(st("riproduzione", "riproduzione: /bin/nonesiste-mai --x\n", alta) == 1,
              "riproduzione: comando inesistente -> FAIL, mai PASS")
        check(st("riproduzione", "riproduzione: /usr/bin/false --x\n", alta) == 0,
              "riproduzione: comando che esce !=0 -> PASS (riproduce)")
        check(st("riproduzione", "riproduzione: /usr/bin/true --x\n", alta) == 1,
              "riproduzione: comando che esce 0 -> FAIL (non riproduce)")

        # --- causa: ricorrenza consultata PRIMA (B8), poi path:riga sul file vero
        check(st("causa") == 1, "causa: 'ricorrenza' assente -> FAIL (B8: archivio mai consultato)")
        check(st("causa", "ricorrenza: .\n") == 1,
              "causa: ricorrenza placeholder -> FAIL")
        check(st("causa", "ricorrenza: 0 match in archivio\n") == 1,
              "causa: 'causa_in' assente -> FAIL")
        check(st("causa", "ricorrenza: 0 match\ncausa_in: credo sia il refresh\n") == 1,
              "causa: non e' path:riga -> FAIL")
        check(st("causa", f"ricorrenza: 0 match\ncausa_in: {repo / 'nofile.py'}:3\n") == 1,
              "causa: file inesistente -> FAIL")
        (repo / "src.py").write_text("a\nb\nc\n", encoding="utf-8")
        check(st("causa", f"ricorrenza: 0 match\ncausa_in: {repo / 'src.py'}:99\n") == 1,
              "causa: riga oltre la fine del file -> FAIL")
        check(st("causa", f"ricorrenza: recidiva di acme-web#1279, fix precedente regredito\n"
                          f"causa_in: {repo / 'src.py'}:2\n") == 0,
              "causa: ricorrenza dichiarata + path:riga reale -> PASS")

        # --- raggio: due assi, zero chiamanti DICHIARATO, e chiamanti PROVATI (B7)
        check(st("raggio") == 1, "raggio: chiamanti e issue assenti -> FAIL")
        check(st("raggio", "chiamanti: [a, b]\nchiamanti_cmd: trace_path f\n") == 1,
              "raggio: chiamanti senza asse issue -> FAIL")
        check(st("raggio", "chiamanti: [a]\nissue_prese: []\nissue_lasciate: []\n") == 1,
              "raggio: chiamanti senza il comando che li ha prodotti -> FAIL (B7, #107)")
        check(st("raggio", "chiamanti: [a]\nchiamanti_cmd: find_referencing_symbols f\n"
                           "issue_prese: []\nissue_lasciate: []\n") == 0,
              "raggio: chiamanti + comando + assi -> PASS")
        check(st("raggio", "chiamanti: [nessuno]\nissue_prese: []\nissue_lasciate: []\n") == 0,
              "raggio: zero chiamanti dichiarato -> PASS senza comando")
        check(st("raggio", "chiamanti: [a]\nchiamanti_cmd: grep -rn compute backend/\n"
                           "issue_prese: []\nissue_lasciate: []\n") == 1,
              "raggio: grep come prova -> FAIL (B9: il raggio si vede col graph, mai a grep)")

        # --- deposito: senza rilevatore la finestra e' vietata
        check(st("deposito") == 0, "deposito: classe deterministica -> tappa spenta, PASS")
        llm = full.replace("classe: logica", "classe: llm")
        check(st("deposito", base=llm) == 1, "deposito: classe llm senza finestra -> FAIL")
        check(st("deposito", "osserva_fino_a: 2026-09-01\n", llm) == 1,
              "deposito: finestra senza rilevatore -> FAIL")
        check(st("deposito", "osserva_fino_a: 2026-09-01\nsegnale: scripts/watch.sh --since 7d\n", llm) == 0,
              "deposito: finestra + rilevatore -> PASS")
        check(st("deposito", "osserva_fino_a: 2026-09-01\nblocca_su: manca la chiave prod\n", llm) == 0,
              "deposito: blocker dichiarato al posto del rilevatore -> PASS")

        # --- verde: serve un test nominato E un comando nel contratto
        check(st("verde") == 1, "verde: 'test' assente -> FAIL")
        check(st("verde", "test: tests/test_x.py::test_y\n") == 1,
              "verde: contratto senza test.suite -> FAIL, mai PASS")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\ntest.suite: /usr/bin/false\n', encoding="utf-8")
        check(st("verde", "test: tests/test_x.py::test_y\n") == 1,
              "verde: la suite fallisce -> FAIL (danno collaterale)")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\ntest.suite: /usr/bin/true\n', encoding="utf-8")
        check(st("verde", "test: tests/test_x.py::test_y\n") == 0,
              "verde: suite verde -> PASS")
        # fail-open del cd (eval sul campo 2026-08-17): comando composto che DEVE fallire
        (repo / ".fix" / "contract.yml").write_text(
            f'dominii: [auth, billing]\ntest.suite: cd {repo} && /usr/bin/false\n',
            encoding="utf-8")
        check(st("verde", "test: tests/test_x.py::test_y\n") == 1,
              "verde: 'cd x && false' -> FAIL vero (prima: /usr/bin/cd usciva 0, fail-open)")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\ntest.suite: /usr/bin/true\n', encoding="utf-8")

        # --- circuit breaker (B6): >=4 rossi dello stesso test = thrashing
        thrash = repo / "thrash.jsonl"
        thrash.write_text("".join(
            json.dumps({"ts": f"2026-01-0{i}T00:00:00+00:00", "test": "t.py::a",
                        "rosso": i < 5, "file_sha": "aaa"}) + "\n" for i in range(1, 6)),
            encoding="utf-8")
        check(st("verde", f"test: t.py::a\nrosso_log: {thrash}\n") == 1,
              "verde: 4 rossi stesso test -> CIRCUIT BREAKER, FAIL (B6)")
        check(st("verde", f"test: t.py::a\nrosso_log: {thrash}\n"
                          "architettura_riesaminata: il retry maschera un lock, refactor issue #x\n") == 0,
              "verde: breaker + architettura riesaminata dichiarata -> PASS")
        due = repo / "due.jsonl"
        due.write_text("".join(
            json.dumps({"ts": f"2026-01-0{i}T00:00:00+00:00", "test": "t.py::a",
                        "rosso": i == 1, "file_sha": "aaa"}) + "\n" for i in (1, 2)),
            encoding="utf-8")
        check(st("verde", f"test: t.py::a\nrosso_log: {due}\n") == 0,
              "verde: 1 rosso poi verde -> nessun breaker, PASS")

        # --- rosso: si registra, non si dichiara. Lo verifica tdd-dev
        check(st("rosso") == 1, "rosso: 'test' e 'rosso_log' assenti -> FAIL")
        check(st("rosso", "test: t.py::a\nrosso_log: /tmp/r.jsonl\n") == 1,
              "rosso: contratto senza tdd_dev -> FAIL, mai PASS")
        tdd = repo / "tdd"
        (tdd / "scripts").mkdir(parents=True)
        (repo / ".fix" / "contract.yml").write_text(
            f'dominii: [auth, billing]\ntdd_red: {tdd}\n', encoding="utf-8")
        check(st("rosso", "test: t.py::a\nrosso_log: /tmp/r.jsonl\n") == 1,
              "rosso: contratto tdd_red legacy resta compatibile -> path mancante FAIL")
        (tdd / "scripts" / "red_check.py").write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
        check(st("rosso", "test: t.py::a\nrosso_log: /tmp/r.jsonl\n") == 1,
              "rosso: tdd-dev rifiuta -> FAIL propagato")
        (tdd / "scripts" / "red_check.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        check(st("rosso", "test: t.py::a\nrosso_log: /tmp/r.jsonl\n") == 0,
              "rosso: contratto tdd_red legacy resta compatibile -> PASS")
        (repo / ".fix" / "contract.yml").write_text(
            f'dominii: [auth, billing]\ntdd_dev: {tdd}\n', encoding="utf-8")
        check(st("rosso", "test: t.py::a\nrosso_log: /tmp/r.jsonl\n") == 0,
              "rosso: tdd-dev e' la porta canonica -> PASS")

        # --- raccolto: un test che la CI non raccoglie e' orfano (R5)
        check(st("raccolto") == 1, "raccolto: 'test' assente -> FAIL")
        check(st("raccolto", "test: tests/test_x.py::test_y\n") == 1,
              "raccolto: contratto senza ci.collect -> FAIL, mai PASS")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\nci.collect: /bin/nonesiste-mai\n', encoding="utf-8")
        check(st("raccolto", "test: tests/test_x.py::test_y\n") == 1,
              "raccolto: comando di raccolta inesistente -> FAIL")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\nci.collect: /usr/bin/false\n', encoding="utf-8")
        check(st("raccolto", "test: tests/test_x.py::test_y\n") == 1,
              "raccolto: la raccolta fallisce -> FAIL")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\nci.collect: /usr/bin/true\n', encoding="utf-8")
        check(st("raccolto", "test: tests/test_x.py::test_y\n") == 1,
              "raccolto: test assente dall'output della raccolta -> FAIL (orfano)")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\n'
            'ci.collect: /bin/echo tests/test_x.py::test_y\n', encoding="utf-8")
        check(st("raccolto", "test: tests/test_x.py::test_y\n") == 0,
              "raccolto: test raccolto dalla CI -> PASS")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\n', encoding="utf-8")

        # --- mutazione: il log deve essere reale, attribuito, e rosso
        check(st("mutazione") == 1, "mutazione: 'mutation_log' assente -> FAIL")
        check(st("mutazione", f"mutation_log: {repo / 'nope.json'}\n") == 1,
              "mutazione: log inesistente -> FAIL")
        ml = repo / "m.json"
        ml.write_text("non-json", encoding="utf-8")
        check(st("mutazione", f"mutation_log: {ml}\n") == 1, "mutazione: log illeggibile -> FAIL")
        ml.write_text(json.dumps({"fix_sha": "aaa", "tornato_rosso": True}), encoding="utf-8")
        check(st("mutazione", f"mutation_log: {ml}\n") == 1,
              "mutazione: 'fix_sha' assente nel record -> FAIL")
        check(st("mutazione", f"mutation_log: {ml}\nfix_sha: bbb\n") == 1,
              "mutazione: il log e' di un ALTRO fix -> FAIL")
        ml.write_text(json.dumps({"fix_sha": "aaa", "tornato_rosso": False}), encoding="utf-8")
        check(st("mutazione", f"mutation_log: {ml}\nfix_sha: aaa\n") == 1,
              "mutazione: i test restano verdi col bug rimesso -> FAIL")
        ml.write_text(json.dumps({"fix_sha": "aaa", "tornato_rosso": True}), encoding="utf-8")
        check(st("mutazione", f"mutation_log: {ml}\nfix_sha: aaa\n") == 0,
              "mutazione: la suite torna rossa col bug rimesso -> PASS")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\n', encoding="utf-8")

        # --- realtest: si propaga il verdetto di real-test, non se ne scrive uno nuovo
        check(st("realtest") == 1, "realtest: contratto senza real_test -> FAIL")
        (repo / ".fix" / "contract.yml").write_text(
            f'dominii: [auth, billing]\nreal_test: {repo / "nonesiste"}\n', encoding="utf-8")
        check(st("realtest", "verdict_path: /tmp/x.json\n") == 1,
              "realtest: real-test non trovato al path dichiarato -> FAIL")
        rt = repo / "rt"
        (rt / "scripts").mkdir(parents=True)
        (rt / "scripts" / "verdict.py").write_text(
            "import sys\nsys.exit(1)\n", encoding="utf-8")
        (repo / ".fix" / "contract.yml").write_text(
            f'dominii: [auth, billing]\nreal_test: {rt}\n', encoding="utf-8")
        check(st("realtest") == 1, "realtest: verdict_path assente -> FAIL")
        check(st("realtest", f"verdict_path: {repo / 'nope.json'}\n") == 1,
              "realtest: verdict_path inesistente -> FAIL")
        vj = repo / "v.json"
        vj.write_text("{}", encoding="utf-8")
        check(st("realtest", f"verdict_path: {vj}\n") == 1,
              "realtest: real-test rifiuta -> FAIL propagato, mai PASS")
        (rt / "scripts" / "verdict.py").write_text(
            "import sys\nsys.exit(0)\n", encoding="utf-8")
        check(st("realtest", f"verdict_path: {vj}\n") == 0,
              "realtest: real-test accetta -> PASS")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\n', encoding="utf-8")

        # --- firma: evidenza + campo leggibile da uno script
        check(st("firma") == 1, "firma: senza verdict_path ne firma -> FAIL")
        v = repo / "verdict.json"
        v.write_text("{}", encoding="utf-8")
        check(st("firma", f"verdict_path: {v}\n") == 1,
              "firma: evidenza presente ma non firmata -> FAIL")
        check(st("firma", f"verdict_path: {repo / 'assente.json'}\nfirma: founder\nfirmato_il: 2026-08-11\n") == 1,
              "firma: firmata ma l'evidenza non esiste -> FAIL")
        check(st("firma", f"verdict_path: {v}\nfirma: founder\nfirmato_il: 2026-08-11\n") == 0,
              "firma: evidenza + firma -> PASS")

        # --- prod: l'osservazione ha un exit code
        check(st("prod") == 1, "prod: 'prod_il' assente -> FAIL")
        check(st("prod", "prod_il: 2026-08-11\n") == 1,
              "prod: contratto senza prod.osserva -> FAIL (deployato != osservato)")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\nprod.osserva: /usr/bin/false\n', encoding="utf-8")
        check(st("prod", "prod_il: 2026-08-11\n") == 1,
              "prod: l'osservazione fallisce -> FAIL")
        (repo / ".fix" / "contract.yml").write_text(
            'dominii: [auth, billing]\nprod.osserva: /usr/bin/true\n', encoding="utf-8")
        check(st("prod", "prod_il: 2026-08-11\n") == 0,
              "prod: osservazione eseguita e verde -> PASS")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="fix_gate.py")
    ap.add_argument("--selfcheck", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check")
    c.add_argument("--stage", required=True)
    c.add_argument("--record", required=True)
    c.add_argument("--repo", required=True)
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    if a.cmd == "check":
        return cmd_check(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
