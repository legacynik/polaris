#!/usr/bin/env python3
"""T2b (2/2) — ratchet del rank-1: la soglia sale, non scende mai.

La misura (rank-1 rate) viene da fuori: un run reale dell'agente sul test set di
split_traintest.py, contando quante query positive rankano la skill #1 — il loop e'
documentato in references/eval-protocol.md, non reimplementato qui (eseguire un harness
LLM reale e' compito dell'agente orchestratore, non di uno script stdlib). Qui sta solo
il floor persistito: se la nuova misura e' sotto il floor, FAIL — e il floor non si
riscrive mai piu' basso, nemmeno quando la skill peggiora davvero (si fallisce, non si
abbassa l'asticella per farla passare).

    trigger_ratchet.py --slug SLUG --rate 0.83 --state FILE --model MODEL \
        --input-tokens N --output-tokens N --wall-ms N --valid-runs N \
        --excluded-runs N [--skill DIR] [--floor-init 0.80]
    trigger_ratchet.py --selfcheck

`--skill` pins the receipt to the description it was measured on (sha256 of the
description, stored beside the rate). change_gate.py refuses to reuse a rate whose pin no
longer matches the file, which is what stops a green from travelling across a trigger
edit. Without `--skill` the rate is recorded unpinned and change_gate reports CONCERNS.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import desc_sha  # noqa: E402 — one implementation of the pin, not two

FLOOR_INIT_DEFAULT = 0.80
# The floor rises with the measured rate but never past this cap. A floor at 100% turns one
# flaky sample into a permanent red, and the door then gets edited with the gate switched
# off — the failure mode the founder named for CI gates. It is also a precision claim the
# corpus cannot back: with 4 positives in the test split the smallest observable change is
# 25%, so a 100% floor pretends to a resolution the measurement does not have.
FLOOR_CAP = 0.95


def load_state(state_file: Path) -> dict:
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {}


def source_ok(measured_on: str | None) -> bool:
    """Tripwire contro la selezione sul TRAIN split (violazione silenziosa, non
    altrimenti rilevabile da uno script): se il chiamante DICHIARA la fonte, il nome
    file deve dire 'test', mai 'train'. Nessuna dichiarazione -> non verificabile qui,
    passa (il workflow a monte, references/eval-protocol.md, resta responsabile)."""
    if not measured_on:
        return True
    name = Path(measured_on).name.lower()
    return "train" not in name


def rebaseline(previous: dict, model: str | None) -> str | None:
    """Il modello che ha misurato il floor, se e' incomparabile con quello di adesso.

    Il protocollo lo dice gia' a parole — «numbers taken with different models on
    different days must not be compared in silence» — ma `apply` li confrontava lo
    stesso: all'arrivo del proxy economico (#323) due porte sarebbero rimaste rosse per
    sempre a un rate che la loro description INVARIATA produceva gia'. Un floor misurato
    con un altro metodo non e' un'asticella piu' alta, e' un'asticella diversa: si
    ri-baselina, in chiaro. Stesso modello e rate sotto il floor resta una regressione."""
    if not previous or "floor" not in previous:
        return None
    was = previous.get("model")
    return None if was == model else (was or "unrecorded")


def apply(state: dict, slug: str, rate: float, floor_init: float,
          receipt: dict | None = None) -> tuple[bool, str, dict]:
    previous = state.get(slug, {})
    floor = previous.get("floor", floor_init)
    if not 0.0 <= rate <= 1.0:
        return False, f"rank-1 {rate!r} fuori intervallo: deve essere tra 0 e 1", state
    superseded = rebaseline(previous, (receipt or {}).get("model"))
    if superseded is not None:
        entry = {"floor": min(rate, FLOOR_CAP), "last_rate": rate, **(receipt or {}),
                 "superseded_floor": floor, "superseded_model": superseded}
        return True, (f"RE-BASELINE: il floor {floor:.0%} era misurato da {superseded!r}, "
                      f"questo rate {rate:.0%} da {(receipt or {}).get('model')!r} — metodi "
                      "diversi non si confrontano, il floor riparte da questa misura"), \
            {**state, slug: entry}
    if rate < floor:
        return False, (f"rank-1 {rate:.0%} sotto il floor {floor:.0%} — la skill discrimina "
                        "peggio di prima: riscrivi la description, non abbassare il floor per "
                        "farla passare (e' il ratchet: sale, non scende mai)."), state
    new_floor = min(max(floor, rate), FLOOR_CAP)
    state = {**state, slug: {"floor": new_floor, "last_rate": rate, **(receipt or {})}}
    msg = (f"rank-1 {rate:.0%} >= floor {floor:.0%} -> OK"
           + (f", floor alzato a {new_floor:.0%}" if new_floor > floor else "")
           + (f" (cap {FLOOR_CAP:.0%}: il floor non sale oltre la risoluzione del test set)"
              if rate > FLOOR_CAP else ""))
    return True, msg, state



def selfcheck() -> int:
    state: dict = {}
    ok, msg, state = apply(state, "triage", 0.86, FLOOR_INIT_DEFAULT)
    assert ok and state["triage"]["floor"] == 0.86, msg
    ok, msg, state = apply(state, "triage", 0.90, FLOOR_INIT_DEFAULT)
    assert ok and state["triage"]["floor"] == 0.90, msg
    ok, msg, _ = apply(state, "triage", 0.75, FLOOR_INIT_DEFAULT)
    assert not ok, "sotto il floor deve fallire"
    assert state["triage"]["floor"] == 0.90, "il floor non deve MAI abbassarsi dopo un fail"
    assert source_ok(None) and source_ok("data/test.json"), "nessuna fonte o 'test' nel nome: ok"
    assert not source_ok("data/train.json"), "misurato sul TRAIN: la tripwire deve rifiutare"
    ok, msg, capped = apply({}, "perfect", 1.0, FLOOR_INIT_DEFAULT)
    assert ok and capped["perfect"]["floor"] == FLOOR_CAP, (
        f"un run perfetto non deve murare la porta a 100%: {msg}")
    assert capped["perfect"]["last_rate"] == 1.0, "il rate misurato si registra intero"
    receipt = {"model": "demo", "input_tokens": 10, "output_tokens": 2,
               "wall_ms": 30, "valid_runs": 3, "excluded_runs": 0}
    ok, _, measured = apply({}, "measured", 0.9, FLOOR_INIT_DEFAULT, receipt)
    assert ok and all(measured["measured"][k] == v for k, v in receipt.items())
    legacy = {"old": {"floor": 0.95, "last_rate": 1.0, "model": "ranker"}}
    ok, msg, rebased = apply(legacy, "old", 0.87, FLOOR_INIT_DEFAULT, {**receipt, "model": "llm"})
    assert ok and "RE-BASELINE" in msg and rebased["old"]["superseded_floor"] == 0.95, msg
    ok, _, _ = apply(rebased, "old", 0.5, FLOOR_INIT_DEFAULT, {**receipt, "model": "llm"})
    assert not ok, "stesso modello del re-baseline: un calo torna a essere una regressione"
    print("SELFCHECK OK — 8 rami: alza il floor, alza ancora, fallisce sotto senza abbassarlo, "
          "tripwire train/test, cap del floor, receipt costo persistita, re-baseline su "
          "modello diverso, regressione di nuovo rossa dopo il re-baseline")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slug")
    p.add_argument("--rate", type=float)
    p.add_argument("--state", type=Path)
    p.add_argument("--skill", type=Path, help="pin the receipt to this skill's description")
    p.add_argument("--floor-init", type=float, default=FLOOR_INIT_DEFAULT)
    p.add_argument("--measured-on", help="path del file da cui viene il rate (tripwire train/test)")
    p.add_argument("--model")
    p.add_argument("--input-tokens", type=int)
    p.add_argument("--output-tokens", type=int)
    p.add_argument("--wall-ms", type=int)
    p.add_argument("--valid-runs", type=int)
    p.add_argument("--excluded-runs", type=int)
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()
    required = (a.slug, a.rate, a.state, a.model, a.input_tokens, a.output_tokens,
                a.wall_ms, a.valid_runs, a.excluded_runs)
    if any(value is None for value in required):
        p.error("servono --slug --rate --state --model --input-tokens --output-tokens "
                "--wall-ms --valid-runs --excluded-runs (o --selfcheck)")
    if (not a.model.strip() or a.input_tokens < 0 or a.output_tokens < 0 or a.wall_ms <= 0
            or a.valid_runs <= 0 or a.excluded_runs < 0):
        p.error("model deve essere non vuoto; token/run esclusi >=0; wall-ms e valid-runs >0")
    if not source_ok(a.measured_on):
        print(f"rifiutato: --measured-on {a.measured_on!r} sembra il TRAIN split — il rank-1 "
              "va misurato sul TEST (mai selezionare sulle query di addestramento).")
        return 1
    state = load_state(a.state)
    receipt = {
        "model": a.model,
        "input_tokens": a.input_tokens,
        "output_tokens": a.output_tokens,
        "wall_ms": a.wall_ms,
        "valid_runs": a.valid_runs,
        "excluded_runs": a.excluded_runs,
    }
    ok, msg, state = apply(state, a.slug, a.rate, a.floor_init, receipt)
    if ok:
        if a.skill:
            md = a.skill / "SKILL.md"
            if not md.exists():
                print(f"rifiutato: --skill {a.skill} senza SKILL.md — il pin non e' "
                      "calcolabile, e un rate non pinnato non deve sembrare pinnato.")
                return 2
            state[a.slug]["desc_sha256"] = desc_sha(md.read_text())
            msg += f", pin {state[a.slug]['desc_sha256']}"
        msg += (f", model {a.model}, token {a.input_tokens}+{a.output_tokens}, "
                f"latenza {a.wall_ms}ms, run {a.valid_runs} validi/{a.excluded_runs} esclusi")
        a.state.parent.mkdir(parents=True, exist_ok=True)
        a.state.write_text(json.dumps(state, indent=2))
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
