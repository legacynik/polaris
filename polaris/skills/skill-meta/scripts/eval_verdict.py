#!/usr/bin/env python3
"""T3 — verdetto cieco baseline-vs-donor-vs-nuovo, in blocco grep-verificabile.

I run (baseline = senza skill o versione precedente; donor = miglior workflow applicabile;
nuovo = con la skill) li lancia l'agente orchestratore nello STESSO turno — questo script non
dispatcha nulla, aggrega grading gia' scritto su disco.
Stesso primitivo di `review`: blocco `## REVIEW REPORT`, riga `VERDICT`, sentinella
finale — un formato indipendente in piu' sarebbe l'overlap tra job-gate che il Critic-2
sul disegno ha segnalato (nessun primitivo condiviso dichiarato).

Formato dei tre input (grading.json), uno per lato — un subagent "grader" dedicato li
scrive, non l'agente sotto test (vedi references/eval-protocol.md):
    {"checks": [{"id": "stable-case-id", "assertion": "...", "passed": true,
                 "evidence": "..."}],
     "metrics": {"model": "...", "input_tokens": 1, "output_tokens": 1,
                 "wall_ms": 1, "tool_calls": 1, "repeated_commands": 0,
                 "consistent_runs": 3, "runs": 3,
                 "context_reuse": "reused|not_available|missed"},
     "limits": { ... }}

    eval_verdict.py --baseline B.json --donor D.json --donor-label NAME --new N.json \
      --critic C.json --checks CHECKS.json --diff DIFF.patch \
      --critic-transcript TRANSCRIPT.txt --skill SLUG [--append FILE]
    eval_verdict.py --selfcheck
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

SENTINEL = "NO UNRESOLVED DECISIONS"
METRIC_FIELDS = ("model", "input_tokens", "output_tokens", "wall_ms", "tool_calls",
                 "repeated_commands", "consistent_runs", "runs", "context_reuse")
LIMIT_FIELDS = ("max_total_tokens", "max_wall_ms", "max_tool_calls",
                "max_repeated_commands", "min_consistency")
CONTEXT_VALUES = {"reused", "not_available", "missed"}
ATTACK_KEYS = {"sibling_branches", "claim_code_mismatch", "bypasses",
               "false_green_selfchecks"}


def pass_rate(grading: list[dict]) -> tuple[int, int]:
    passed = sum(1 for g in grading if g.get("passed"))
    return passed, len(grading)


def verdict(base_rate: tuple[int, int], new_rate: tuple[int, int]) -> str:
    b = base_rate[0] / base_rate[1] if base_rate[1] else 0.0
    n = new_rate[0] / new_rate[1] if new_rate[1] else 0.0
    if n > b:
        return "PASS"
    if n == b:
        return "CONCERNS"
    return "FAIL"


def _validate_token_fields(metrics: dict) -> None:
    """output_tokens may be UNKNOWN (unsupported telemetry is never reported as 0,
    critic round-2 F5) — every other numeric field stays a required non-negative int."""
    numeric = ("input_tokens", "wall_ms", "tool_calls", "repeated_commands", "consistent_runs", "runs")
    if any(not isinstance(metrics[field], int) or isinstance(metrics[field], bool) for field in numeric):
        raise ValueError("token, latency, tool and run metrics must be integers")
    if metrics["input_tokens"] < 0:
        raise ValueError("metrics out of range")
    ot = metrics["output_tokens"]
    if ot != "UNKNOWN" and (type(ot) is not int or isinstance(ot, bool) or ot < 0):
        raise ValueError("metrics.output_tokens must be a non-negative integer or UNKNOWN")


def arm_tokens(metrics: dict) -> str:
    """int total as str if both known, else UNKNOWN — same convention as critic_tokens()."""
    values = metrics["input_tokens"], metrics["output_tokens"]
    return str(sum(values)) if all(type(value) is int for value in values) else "UNKNOWN"


def token_delta(a: dict, b: dict) -> str:
    at, bt = arm_tokens(a), arm_tokens(b)
    return "UNKNOWN" if "UNKNOWN" in (at, bt) else f"{int(at) - int(bt):+d}"


def validate_arm(value: object, *, require_limits: bool) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get("checks"), list) \
            or not isinstance(value.get("metrics"), dict):
        raise ValueError("grading must be an object with checks[] and metrics{}")
    checks = value["checks"]
    if not checks:
        raise ValueError("checks must not be empty")
    if any(not isinstance(check, dict)
           or not isinstance(check.get("id"), str) or not check["id"].strip()
           or not isinstance(check.get("assertion"), str) or not check["assertion"].strip()
           or type(check.get("passed")) is not bool for check in checks):
        raise ValueError("each check needs id, non-empty assertion and boolean passed")
    ids = [check["id"] for check in checks]
    if len(ids) != len(set(ids)):
        raise ValueError("check ids must be unique inside each arm")
    metrics = value["metrics"]
    missing = [field for field in METRIC_FIELDS if field not in metrics]
    if missing:
        raise ValueError(f"metrics missing: {', '.join(missing)}")
    if not isinstance(metrics["model"], str) or not metrics["model"].strip():
        raise ValueError("metrics.model must be a non-empty string")
    _validate_token_fields(metrics)
    if (metrics["wall_ms"] <= 0 or metrics["tool_calls"] < 0
            or metrics["repeated_commands"] < 0 or metrics["runs"] <= 0
            or not 0 <= metrics["consistent_runs"] <= metrics["runs"]):
        raise ValueError("metrics out of range")
    if metrics["context_reuse"] not in CONTEXT_VALUES:
        raise ValueError(f"metrics.context_reuse must be one of {sorted(CONTEXT_VALUES)}")
    limits = value.get("limits")
    if require_limits and not isinstance(limits, dict):
        raise ValueError("new grading must carry predeclared limits")
    if limits is not None:
        if not isinstance(limits, dict):
            raise ValueError("limits must be an object")
        missing_limits = [field for field in LIMIT_FIELDS if field not in limits]
        if missing_limits:
            raise ValueError(f"limits missing: {', '.join(missing_limits)}")
        maximums = ("max_total_tokens", "max_wall_ms", "max_tool_calls",
                    "max_repeated_commands")
        if any(type(limits[field]) is not int or limits[field] < 0 for field in maximums):
            raise ValueError("token, latency, tool and repeat limits must be non-negative integers")
        minimum = limits["min_consistency"]
        if isinstance(minimum, bool) or not isinstance(minimum, (int, float)) \
                or not 0 <= minimum <= 1:
            raise ValueError("min_consistency must be a number from 0 to 1")
    return value


def load_check_ids(value: object) -> set[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("checks corpus must be a non-empty list")
    ids = [item.get("id") for item in value if isinstance(item, dict)]
    if len(ids) != len(value) or any(not isinstance(item, str) or not item.strip() for item in ids):
        raise ValueError("each checks corpus entry needs a non-empty id")
    if len(ids) != len(set(ids)):
        raise ValueError("checks corpus ids must be unique")
    return set(ids)


def validate_critic(value: object, required_check_ids: set[str], *, diff_sha256: str,
                    transcript_sha256: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError("critic receipt must be an object")
    if value.get("agent_type") != "critic":
        raise ValueError("critic.agent_type must be critic")
    if value.get("fork_turns") != "none":
        raise ValueError("critic must use fresh context (fork_turns=none)")
    if value.get("review_lanes") != ["critic"]:
        raise ValueError("critic.review_lanes must contain exactly one critic lane")
    if value.get("reviewed_diff_sha256") != diff_sha256:
        raise ValueError("critic.reviewed_diff_sha256 does not match the supplied diff")
    if value.get("transcript_sha256") != transcript_sha256:
        raise ValueError("critic.transcript_sha256 does not match the supplied transcript")
    graded = value.get("graded_checks")
    if not isinstance(graded, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("id"), str)
            or type(item.get("passed")) is not bool
            or not isinstance(item.get("evidence"), str) or not item["evidence"].strip()
            for item in graded):
        raise ValueError("critic.graded_checks need id, boolean passed and non-empty evidence")
    graded_ids = [item["id"] for item in graded]
    if len(graded_ids) != len(set(graded_ids)) or set(graded_ids) != required_check_ids:
        raise ValueError("critic.graded_checks must cover every declared check id exactly")
    if value.get("verdict") not in {"PASS", "BLOCK"}:
        raise ValueError("critic.verdict must be PASS or BLOCK")
    findings = value.get("findings")
    if not isinstance(findings, list) or any(not isinstance(item, str) for item in findings):
        raise ValueError("critic.findings must be a list of strings")
    attacks = value.get("attacks")
    if not isinstance(attacks, dict) or set(attacks) != ATTACK_KEYS:
        raise ValueError(f"critic.attacks must contain exactly {sorted(ATTACK_KEYS)}")
    for name, attack in attacks.items():
        if not isinstance(attack, dict) or not isinstance(attack.get("inventory"), list) \
                or not attack["inventory"] or not isinstance(attack.get("probes"), list):
            raise ValueError(f"critic.attacks.{name} needs inventory[] and probes[]")
        inventory = attack["inventory"]
        if len(inventory) != len(set(inventory)) or any(
                not isinstance(target, str) or len(target.strip()) < 8
                or not any(mark in target for mark in (":", "/", "->"))
                for target in inventory):
            raise ValueError(f"critic.attacks.{name} inventory needs unique concrete targets")
        probes = attack["probes"]
        if any(not isinstance(probe, dict) or not isinstance(probe.get("target"), str)
               or type(probe.get("passed")) is not bool
               or not isinstance(probe.get("evidence"), str)
               or len(probe["evidence"].strip()) < 8 for probe in probes):
            raise ValueError(f"critic.attacks.{name} probes need target, result and evidence")
        probe_targets = [probe["target"] for probe in probes]
        if len(probe_targets) != len(set(probe_targets)) or set(probe_targets) != set(inventory):
            raise ValueError(f"critic.attacks.{name} must probe every inventoried target exactly")
    if value["verdict"] == "PASS" and any(
            not probe["passed"] for attack in attacks.values() for probe in attack["probes"]):
        raise ValueError("critic PASS cannot carry a failed adversarial attack")
    if value["verdict"] == "PASS" and any(not check["passed"] for check in graded):
        raise ValueError("critic PASS cannot carry a failed declared check")
    for field in ("model",):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"critic.{field} must be a non-empty string")
    for field in ("input_tokens", "output_tokens"):
        metric = value.get(field)
        if metric != "UNKNOWN" and (type(metric) is not int or metric < 0):
            raise ValueError(f"critic.{field} must be a non-negative integer or UNKNOWN")
    if type(value.get("wall_ms")) is not int or value["wall_ms"] <= 0:
        raise ValueError("critic.wall_ms must be positive")
    return value


def limit_failures(arm: dict) -> list[str]:
    metrics, limits = arm["metrics"], arm["limits"]
    total_tokens = arm_tokens(metrics)
    consistency = metrics["consistent_runs"] / metrics["runs"]
    checks = (
        (total_tokens == "UNKNOWN" or int(total_tokens) <= limits["max_total_tokens"],
         f"total tokens {total_tokens} > {limits['max_total_tokens']}"),
        (metrics["wall_ms"] <= limits["max_wall_ms"],
         f"wall_ms {metrics['wall_ms']} > {limits['max_wall_ms']}"),
        (metrics["tool_calls"] <= limits["max_tool_calls"],
         f"tool calls {metrics['tool_calls']} > {limits['max_tool_calls']}"),
        (metrics["repeated_commands"] <= limits["max_repeated_commands"],
         f"repeated commands {metrics['repeated_commands']} > {limits['max_repeated_commands']}"),
        (consistency >= limits["min_consistency"]
         or math.isclose(consistency, limits["min_consistency"], abs_tol=1e-9),
         f"consistency {consistency:.0%} < {limits['min_consistency']:.0%}"),
        (metrics["context_reuse"] != "missed", "available context was not reused"),
    )
    return [message for ok, message in checks if not ok]


def donor_failures(baseline: dict, donor: dict, new: dict) -> list[str]:
    """Candidate must add quality without regressing donor-passed checks or consistency."""
    failures: list[str] = []
    baseline_cohort = [(check["id"], check["assertion"]) for check in baseline["checks"]]
    donor_cohort = [(check["id"], check["assertion"]) for check in donor["checks"]]
    new_cohort = [(check["id"], check["assertion"]) for check in new["checks"]]
    if not baseline_cohort == donor_cohort == new_cohort:
        return ["donor parity: checks or contexts differ — comparison is not a cohort"]
    bm, dm, nm = baseline["metrics"], donor["metrics"], new["metrics"]
    for field in ("model", "runs", "context_reuse"):
        if not bm[field] == dm[field] == nm[field]:
            failures.append(f"donor parity: {field} differs across baseline/donor/candidate")
    for donor_check, new_check in zip(donor["checks"], new["checks"]):
        if donor_check["passed"] and not new_check["passed"]:
            failures.append(f"donor parity: regressed check {new_check['assertion']}")
    if nm["consistent_runs"] * dm["runs"] < dm["consistent_runs"] * nm["runs"]:
        failures.append("donor parity: consistency regressed")
    if not any(new_check["passed"] and not donor_check["passed"]
               for donor_check, new_check in zip(donor["checks"], new["checks"])):
        failures.append("donor parity: no strict quality win over donor")
    return failures


def cost_line(label: str, arm: dict) -> str:
    metrics = arm["metrics"]
    tokens = arm_tokens(metrics)
    return (f"{label} cost: tokens={tokens} ({metrics['input_tokens']}+{metrics['output_tokens']}), "
            f"wall_ms={metrics['wall_ms']}, tool_calls={metrics['tool_calls']}, "
            f"repeated={metrics['repeated_commands']}, "
            f"consistency={metrics['consistent_runs']}/{metrics['runs']}, "
            f"context={metrics['context_reuse']}, model={metrics['model']}")


def critic_tokens(critic: dict) -> str:
    values = critic["input_tokens"], critic["output_tokens"]
    return str(sum(values)) if all(type(value) is int for value in values) else "UNKNOWN"


def render(slug: str, baseline: dict, new: dict, critic: dict,
           required_check_ids: set[str], *, donor: dict, donor_label: str, diff_sha256: str,
           transcript_sha256: str) -> tuple[str, str]:
    baseline = validate_arm(baseline, require_limits=False)
    donor = validate_arm(donor, require_limits=False)
    new = validate_arm(new, require_limits=True)
    if not donor_label.strip():
        raise ValueError("donor label must be non-empty")
    critic = validate_critic(critic, required_check_ids, diff_sha256=diff_sha256,
                             transcript_sha256=transcript_sha256)
    base_checks, donor_checks, new_checks = baseline["checks"], donor["checks"], new["checks"]
    br, dr, nr = pass_rate(base_checks), pass_rate(donor_checks), pass_rate(new_checks)
    failures = limit_failures(new) + donor_failures(baseline, donor, new)
    v = "FAIL" if (failures or any(not check.get("passed") for check in new_checks)
                   or critic["verdict"] == "BLOCK") else verdict(br, nr)
    findings = [f"- {g.get('assertion', '?')}: baseline FAIL" for g in base_checks
                if not g.get("passed")]
    findings += [f"- {g.get('assertion', '?')}: nuovo FAIL ({g.get('evidence', 'no evidence')})"
                 for g in new_checks if not g.get("passed")]
    findings += [f"- efficiency: {failure}" for failure in failures]
    findings += [f"- critic: {finding}" for finding in critic["findings"]]
    bm, dm, nm = baseline["metrics"], donor["metrics"], new["metrics"]
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    lines = [
        f"## REVIEW REPORT — skill-meta eval cieca — {slug} — {ts}",
        f"Baseline: {br[0]}/{br[1]} ({br[0] / br[1]:.0%})" if br[1] else "Baseline: n/d",
        f"Donor {donor_label}: {dr[0]}/{dr[1]} ({dr[0] / dr[1]:.0%})",
        f"Nuovo:    {nr[0]}/{nr[1]} ({nr[0] / nr[1]:.0%})" if nr[1] else "Nuovo: n/d",
        cost_line("Baseline", baseline),
        cost_line(f"Donor {donor_label}", donor),
        cost_line("New", new),
        f"Delta: tokens={token_delta(nm, bm)}, "
        f"wall_ms={nm['wall_ms'] - bm['wall_ms']:+d}, "
        f"tool_calls={nm['tool_calls'] - bm['tool_calls']:+d}",
        f"Donor delta: tokens={token_delta(nm, dm)}, "
        f"wall_ms={nm['wall_ms'] - dm['wall_ms']:+d}, "
        f"tool_calls={nm['tool_calls'] - dm['tool_calls']:+d}",
        f"Critic: {critic['verdict']}, context=fresh, model={critic['model']}, "
        f"tokens={critic_tokens(critic)}, wall_ms={critic['wall_ms']}",
        "Findings:",
        *(findings or ["- nessun assertion fallito"]),
        f"VERDICT: {v}",
        SENTINEL,
    ]
    return v, "\n".join(lines) + "\n"


def selfcheck() -> int:
    metrics = {"model": "demo", "input_tokens": 10, "output_tokens": 2, "wall_ms": 30,
               "tool_calls": 2, "repeated_commands": 0, "consistent_runs": 3, "runs": 3,
               "context_reuse": "not_available"}
    limits = {"max_total_tokens": 20, "max_wall_ms": 40, "max_tool_calls": 3,
              "max_repeated_commands": 0, "min_consistency": 1.0}
    baseline = {"checks": [{"id": "a", "assertion": "a", "passed": False},
                            {"id": "b", "assertion": "b", "passed": True}], "metrics": metrics}
    better = {"checks": [{"id": "a", "assertion": "a", "passed": True, "evidence": "e1"},
                          {"id": "b", "assertion": "b", "passed": True, "evidence": "e2"}],
              "metrics": metrics, "limits": limits}
    same = {"checks": better["checks"], "metrics": metrics, "limits": limits}
    worse = {"checks": [{"id": "a", "assertion": "a", "passed": False},
                         {"id": "b", "assertion": "b", "passed": False}],
             "metrics": metrics, "limits": limits}
    critic = {"agent_type": "critic", "fork_turns": "none", "verdict": "PASS",
              "findings": [], "review_lanes": ["critic"],
              "reviewed_diff_sha256": "a" * 64, "transcript_sha256": "b" * 64,
              "graded_checks": [{"id": "c1", "passed": True,
                                  "evidence": "command returned expected exit"}],
              "attacks": {key: {
                  "inventory": [f"bundle/{key}:negative-branch"],
                  "probes": [{"target": f"bundle/{key}:negative-branch", "passed": True,
                              "evidence": f"forced {key} negative branch"}]}
                          for key in ATTACK_KEYS},
              "model": "demo", "input_tokens": 20,
              "output_tokens": 5, "wall_ms": 50}
    required = {"c1"}
    seals = {"diff_sha256": "a" * 64, "transcript_sha256": "b" * 64}
    comparison = {"donor": baseline, "donor_label": "demo donor", **seals}
    v1, r1 = render("demo", baseline, better, critic, required, **comparison)
    assert v1 == "PASS" and "VERDICT: PASS" in r1 and r1.rstrip().endswith(SENTINEL)
    v2, _ = render("demo", {"checks": better["checks"], "metrics": metrics}, same,
                   critic, required, **comparison)
    assert v2 == "CONCERNS", "nessun miglioramento misurabile = CONCERNS, non un pass silenzioso"
    v2b, _ = render("demo", baseline,
                     {"checks": baseline["checks"], "metrics": metrics, "limits": limits},
                     critic, required, **comparison)
    assert v2b == "FAIL", "un candidate check falso non passa per miglioramento relativo"
    v3, _ = render("demo", baseline, worse, critic, required, **comparison)
    assert v3 == "FAIL", "la skill nuova peggiora il pass-rate: deve fallire"
    over = {**better, "metrics": {**metrics, "wall_ms": 41}}
    v4, r4 = render("demo", baseline, over, critic, required, **comparison)
    assert v4 == "FAIL" and "wall_ms 41 > 40" in r4
    blocked = {**critic, "verdict": "BLOCK", "findings": ["sibling branch omitted"]}
    v5, r5 = render("demo", baseline, better, blocked, required, **comparison)
    assert v5 == "FAIL" and "critic: sibling branch omitted" in r5
    try:
        render("demo", baseline, better, {**critic, "fork_turns": "all"}, required,
               **comparison)
    except ValueError as exc:
        assert "fresh context" in str(exc)
    else:
        raise AssertionError("un critic con contesto ereditato deve essere rifiutato")
    try:
        render("demo", baseline, better, critic, required,
               donor=baseline, donor_label="demo donor",
               diff_sha256="0" * 64, transcript_sha256="b" * 64)
    except ValueError as exc:
        assert "supplied diff" in str(exc)
    else:
        raise AssertionError("una receipt su un diff diverso deve essere rifiutata")
    generic = {**critic, "attacks": {**critic["attacks"], "bypasses": {
        "inventory": ["generic"],
        "probes": [{"target": "generic", "passed": True, "evidence": "attempted"}]}}}
    try:
        render("demo", baseline, better, generic, required, **comparison)
    except ValueError as exc:
        assert "concrete targets" in str(exc)
    else:
        raise AssertionError("evidenza adversarial generica deve essere rifiutata")
    try:
        validate_arm(baseline["checks"], require_limits=False)
    except ValueError as exc:
        assert "metrics" in str(exc)
    else:
        raise AssertionError("un grading legacy senza metrics deve essere rifiutato")
    print("SELFCHECK OK — PASS/CONCERNS/FAIL, cost receipt e critic fresco bloccanti")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path)
    p.add_argument("--donor", type=Path)
    p.add_argument("--donor-label")
    p.add_argument("--new", type=Path)
    p.add_argument("--critic", type=Path)
    p.add_argument("--checks", type=Path)
    p.add_argument("--diff", type=Path)
    p.add_argument("--critic-transcript", type=Path)
    p.add_argument("--skill")
    p.add_argument("--append", type=Path)
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not (a.baseline and a.donor and a.donor_label and a.new and a.critic and a.checks and a.diff
            and a.critic_transcript and a.skill):
        p.error("servono --baseline --donor --donor-label --new --critic --checks --diff "
                "--critic-transcript --skill (o --selfcheck)")
    try:
        baseline = json.loads(a.baseline.read_text())
        donor = json.loads(a.donor.read_text())
        new = json.loads(a.new.read_text())
        critic = json.loads(a.critic.read_text())
        required_check_ids = load_check_ids(json.loads(a.checks.read_text()))
        diff_sha256 = hashlib.sha256(a.diff.read_bytes()).hexdigest()
        transcript_sha256 = hashlib.sha256(a.critic_transcript.read_bytes()).hexdigest()
        v, report = render(a.skill, baseline, new, critic, required_check_ids,
                           donor=donor, donor_label=a.donor_label,
                           diff_sha256=diff_sha256, transcript_sha256=transcript_sha256)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    if a.append:
        with a.append.open("a") as f:
            f.write("\n" + report)
    else:
        print(report)
    return 0 if v != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
