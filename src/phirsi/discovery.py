"""R6 bounded improvement-search demonstration with replayable experiment ledger.

Only PRE-REVIEWED R1 registered prime-count algorithms execute. The same-algorithm
negative control is mandatory, and selection uses development measurements only.
A single distinct evaluation seed is consulted ONCE, after selection. This is
not a secret holdout, autonomous source generation, statistical replication,
trusted chronology or deployment permission.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from time import monotonic
from typing import Any

from .algorithms import ALGORITHMS
from .lab import InvalidExperiment, bounded_int, digest, run_experiment, verify_receipt

PLAN_SCHEMA = "phirsi.discovery_plan.v1"
LEDGER_SCHEMA = "phirsi.discovery_ledger.v1"
CANDIDATES = ["trial", "sieve"]
EMPTY_HASH = "0" * 64
PLAN_FIELDS = frozenset({
    "schema", "hypothesis", "candidates", "baseline", "seed_development",
    "seed_evaluation", "max_n", "cases", "rounds", "warmups",
    "min_dev_speedup", "min_eval_speedup", "min_eval_case_fraction",
    "max_candidates", "max_evaluations", "max_wall_seconds",
    "created_utc", "plan_sha256",
})
LEDGER_FIELDS = frozenset({
    "schema", "plan", "runner_code_sha256", "events",
    "decision", "elapsed_wall_seconds", "elapsed_is_unattested",
    "governance", "ledger_sha256",
})
GOVERNANCE = {
    "automatic_promotion": False,
    "human_review_required": True,
    "candidate_code_execution": "built_in_registered_only",
    "external_network_calls": False,
    "model_weight_changes": False,
    "independent_timing_replication": False,
    "model_intelligence_gain_claim": False,
}


def _float(value: Any, low: float, high: float, name: str) -> float:
    if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
        raise InvalidExperiment(f"{name} must be finite number in [{low}, {high}]")
    return float(value)


def _runner_hash() -> str:
    return sha256(Path(__file__).read_bytes()).hexdigest()


def _checked_timestamp(value: Any):
    if type(value) is not str or len(value) > 64:
        raise InvalidExperiment("invalid timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidExperiment("invalid timestamp") from exc
    if parsed.utcoffset() is None:
        raise InvalidExperiment("timestamp must include timezone")


def make_plan(*, hypothesis: str = "Sieve can improve measured prime counting over trial division",
              seed: int = 369, max_n: int = 5000, cases: int = 3,
              rounds: int = 2, warmups: int = 0,
              min_dev_speedup: float = 1.05, min_eval_speedup: float = 1.2,
              min_eval_case_fraction: float = 0.6,
              max_wall_seconds: int = 30) -> dict[str, Any]:
    if type(hypothesis) is not str or not 8 <= len(hypothesis.strip()) <= 240:
        raise InvalidExperiment("hypothesis must be 8-240 characters")
    bounded_int(seed, 0, 2**32 - 1, "seed")
    bounded_int(max_n, 1000, 12000, "max_n")
    bounded_int(cases, 2, 5, "cases")
    bounded_int(rounds, 1, 3, "rounds")
    bounded_int(warmups, 0, 1, "warmups")
    bounded_int(max_wall_seconds, 5, 120, "max_wall_seconds")
    dev = _float(min_dev_speedup, 1.01, 5.0, "min_dev_speedup")
    evaluation = _float(min_eval_speedup, 1.01, 5.0, "min_eval_speedup")
    fraction = _float(min_eval_case_fraction, 0.5, 1.0, "min_eval_case_fraction")
    plan = {
        "schema": PLAN_SCHEMA,
        "hypothesis": hypothesis.strip(),
        "candidates": list(CANDIDATES),
        "baseline": "trial",
        "seed_development": seed,
        "seed_evaluation": (seed ^ 0x9E3779B9) & 0xFFFFFFFF,
        "max_n": max_n, "cases": cases, "rounds": rounds, "warmups": warmups,
        "min_dev_speedup": dev, "min_eval_speedup": evaluation,
        "min_eval_case_fraction": fraction,
        "max_candidates": len(CANDIDATES), "max_evaluations": 1,
        "max_wall_seconds": max_wall_seconds,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    plan["plan_sha256"] = digest(plan)
    return plan


def validate_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or set(plan) != PLAN_FIELDS:
        raise InvalidExperiment("unrecognized discovery plan")
    if plan["schema"] != PLAN_SCHEMA or plan["baseline"] != "trial":
        raise InvalidExperiment("unsupported discovery protocol or baseline")
    if plan["candidates"] != CANDIDATES or any(name not in ALGORITHMS for name in CANDIDATES):
        raise InvalidExperiment("only registered control and candidate may run")
    if type(plan["hypothesis"]) is not str or not 8 <= len(plan["hypothesis"]) <= 240:
        raise InvalidExperiment("invalid hypothesis")
    if plan["hypothesis"] != plan["hypothesis"].strip():
        raise InvalidExperiment("hypothesis is not canonical")
    seed = bounded_int(plan["seed_development"], 0, 2**32 - 1, "seed_development")
    if type(plan["seed_evaluation"]) is not int or plan["seed_evaluation"] != ((seed ^ 0x9E3779B9) & 0xFFFFFFFF):
        raise InvalidExperiment("evaluation seed does not match plan")
    bounded_int(plan["max_n"], 1000, 12000, "max_n")
    bounded_int(plan["cases"], 2, 5, "cases")
    bounded_int(plan["rounds"], 1, 3, "rounds")
    bounded_int(plan["warmups"], 0, 1, "warmups")
    bounded_int(plan["max_wall_seconds"], 5, 120, "max_wall_seconds")
    if plan["max_candidates"] != 2 or type(plan["max_candidates"]) is not int:
        raise InvalidExperiment("candidate budget changed")
    if plan["max_evaluations"] != 1 or type(plan["max_evaluations"]) is not int:
        raise InvalidExperiment("evaluation budget changed")
    for name, lo, hi in (
        ("min_dev_speedup", 1.01, 5.0),
        ("min_eval_speedup", 1.01, 5.0),
        ("min_eval_case_fraction", 0.5, 1.0),
    ):
        _float(plan[name], lo, hi, name)
        if type(plan[name]) is not float:
            raise InvalidExperiment("thresholds must use canonical floats")
    _checked_timestamp(plan["created_utc"])
    if plan["plan_sha256"] != digest({k: v for k, v in plan.items() if k != "plan_sha256"}):
        raise InvalidExperiment("plan checksum mismatch; hashes are not authenticated")
    return plan


def _event(ledger: list[dict[str, Any]], phase: str, candidate: str,
           receipt: dict[str, Any]) -> None:
    item = {
        "sequence": len(ledger),
        "previous_event_sha256": ledger[-1]["event_sha256"] if ledger else EMPTY_HASH,
        "phase": phase,
        "candidate": candidate,
        "receipt": receipt,
    }
    item["event_sha256"] = digest(item)
    ledger.append(item)


def _run_one(plan: dict[str, Any], candidate: str, seed: int) -> dict[str, Any]:
    return run_experiment(
        candidate=candidate, seed=seed, max_n=plan["max_n"],
        cases=plan["cases"], rounds=plan["rounds"], warmups=plan["warmups"],
    )


def _check_observation(plan: dict[str, Any], event: Any, index: int, previous: str) -> None:
    if not isinstance(event, dict) or set(event) != {
        "sequence", "previous_event_sha256", "phase", "candidate", "receipt", "event_sha256",
    }:
        raise InvalidExperiment("event shape invalid")
    if type(event["sequence"]) is not int or event["sequence"] != index:
        raise InvalidExperiment("event sequence mismatch")
    if event["previous_event_sha256"] != previous:
        raise InvalidExperiment("event chain broken")
    if event["event_sha256"] != digest({k: v for k, v in event.items() if k != "event_sha256"}):
        raise InvalidExperiment("event checksum mismatch")
    receipt = event["receipt"]
    if not verify_receipt(receipt)["passed"]:
        raise InvalidExperiment("existing R1 verifier rejected embedded measurement")
    cfg = receipt["experiment"]
    expected_seed = (
        plan["seed_development"] if event["phase"] == "development"
        else plan["seed_evaluation"]
    )
    match = {
        "workload": "prime-count", "baseline": "trial",
        "candidate": event["candidate"], "seed": expected_seed,
        "max_n": plan["max_n"], "cases": plan["cases"],
        "rounds": plan["rounds"], "warmups": plan["warmups"],
    }
    if any(cfg.get(k) != v for k, v in match.items()):
        raise InvalidExperiment("measurement does not match predeclared plan")


def _derive(plan: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    dev = [e for e in events if e["phase"] == "development"]
    evaluation = [e for e in events if e["phase"] == "evaluation"]
    completed = len(dev) == len(CANDIDATES)
    candidate = None
    speed = None
    if completed:
        # Never select a same-algorithm negative control.
        sieve_dev = next(e for e in dev if e["candidate"] == "sieve")
        sieve_speed = sieve_dev["receipt"]["summary"]["geomean_observed_speedup"]
        if sieve_dev["receipt"]["summary"]["correctness_passed"] and sieve_speed >= plan["min_dev_speedup"]:
            candidate = "sieve"
    if not completed:
        status = "BUDGET_STOPPED"
    elif candidate is None:
        status = "NO_ELIGIBLE_CANDIDATE"
    elif not evaluation:
        status = "BUDGET_STOPPED"
    else:
        measurement = evaluation[0]["receipt"]
        speed = measurement["summary"]["geomean_observed_speedup"]
        passed = sum(
            row["baseline"]["median_ns"] / row["candidate"]["median_ns"] >= plan["min_eval_speedup"]
            for row in measurement["observations"]
        )
        fraction = passed / plan["cases"]
        status = (
            "OBSERVATIONAL_SUPPORT"
            if measurement["summary"]["correctness_passed"]
            and speed >= plan["min_eval_speedup"]
            and fraction >= plan["min_eval_case_fraction"]
            else "NOT_SUPPORTED"
        )
    return {
        "status": status,
        "selected_candidate": candidate,
        "evaluated_candidate": evaluation[0]["candidate"] if evaluation else None,
        "development_candidates_measured": [e["candidate"] for e in dev],
        "negative_control_executed": bool(dev and dev[0]["candidate"] == "trial"),
        "evaluation_observed_speedup": speed,
        "evaluation_used_once": len(evaluation) == 1,
        "automatic_promotion": False,
        "human_review_required": True,
        "independent_replication": False,
        "model_intelligence_improvement_claim": False,
    }


def _validate_events(plan: dict[str, Any], events: Any) -> None:
    if not isinstance(events, list) or len(events) > 3:
        raise InvalidExperiment("event count exceeds budget")
    previous = EMPTY_HASH
    dev_seen = []
    eval_seen = 0
    for index, event in enumerate(events):
        _check_observation(plan, event, index, previous)
        previous = event["event_sha256"]
        if event["phase"] == "development":
            if eval_seen or len(dev_seen) >= len(CANDIDATES):
                raise InvalidExperiment("invalid development phase ordering")
            if event["candidate"] != CANDIDATES[len(dev_seen)]:
                raise InvalidExperiment("control or candidate order altered")
            dev_seen.append(event["candidate"])
        elif event["phase"] == "evaluation":
            if eval_seen or dev_seen != CANDIDATES or event["candidate"] != "sieve":
                raise InvalidExperiment("evaluation cannot precede a full controlled search")
            if (events[1]["receipt"]["summary"]["geomean_observed_speedup"]
                    < plan["min_dev_speedup"]):
                raise InvalidExperiment("evaluation conducted without eligible candidate")
            eval_seen += 1
        else:
            raise InvalidExperiment("unregistered ledger phase")


def run_discovery(plan: Any, *, approved: bool = False,
                  clock=monotonic) -> dict[str, Any]:
    validate_plan(plan)
    if approved is not True:
        raise InvalidExperiment("operator approval required even for built-in experiments")
    started = clock()
    events: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        if clock() - started >= plan["max_wall_seconds"]:
            break
        receipt = _run_one(plan, candidate, plan["seed_development"])
        if not verify_receipt(receipt)["passed"]:
            raise InvalidExperiment("development evidence failed independent code-path replay")
        _event(events, "development", candidate, receipt)
    _validate_events(plan, events)
    tentative = _derive(plan, events)
    if (tentative["selected_candidate"] and clock() - started < plan["max_wall_seconds"]):
        receipt = _run_one(plan, tentative["selected_candidate"], plan["seed_evaluation"])
        if not verify_receipt(receipt)["passed"]:
            raise InvalidExperiment("evaluation evidence failed reference replay")
        _event(events, "evaluation", tentative["selected_candidate"], receipt)
    _validate_events(plan, events)
    elapsed = round(max(0.0, clock() - started), 6)
    decision = _derive(plan, events)
    # A soft wall budget may be exceeded by a synchronous trusted algorithm
    # call. Mark the result inconclusive rather than certifying success.
    if elapsed > plan["max_wall_seconds"]:
        decision = {**decision, "status": "BUDGET_STOPPED"}
    result = {
        "schema": LEDGER_SCHEMA,
        "plan": plan,
        "runner_code_sha256": _runner_hash(),
        "events": events,
        "decision": decision,
        "elapsed_wall_seconds": elapsed,
        "elapsed_is_unattested": True,
        "governance": dict(GOVERNANCE),
    }
    result["ledger_sha256"] = digest(result)
    return result


def verify_discovery(ledger: Any) -> dict[str, Any]:
    try:
        if not isinstance(ledger, dict) or set(ledger) != LEDGER_FIELDS:
            raise InvalidExperiment("unrecognized discovery ledger")
        if ledger["schema"] != LEDGER_SCHEMA:
            raise InvalidExperiment("ledger schema mismatch")
        if ledger["ledger_sha256"] != digest({
            k: v for k, v in ledger.items() if k != "ledger_sha256"
        }):
            raise InvalidExperiment("ledger checksum mismatch")
        plan = validate_plan(ledger["plan"])
        if ledger["runner_code_sha256"] != _runner_hash():
            raise InvalidExperiment("local discovery source changed")
        _validate_events(plan, ledger["events"])
        if ledger["governance"] != GOVERNANCE or ledger["elapsed_is_unattested"] is not True:
            raise InvalidExperiment("unrecognized authority or elapsed-time claims")
        elapsed = ledger["elapsed_wall_seconds"]
        if type(elapsed) not in (int, float) or not isfinite(elapsed) or elapsed < 0:
            raise InvalidExperiment("elapsed time is malformed")
        expected = _derive(plan, ledger["events"])
        if elapsed > plan["max_wall_seconds"]:
            expected["status"] = "BUDGET_STOPPED"
        if ledger["decision"] != expected:
            raise InvalidExperiment("stored decision is inconsistent with evidence")
        return {
            "passed": True,
            "status": expected["status"],
            "embedded_correctness_replayed": True,
            "event_chain_checked": True,
            "plan_consistency_checked": True,
            "historical_timings_authenticated": False,
            "independent_replication": False,
            "automatic_promotion": False,
        }
    except (InvalidExperiment, ValueError, KeyError, TypeError, IndexError,
            OverflowError, ZeroDivisionError):
        return {
            "passed": False, "status": "REJECTED",
            "historical_timings_authenticated": False,
            "independent_replication": False,
            "automatic_promotion": False,
        }
