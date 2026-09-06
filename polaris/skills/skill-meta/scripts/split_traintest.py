#!/usr/bin/env python3
"""T2b (1/2) — split train/test stratificato per la description-eval.

Mai scegliere la description finale sulle query di addestramento: e' overfitting sulle
stesse query che l'hanno "insegnata", rischio diretto quando il criterio di successo (una
skill per query) si misura su query gia' viste. Stratifica per `should_trigger` cosi' sia
train sia test hanno esempi positivi e negativi; seed fisso per riproducibilita' (mai
scegliere la versione finale su uno split diverso ogni volta).

    split_traintest.py IN.json [--holdout 0.4] [--seed 42] --out-dir DIR
    split_traintest.py --selfcheck
"""
from __future__ import annotations
import argparse
import json
import random
import sys
from pathlib import Path


def stratum(case: dict, arms: frozenset[str]) -> str:
    """Positive/negative, and the arm too when the corpus declares one.

    Stratifying on `should_trigger` alone is enough for a door with one job and not enough for
    a router: architettura's seed-42 split put every `framework` case on the same side, so the
    arm that had just failed could have been "fixed" with no test evidence that it had. The arm
    is the first component of the hand-written tuple, and only counts when it matches an arm the
    corpus declared in `dimensions.arm` — a corpus that declares none splits exactly as before.
    """
    arm = case.get("tuple", "").split("·")[0].strip()
    return f"{bool(case.get('should_trigger'))}|{arm if arm in arms else ''}"


def split(eval_set: list[dict], holdout: float, seed: int,
          arms: frozenset[str] = frozenset()) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    groups: dict[str, list[dict]] = {}
    for e in eval_set:
        groups.setdefault(stratum(e, arms), []).append(e)
    train: list[dict] = []
    test: list[dict] = []
    # reverse: positives before negatives, so a corpus with no arms lands on the exact
    # partition the old two-group code produced and its recorded split stays valid
    for key in sorted(groups, reverse=True):
        g = groups[key]
        rng.shuffle(g)
        n = max(1, round(len(g) * holdout))
        test += g[:n]
        train += g[n:]
    return train, test


def selfcheck() -> int:
    data = [{"q": i, "should_trigger": i < 12} for i in range(20)]  # 12 pos, 8 neg
    train1, test1 = split(data, 0.4, seed=42)
    train2, test2 = split(data, 0.4, seed=42)
    assert train1 == train2 and test1 == test2, "stesso seed deve dare lo stesso split"
    assert {t["q"] for t in train1} & {t["q"] for t in test1} == set(), "train/test disgiunti"
    n_pos_test = sum(1 for t in test1 if t["should_trigger"])
    n_neg_test = sum(1 for t in test1 if not t["should_trigger"])
    assert n_pos_test == 5 and n_neg_test == 3, f"stratificato 40%: {n_pos_test} pos, {n_neg_test} neg"
    _, test3 = split(data, 0.4, seed=7)
    assert [t["q"] for t in test1] != [t["q"] for t in test3], "seed diverso -> split diverso"
    # arm stratification: due casi per braccio, tre bracci -> ogni braccio in ENTRAMBI gli split
    arms = frozenset({"a", "b", "c"})
    multi = [{"q": f"{a}{i}", "should_trigger": True, "tuple": f"{a} · x · y"}
             for a in arms for i in range(2)]
    tr, te = split(multi, 0.4, seed=42, arms=arms)
    seen = lambda s: {c["tuple"].split("·")[0].strip() for c in s}  # noqa: E731
    assert seen(tr) == arms and seen(te) == arms, (seen(tr), seen(te))
    # e senza bracci dichiarati lo stesso corpus si divide come prima: nessun braccio garantito
    _, te_flat = split(multi, 0.4, seed=42)
    assert seen(te_flat) != arms, "senza dichiarazione non c'e' garanzia per braccio — e' il punto"
    print("SELFCHECK OK — determinismo, disgiunzione, stratificazione, seed diverso->split "
          "diverso, ogni braccio dichiarato presente in train E test")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input", nargs="?", type=Path)
    p.add_argument("--holdout", type=float, default=0.4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-dir", type=Path)
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not a.input or not a.out_dir:
        p.error("servono IN.json e --out-dir (o --selfcheck)")
    raw = json.loads(a.input.read_text())
    # The stored corpus is `{"skill": ..., "cases": [...]}`; a bare list still works so an
    # ad-hoc set does not need wrapping. Anything else is a usage error, never an empty run.
    eval_set = raw.get("cases") if isinstance(raw, dict) else raw
    if not isinstance(eval_set, list) or not eval_set:
        print(f"{a.input}: no cases found — expected a list, or an object with 'cases'")
        return 2
    arms = frozenset((raw.get("dimensions", {}) if isinstance(raw, dict) else {}).get("arm", []))
    train, test = split(eval_set, a.holdout, a.seed, arms)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "train.json").write_text(json.dumps(train, indent=2))
    (a.out_dir / "test.json").write_text(json.dumps(test, indent=2))
    print(f"train={len(train)} test={len(test)} seed={a.seed} holdout={a.holdout} -> {a.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
