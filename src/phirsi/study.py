"""R2 precommitted two-split evaluation, with a mandatory negative control.

This is an observational research protocol, NOT authenticated preregistration
or independent timing replication. Only locally registered algorithms run.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any
import json

from .algorithms import ALGORITHMS
from .lab import InvalidExperiment, bounded_int, digest, run_experiment, verify_receipt

PLAN_SCHEMA = "phirsi.plan.v1"
STUDY_SCHEMA = "phirsi.study.v1"
BASELINE = "trial"
PLAN_KEYS = frozenset({
    "schema", "hypothesis", "workload", "baseline", "candidate", "seed_development",
    "seed_evaluation", "max_n", "cases", "rounds", "warmups",
    "min_speedup", "min_case_fraction", "created_utc", "plan_sha256",
})

def _hash_sources() -> str:
    h = sha256()
    parent = Path(__file__).resolve().parent
    for filename in ("algorithms.py", "lab.py", "study.py"):
        h.update(filename.encode() + b"\0")
        h.update((parent / filename).read_bytes())
    return h.hexdigest()

def _finite_float(value: Any, lo: float, hi: float, label: str) -> float:
    if type(value) not in (int, float) or not isfinite(value) or not lo <= value <= hi:
        raise InvalidExperiment(f"{label} must be a finite number in [{lo}, {hi}]")
    return float(value)

def _payload_hash(obj: dict[str, Any], field: str) -> str:
    return digest({k: v for k, v in obj.items() if k != field})

def make_plan(*, candidate: str = "sieve", hypothesis: str = "Sieve reduces prime-count runtime",
              seed: int = 369, max_n: int = 20000, cases: int = 5, rounds: int = 5,
              warmups: int = 1, min_speedup: float = 1.2,
              min_case_fraction: float = 0.6) -> dict[str, Any]:
    if candidate not in ALGORITHMS:
        raise InvalidExperiment("candidate must be a registered local algorithm")
    if type(hypothesis) is not str or not 8 <= len(hypothesis.strip()) <= 240:
        raise InvalidExperiment("hypothesis must have 8-240 nonblank characters")
    bounded_int(seed, 0, 2**32 - 1, "seed")
    bounded_int(max_n, 1000, 100000, "max_n")
    bounded_int(cases, 2, 10, "cases")
    bounded_int(rounds, 1, 10, "rounds")
    bounded_int(warmups, 0, 3, "warmups")
    _finite_float(min_speedup, 1.01, 10.0, "min_speedup")
    _finite_float(min_case_fraction, 0.5, 1.0, "min_case_fraction")
    plan = {
        "schema": PLAN_SCHEMA, "hypothesis": hypothesis.strip(), "workload": "prime-count",
        "baseline": BASELINE, "candidate": candidate, "seed_development": seed,
        "seed_evaluation": (seed ^ 0x9E3779B9) & 0xffffffff,
        "max_n": max_n, "cases": cases, "rounds": rounds, "warmups": warmups,
        "min_speedup": float(min_speedup),
        "min_case_fraction": float(min_case_fraction),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    plan["plan_sha256"] = _payload_hash(plan, "plan_sha256")
    return plan

def validate_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or set(plan) != PLAN_KEYS:
        raise InvalidExperiment("plan fields or schema invalid")
    if plan["schema"] != PLAN_SCHEMA or plan["workload"] != "prime-count":
        raise InvalidExperiment("unsupported protocol")
    if plan["baseline"] != BASELINE or plan["candidate"] not in ALGORITHMS:
        raise InvalidExperiment("unregistered algorithm")
    if type(plan["hypothesis"]) is not str or not 8 <= len(plan["hypothesis"].strip()) <= 240:
        raise InvalidExperiment("invalid hypothesis")
    if plan["hypothesis"] != plan["hypothesis"].strip():
        raise InvalidExperiment("noncanonical hypothesis")
    if type(plan["created_utc"]) is not str or len(plan["created_utc"]) > 64:
        raise InvalidExperiment("invalid timestamp")
    try:
        ts = datetime.fromisoformat(plan["created_utc"])
    except ValueError as e:
        raise InvalidExperiment("invalid timestamp") from e
    if ts.utcoffset() is None:
        raise InvalidExperiment("timestamp must be timezone-aware")
    seed = bounded_int(plan["seed_development"], 0, 2**32 - 1, "seed_development")
    if plan["seed_evaluation"] != ((seed ^ 0x9E3779B9) & 0xffffffff):
        raise InvalidExperiment("evaluation seed mismatch")
    bounded_int(plan["max_n"], 1000, 100000, "max_n")
    bounded_int(plan["cases"], 2, 10, "cases")
    bounded_int(plan["rounds"], 1, 10, "rounds")
    bounded_int(plan["warmups"], 0, 3, "warmups")
    for name, lo, hi in (("min_speedup", 1.01, 10.0),
                         ("min_case_fraction", 0.5, 1.0)):
        value = _finite_float(plan[name], lo, hi, name)
        if type(plan[name]) is not float:
            raise InvalidExperiment(f"{name} must be canonical float")
    if plan["plan_sha256"] != _payload_hash(plan, "plan_sha256"):
        raise InvalidExperiment("plan checksum mismatch: not an authenticated registration")
    return plan

def _run_split(plan: dict[str, Any], seed: int) -> dict[str, Any]:
    return run_experiment(
        candidate=plan["candidate"], seed=seed, max_n=plan["max_n"],
        cases=plan["cases"], rounds=plan["rounds"], warmups=plan["warmups"],
    )

def _assess(plan: dict[str, Any], dev: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    if not dev["summary"]["correctness_passed"] or not evaluation["summary"]["correctness_passed"]:
        status = "incorrect"
    elif plan["candidate"] == plan["baseline"]:
        status = "negative_control"
    else:
        status = "not_supported"
    ratio = evaluation["summary"]["geomean_observed_speedup"]
    passed_cases = sum(
        row["baseline"]["median_ns"] / row["candidate"]["median_ns"] >= plan["min_speedup"]
        for row in evaluation["observations"]
    )
    frac = round(passed_cases / plan["cases"], 6)
    if status == "not_supported" and ratio >= plan["min_speedup"] and frac >= plan["min_case_fraction"]:
        status = "observational_support"
    return {
        "status": status,
        "development_observed_geomean_speedup": dev["summary"]["geomean_observed_speedup"],
        "evaluation_observed_geomean_speedup": ratio,
        "evaluation_cases_meeting_threshold": passed_cases,
        "evaluation_case_fraction_meeting_threshold": frac,
        "human_review_required": True,
        "automatic_promotion": False,
        "independent_timing_replication": False,
        "model_intelligence_gain_claim": False,
    }

def _check_split(plan: dict[str, Any], run: Any, seed: int) -> None:
    checked = verify_receipt(run)
    if not checked["passed"]:
        raise InvalidExperiment(f"embedded R1 receipt rejected: {checked.get('reason')}")
    cfg = run["experiment"]
    expected = {
        "workload": "prime-count", "baseline": BASELINE,
        "candidate": plan["candidate"], "seed": seed,
        "max_n": plan["max_n"], "cases": plan["cases"],
        "rounds": plan["rounds"], "warmups": plan["warmups"],
    }
    for key, value in expected.items():
        if cfg[key] != value:
            raise InvalidExperiment(f"embedded run {key} disagrees with plan")

def run_study(plan: Any) -> dict[str, Any]:
    validate_plan(plan)
    development = _run_split(plan, plan["seed_development"])
    evaluation = _run_split(plan, plan["seed_evaluation"])
    for run, seed in ((development, plan["seed_development"]),
                      (evaluation, plan["seed_evaluation"])):
        _check_split(plan, run, seed)
    result = {
        "schema": STUDY_SCHEMA,
        "plan": plan,
        "study_code_sha256": _hash_sources(),
        "runs": {"development": development, "evaluation": evaluation},
        "assessment": _assess(plan, development, evaluation),
    }
    result["study_sha256"] = _payload_hash(result, "study_sha256")
    return result

def verify_study(study: Any) -> dict[str, Any]:
    try:
        if not isinstance(study, dict) or set(study) != {
            "schema", "plan", "study_code_sha256", "runs", "assessment", "study_sha256"
        }:
            raise InvalidExperiment("invalid study shape")
        if study["schema"] != STUDY_SCHEMA:
            raise InvalidExperiment("unknown study schema")
        if study["study_sha256"] != _payload_hash(study, "study_sha256"):
            raise InvalidExperiment("study checksum mismatch")
        plan = validate_plan(study["plan"])
        if study["study_code_sha256"] != _hash_sources():
            raise InvalidExperiment("study source fingerprint mismatch")
        runs = study["runs"]
        if not isinstance(runs, dict) or set(runs) != {"development", "evaluation"}:
            raise InvalidExperiment("split mismatch")
        _check_split(plan, runs["development"], plan["seed_development"])
        _check_split(plan, runs["evaluation"], plan["seed_evaluation"])
        assessment = _assess(plan, runs["development"], runs["evaluation"])
        if assessment != study["assessment"]:
            raise InvalidExperiment("assessment does not match stored evidence")
        return {
            "passed": True, "status": assessment["status"],
            "correctness_replayed": True,
            "timings_independently_reproduced": False,
            "origin_authenticated": False,
            "automatic_promotion": False,
        }
    except (InvalidExperiment, KeyError, TypeError, ValueError, OverflowError,
            ZeroDivisionError, IndexError) as error:
        return {
            "passed": False, "reason": str(error),
            "timings_independently_reproduced": False,
            "origin_authenticated": False,
            "automatic_promotion": False,
        }
