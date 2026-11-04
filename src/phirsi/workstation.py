"""R10: review-only repeat-run acceptance dossier from original R9 receipts.

No inference, GPU calls, network requests, shell commands, model modifications,
or deployment authority exist in this module. All original R9 records are
preserved and individually checked against the current local R9 implementation.

An operator's "initial" versus "repeat" labels are ordering labels only. They
do NOT attest cold starts, warmed weights, a shared physical host, or execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from statistics import median
from typing import Any

from .field_lab import CASE_HASH, _source_hash, validate_plan as validate_r9_plan, verify_field
from .field_lab import make_plan as make_r9_plan
from .lab import InvalidExperiment, bounded_int, digest

PLAN_SCHEMA = "phirsi.workstation_acceptance_plan.v1"
DOSSIER_SCHEMA = "phirsi.workstation_acceptance_dossier.v1"
SUMMARY_SCHEMA = "phirsi.workstation_acceptance_summary.v1"
MIN_RUNS = 3
MAX_RUNS = 6

PLAN_KEYS = frozenset({
    "schema", "model_a", "model_b", "port", "rounds", "max_tokens",
    "timeout_seconds", "first_seed", "run_count", "quality_floor",
    "max_repeat_median_latency_spread", "task_set_sha256",
    "r9_code_sha256", "created_utc", "plan_sha256",
})
DOSSIER_KEYS = frozenset({
    "schema", "plan", "created_utc", "original_r9_receipts",
    "assessment", "governance", "dossier_sha256",
})
GOVERNANCE = {
    "automatic_promotion": False,
    "human_review_required": True,
    "real_model_execution_authenticated": False,
    "machine_identity_authenticated": False,
    "model_weights_bound_to_server": False,
    "historical_timings_authenticated": False,
    "cold_start_verified": False,
    "warm_cache_verified": False,
    "gpu_execution_independently_verified": False,
    "driver_memory_from_same_r10_run": False,
    "statistical_significance_claim": False,
    "general_intelligence_improvement_claim": False,
    "network_or_model_execution_by_r10": False,
    "model_deployment_authorized": False,
}


def _timestamp(value: Any) -> None:
    if type(value) is not str or len(value) > 64:
        raise InvalidExperiment("invalid timestamp")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidExperiment("invalid timestamp") from exc
    if dt.utcoffset() is None:
        raise InvalidExperiment("timestamp must contain timezone offset")


def _threshold(value: Any, lower: float, upper: float, name: str) -> float:
    if type(value) is not float or not isfinite(value) or not lower <= value <= upper:
        raise InvalidExperiment(f"{name} must be a finite canonical float in [{lower}, {upper}]")
    return value


def make_plan(*, model_a: str, model_b: str, port: int = 11435,
              rounds: int = 1, max_tokens: int = 32, timeout_seconds: int = 30,
              first_seed: int = 369, run_count: int = 3,
              quality_floor: float = 0.75,
              max_repeat_median_latency_spread: float = 2.0) -> dict[str, Any]:
    bounded_int(run_count, MIN_RUNS, MAX_RUNS, "run_count")
    bounded_int(first_seed, 0, 2**32 - run_count, "first_seed")
    _threshold(quality_floor, 0.5, 1.0, "quality_floor")
    _threshold(max_repeat_median_latency_spread, 1.0, 5.0, "max_repeat_median_latency_spread")
    # Reuse the actual R9 operator/transport and task-compatibility bounds.
    make_r9_plan(model_a=model_a, model_b=model_b, port=port, rounds=rounds,
                 max_tokens=max_tokens, timeout_seconds=timeout_seconds, seed=first_seed)
    plan = {
        "schema": PLAN_SCHEMA, "model_a": model_a, "model_b": model_b,
        "port": port, "rounds": rounds, "max_tokens": max_tokens,
        "timeout_seconds": timeout_seconds, "first_seed": first_seed,
        "run_count": run_count, "quality_floor": quality_floor,
        "max_repeat_median_latency_spread": max_repeat_median_latency_spread,
        "task_set_sha256": CASE_HASH, "r9_code_sha256": _source_hash(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    plan["plan_sha256"] = digest(plan)
    return plan


def validate_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or set(plan) != PLAN_KEYS or plan["schema"] != PLAN_SCHEMA:
        raise InvalidExperiment("unrecognized R10 acceptance plan")
    bounded_int(plan["run_count"], MIN_RUNS, MAX_RUNS, "run_count")
    bounded_int(plan["first_seed"], 0, 2**32-plan["run_count"], "first_seed")
    for name in ("port", "rounds", "max_tokens", "timeout_seconds"):
        if type(plan[name]) is not int:
            raise InvalidExperiment("noncanonical R9 configuration")
    make_r9_plan(
        model_a=plan["model_a"], model_b=plan["model_b"], port=plan["port"],
        rounds=plan["rounds"], max_tokens=plan["max_tokens"],
        timeout_seconds=plan["timeout_seconds"], seed=plan["first_seed"],
    )
    _threshold(plan["quality_floor"], .5, 1.0, "quality_floor")
    _threshold(plan["max_repeat_median_latency_spread"], 1.0, 5.0,
               "max_repeat_median_latency_spread")
    _timestamp(plan["created_utc"])
    if plan["task_set_sha256"] != CASE_HASH or plan["r9_code_sha256"] != _source_hash():
        raise InvalidExperiment("R9 task or code revision differs from acceptance plan")
    if plan["plan_sha256"] != digest({k:v for k,v in plan.items() if k != "plan_sha256"}):
        raise InvalidExperiment("R10 plan checksum mismatch; not an authenticated preregistration")
    return plan


def _binding(plan: dict[str, Any], receipt: Any, index: int) -> None:
    if not isinstance(receipt, dict) or not verify_field(receipt)["passed"]:
        raise InvalidExperiment(f"R9 receipt {index+1} failed original R9 verifier")
    if receipt["code_sha256"] != plan["r9_code_sha256"]:
        raise InvalidExperiment("mixed R9 implementation versions are not comparable")
    actual = validate_r9_plan(receipt["plan"])
    expected = {
        "model_a": plan["model_a"], "model_b": plan["model_b"],
        "port": plan["port"], "rounds": plan["rounds"],
        "max_tokens": plan["max_tokens"],
        "timeout_seconds": plan["timeout_seconds"],
        "seed": plan["first_seed"] + index,
        "task_sha256": plan["task_set_sha256"],
    }
    for key,value in expected.items():
        if actual[key] != value:
            raise InvalidExperiment(f"R9 receipt {index+1} differs in {key}")
    if receipt["metrics"]["decision"] != "DESCRIPTIVE_ONLY_NO_WINNER":
        raise InvalidExperiment("R9 receipt claims an unsupported model winner")


def _stable_fingerprints(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    """Only compare file fingerprints if each run includes that operator evidence."""
    outcome = {}
    for role in ("A", "B"):
        values = [r["selected_local_file_fingerprints"].get(role) for r in receipts]
        if any(v is not None for v in values):
            if any(v is None for v in values):
                raise InvalidExperiment("partial GGUF file fingerprints cannot establish consistent evidence")
            if len({v["sha256"] for v in values}) != 1:
                raise InvalidExperiment("different operator-selected GGUF hashes across runs")
            outcome[role] = {
                "declared_file_hash_prefix": values[0]["sha256"][:16],
                "operator_selected_fingerprint_present_all_runs": True,
                "server_weight_binding_verified": False,
            }
        else:
            outcome[role] = {
                "declared_file_hash_prefix": None,
                "operator_selected_fingerprint_present_all_runs": False,
                "server_weight_binding_verified": False,
            }
    return outcome


def _assessment(plan: dict[str, Any], receipts: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(receipts, list) or len(receipts) != plan["run_count"]:
        raise InvalidExperiment("all predeclared R9 runs must be present")
    hashes=set()
    entries=[]
    for index,receipt in enumerate(receipts):
        _binding(plan, receipt, index)
        signature=receipt["receipt_sha256"]
        if signature in hashes:
            raise InvalidExperiment("duplicate R9 receipt")
        hashes.add(signature)
        entries.append({
            "sequence": index+1,
            "operator_run_label": "initial" if index==0 else "repeat",
            "seed": plan["first_seed"]+index,
            "r9_receipt_sha256": signature,
            "model_a_correct": receipt["metrics"]["models"]["A"]["correct_count"],
            "model_b_correct": receipt["metrics"]["models"]["B"]["correct_count"],
            "model_a_accuracy": receipt["metrics"]["models"]["A"]["exact_match_fraction"],
            "model_b_accuracy": receipt["metrics"]["models"]["B"]["exact_match_fraction"],
            "model_a_median_http_ms": receipt["metrics"]["models"]["A"]["median_http_ms"],
            "model_b_median_http_ms": receipt["metrics"]["models"]["B"]["median_http_ms"],
            "includes_separate_phi_serve_telemetry": bool(receipt["separate_phiserve_field_observations"]),
            "historical_execution_authenticated": False,
        })
    fingerprints=_stable_fingerprints(receipts)
    spread={}
    for role in ("A","B"):
        samples=[row[f"model_{role.lower()}_median_http_ms"] for row in entries[1:]]
        if not samples or min(samples) <= 0:
            raise InvalidExperiment("invalid repeated-run median latency")
        spread[role] = round(max(samples)/min(samples),6)
    quality_ok=all(
        row["model_a_accuracy"] >= plan["quality_floor"] and
        row["model_b_accuracy"] >= plan["quality_floor"]
        for row in entries
    )
    spread_ok=all(v <= plan["max_repeat_median_latency_spread"] for v in spread.values())
    return {
        "run_count": len(receipts),
        "run_order_labels_are_operator_declared_not_cold_warm_attestations": True,
        "entries": entries,
        "operator_selected_file_evidence": fingerprints,
        "minimum_exact_match_fraction_observed": {
            role: min(row[f"model_{role.lower()}_accuracy"] for row in entries)
            for role in ("A","B")
        },
        "repeat_only_median_latency_ms": {
            role: round(median([row[f"model_{role.lower()}_median_http_ms"]
                                for row in entries[1:]]),3)
            for role in ("A","B")
        },
        "repeat_only_max_over_min_latency_ratio": spread,
        "quality_threshold_met": quality_ok,
        "repeat_stability_threshold_met": spread_ok,
        "status": "MEETS_CONFIGURED_THRESHOLDS" if quality_ok and spread_ok
                  else "DOES_NOT_MEET_CONFIGURED_THRESHOLDS",
        "qualified_as_independently_verified_workstation": False,
        "automatic_model_selection": False,
        "human_review_required": True,
    }


def build_dossier(plan: Any, receipts: Any) -> dict[str, Any]:
    validate_plan(plan)
    report=_assessment(plan,receipts)
    dossier={
        "schema": DOSSIER_SCHEMA,
        "plan": plan,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "original_r9_receipts": receipts,
        "assessment": report,
        "governance": dict(GOVERNANCE),
    }
    dossier["dossier_sha256"]=digest(dossier)
    return dossier


def verify_dossier(dossier: Any) -> dict[str, Any]:
    try:
        if not isinstance(dossier, dict) or set(dossier) != DOSSIER_KEYS \
           or dossier["schema"] != DOSSIER_SCHEMA:
            raise InvalidExperiment("unsupported R10 dossier")
        if dossier["dossier_sha256"] != digest({
            k:v for k,v in dossier.items() if k != "dossier_sha256"
        }):
            raise InvalidExperiment("dossier checksum mismatch")
        plan=validate_plan(dossier["plan"])
        _timestamp(dossier["created_utc"])
        if dossier["governance"] != GOVERNANCE:
            raise InvalidExperiment("operator-only authority altered")
        derived=_assessment(plan,dossier["original_r9_receipts"])
        if dossier["assessment"] != derived:
            raise InvalidExperiment("R10 outcome not derived from verified original receipts")
        return {
            "passed": True,
            "original_r9_receipts_replayed": True,
            "status": derived["status"],
            "historical_timings_authenticated": False,
            "real_hardware_verified": False,
            "automatic_promotion": False,
        }
    except (InvalidExperiment,ValueError,TypeError,KeyError,IndexError,
            OverflowError,ZeroDivisionError):
        return {
            "passed": False,
            "original_r9_receipts_replayed": False,
            "status": "REJECTED",
            "historical_timings_authenticated": False,
            "real_hardware_verified": False,
            "automatic_promotion": False,
        }


def browser_summary(dossier: Any) -> dict[str, Any]:
    if not verify_dossier(dossier)["passed"]:
        raise InvalidExperiment("cannot export an invalid R10 dossier")
    result={
        "schema": SUMMARY_SCHEMA,
        "source_dossier_sha256": dossier["dossier_sha256"],
        "model_aliases": {
            "A": dossier["plan"]["model_a"],
            "B": dossier["plan"]["model_b"],
        },
        "thresholds": {
            "quality_floor": dossier["plan"]["quality_floor"],
            "max_repeat_median_latency_spread": dossier["plan"]["max_repeat_median_latency_spread"],
        },
        "assessment": dossier["assessment"],
        "governance": dict(GOVERNANCE),
        "shape_only_browser_preview": True,
        "original_receipts_not_in_browser_summary": True,
        "independently_authenticated": False,
    }
    result["summary_sha256"]=digest(result)
    return result
