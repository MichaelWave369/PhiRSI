"""R8: controlled local PhiServe A/B inference observations.

This is not an intelligence benchmark, independent replication, model origin
attestation, or a remotely callable service. Only an explicitly approved local
operator can send bounded requests to the fixed 127.0.0.1 PhiServe API.

The shared R4 HTTP client enforces loopback routing, capped JSON bodies and no
redirects, proxy access, model downloads, remote servers or secret logging.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from math import ceil, isfinite
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from typing import Any

from .lab import InvalidExperiment, bounded_int, digest
from .phiserve_bench import (
    CASES, SYSTEM, _config as r4_config,
    _extract_answer, _hash_answer, _validate_token,
    preflight, request_json,
)

PLAN_SCHEMA = "phirsi.phiserve_pair_plan.v1"
RECEIPT_SCHEMA = "phirsi.phiserve_pair_receipt.v1"
SUMMARY_SCHEMA = "phirsi.phiserve_pair_summary.v1"
GUARD = {
    "automatic_promotion": False,
    "human_review_required": True,
    "model_identity_authenticated": False,
    "distinct_weights_verified": False,
    "inference_execution_independently_attested": False,
    "historical_timings_authenticated": False,
    "gpu_vram_measured": False,
    "quality_is_only_fixed_exact_match": True,
    "statistical_significance_claim": False,
    "model_intelligence_improvement_claim": False,
    "network_outside_loopback": False,
    "model_downloads_or_weight_modifications": False,
}
PLAN_KEYS = frozenset({
    "schema", "model_a", "model_b", "port", "rounds", "max_tokens",
    "timeout_seconds", "seed", "temperature", "stream", "case_set_sha256",
    "created_utc", "plan_sha256",
})
RECEIPT_KEYS = frozenset({
    "schema", "plan", "code_sha256", "recorded_utc", "observations",
    "assessment", "governance", "receipt_sha256",
})
MAX_ROUNDS = 2


def _local_fingerprint() -> str:
    return sha256(Path(__file__).read_bytes()).hexdigest()


def _timestamp(value: Any) -> None:
    if type(value) is not str or len(value) > 64:
        raise InvalidExperiment("invalid local timestamp")
    try:
        when = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidExperiment("invalid local timestamp") from exc
    if when.utcoffset() is None:
        raise InvalidExperiment("timestamp must include timezone")


def make_plan(*, model_a: str, model_b: str, port: int = 11435,
              rounds: int = 1, max_tokens: int = 32,
              timeout_seconds: int = 30, seed: int = 369) -> dict[str, Any]:
    # Reuse actual R4 model alias validation and request bounds.
    r4_config(model_a, port, rounds, max_tokens, timeout_seconds, seed)
    r4_config(model_b, port, rounds, max_tokens, timeout_seconds, seed)
    bounded_int(rounds, 1, MAX_ROUNDS, "rounds")
    if model_a == model_b:
        raise InvalidExperiment("A/B aliases must be distinct; use R4 for one alias")
    plan = {
        "schema": PLAN_SCHEMA,
        "model_a": model_a, "model_b": model_b,
        "port": port, "rounds": rounds, "max_tokens": max_tokens,
        "timeout_seconds": timeout_seconds, "seed": seed,
        "temperature": 0, "stream": False,
        "case_set_sha256": digest(list(CASES)),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    plan["plan_sha256"] = digest(plan)
    return plan


def validate_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or set(plan) != PLAN_KEYS:
        raise InvalidExperiment("invalid or unsupported R8 plan shape")
    if plan["schema"] != PLAN_SCHEMA:
        raise InvalidExperiment("unsupported R8 plan version")
    canonical = r4_config(
        plan["model_a"], plan["port"], plan["rounds"], plan["max_tokens"],
        plan["timeout_seconds"], plan["seed"],
    )
    r4_config(plan["model_b"], plan["port"], plan["rounds"],
              plan["max_tokens"], plan["timeout_seconds"], plan["seed"])
    if not 1 <= plan["rounds"] <= MAX_ROUNDS or plan["model_a"] == plan["model_b"]:
        raise InvalidExperiment("R8 requires two distinct aliases and at most two rounds")
    for name in ("port", "rounds", "max_tokens", "timeout_seconds", "seed"):
        if plan[name] != canonical[name] or type(plan[name]) is not int:
            raise InvalidExperiment("invalid canonical R8 parameter")
    if plan["temperature"] != 0 or type(plan["temperature"]) is not int or plan["stream"] is not False:
        raise InvalidExperiment("only deterministic, non-streaming inference registered")
    if plan["case_set_sha256"] != digest(list(CASES)):
        raise InvalidExperiment("fixed public task set fingerprint mismatch")
    _timestamp(plan["created_utc"])
    if plan["plan_sha256"] != digest({k: v for k, v in plan.items() if k != "plan_sha256"}):
        raise InvalidExperiment("R8 plan checksum mismatch (not trusted preregistration)")
    return plan


def _order(round_index: int, case_index: int) -> tuple[str, str]:
    # Alternate AB / BA per case and round to reduce, not eliminate, ordering bias.
    return ("A", "B") if (round_index * len(CASES) + case_index) % 2 == 0 else ("B", "A")


def _aggregate(rows: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    each = {}
    for role in ("A", "B"):
        group = [row for row in rows if row["role"] == role]
        times = [row["end_to_end_latency_ms"] for row in group]
        tokens = [row["provider_completion_tokens"] for row in group]
        all_tokens_reported = all(value is not None for value in tokens)
        each[role] = {
            "registered_alias": plan["model_a"] if role == "A" else plan["model_b"],
            "request_count": len(group),
            "exact_match_count": sum(int(row["exact_match"]) for row in group),
            "exact_match_fraction": round(sum(int(row["exact_match"]) for row in group) / len(group), 6),
            "median_end_to_end_latency_ms": round(median(times), 3),
            "p95_end_to_end_latency_ms": sorted(times)[ceil(len(times) * 0.95) - 1],
            "provider_reported_completion_tokens": sum(tokens) if all_tokens_reported else None,
            "estimated_end_to_end_tokens_per_sec": (
                round(sum(tokens) / (sum(times) / 1000), 3)
                if all_tokens_reported else None
            ),
        }
    pairs = []
    for r in range(plan["rounds"]):
        for c, case in enumerate(CASES):
            group = [
                row for row in rows
                if row["round"] == r + 1 and row["case_id"] == case["id"]
            ]
            times = {row["role"]: row["end_to_end_latency_ms"] for row in group}
            exact = {row["role"]: row["exact_match"] for row in group}
            pairs.append({
                "round": r + 1,
                "case_id": case["id"],
                "observed_a_over_b_latency_ratio": round(times["A"] / times["B"], 6),
                "a_exact_match": exact["A"],
                "b_exact_match": exact["B"],
            })
    ratios = [pair["observed_a_over_b_latency_ratio"] for pair in pairs]
    return {
        "models": each,
        "paired_task_count": len(pairs),
        "paired_observations": pairs,
        "median_observed_a_over_b_latency_ratio": round(median(ratios), 6),
        "b_faster_pair_count": sum(pair["observed_a_over_b_latency_ratio"] > 1.0 for pair in pairs),
        "a_faster_pair_count": sum(pair["observed_a_over_b_latency_ratio"] < 1.0 for pair in pairs),
        "tie_pair_count": sum(pair["observed_a_over_b_latency_ratio"] == 1.0 for pair in pairs),
        "decision": "DESCRIPTIVE_ONLY_NO_WINNER",
        "task_quality_generalization_claim": False,
        "decode_only_throughput_measured": False,
        "first_token_latency_measured": False,
        "gpu_vram_measured": False,
        "automatic_promotion": False,
    }


def run_pair(plan: Any, *, token: str | None = None, approved: bool = False) -> dict[str, Any]:
    """Real calls to one already running PhiServe instance, never from CI.

    A model load/switch can dominate first-call latency, and aliases may map to
    identical underlying weights. Preserve those uncertainties in the receipt.
    """
    validate_plan(plan)
    if approved is not True:
        raise InvalidExperiment("operator must explicitly approve local A/B inference")
    _validate_token(token)
    # Preflight uses read-only GETs; no network requests before approval.
    preflight(model=plan["model_a"], port=plan["port"], token=token)
    preflight(model=plan["model_b"], port=plan["port"], token=token)
    records = []
    for round_index in range(plan["rounds"]):
        for case_index, case in enumerate(CASES):
            for position, role in enumerate(_order(round_index, case_index), start=1):
                alias = plan["model_a"] if role == "A" else plan["model_b"]
                body = {
                    "model": alias,
                    "stream": False,
                    "temperature": 0,
                    "seed": plan["seed"],
                    "max_tokens": plan["max_tokens"],
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": case["prompt"]},
                    ],
                }
                started = perf_counter_ns()
                result = request_json(
                    "POST", "/v1/chat/completions", port=plan["port"],
                    timeout_seconds=plan["timeout_seconds"], token=token,
                    payload=body,
                )
                elapsed = max(0.001, round((perf_counter_ns() - started) / 1_000_000, 3))
                answer, reported_tokens = _extract_answer(result)
                signature = _hash_answer(answer)
                records.append({
                    "round": round_index + 1, "case_id": case["id"],
                    "role": role, "position_in_pair": position,
                    "response_sha256": signature,
                    "exact_match": signature == _hash_answer(case["expected"]),
                    "end_to_end_latency_ms": elapsed,
                    "provider_completion_tokens": reported_tokens,
                })
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "plan": plan,
        "code_sha256": _local_fingerprint(),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "observations": records,
        "assessment": _aggregate(records, plan),
        "governance": dict(GUARD),
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def _validate_rows(rows: Any, plan: dict[str, Any]) -> None:
    if not isinstance(rows, list) or len(rows) != plan["rounds"] * len(CASES) * 2:
        raise InvalidExperiment("missing or surplus paired observations")
    idx = 0
    for round_index in range(plan["rounds"]):
        for case_index, case in enumerate(CASES):
            for position, role in enumerate(_order(round_index, case_index), start=1):
                row = rows[idx]
                idx += 1
                if not isinstance(row, dict) or set(row) != {
                    "round", "case_id", "role", "position_in_pair",
                    "response_sha256", "exact_match", "end_to_end_latency_ms",
                    "provider_completion_tokens",
                }:
                    raise InvalidExperiment("invalid R8 observation fields")
                if (type(row["round"]) is not int or row["round"] != round_index + 1
                        or row["case_id"] != case["id"]
                        or row["role"] != role
                        or type(row["position_in_pair"]) is not int
                        or row["position_in_pair"] != position):
                    raise InvalidExperiment("recorded model/case ordering was altered")
                signature = row["response_sha256"]
                if type(signature) is not str or len(signature) != 64 or any(
                    char not in "0123456789abcdef" for char in signature
                ):
                    raise InvalidExperiment("invalid model output hash")
                if (type(row["exact_match"]) is not bool
                        or row["exact_match"] != (signature == _hash_answer(case["expected"]))):
                    raise InvalidExperiment("recorded fixed-task score is inconsistent")
                latency = row["end_to_end_latency_ms"]
                if (type(latency) not in (int, float) or not isfinite(latency)
                        or not 0 < latency <= plan["timeout_seconds"] * 1000 + 1000):
                    raise InvalidExperiment("invalid recorded end-to-end latency")
                tokens = row["provider_completion_tokens"]
                if tokens is not None and (type(tokens) is not int or not 0 <= tokens <= 10000):
                    raise InvalidExperiment("invalid provider-reported token count")


def verify_pair(receipt: Any) -> dict[str, Any]:
    """Internal arithmetic/protocol consistency only; no model inference replay."""
    try:
        if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
            raise InvalidExperiment("invalid R8 receipt shape")
        if receipt["schema"] != RECEIPT_SCHEMA:
            raise InvalidExperiment("unknown R8 receipt schema")
        if receipt["receipt_sha256"] != digest({
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        }):
            raise InvalidExperiment("receipt checksum mismatch")
        plan = validate_plan(receipt["plan"])
        if receipt["code_sha256"] != _local_fingerprint():
            raise InvalidExperiment("local experiment source changed")
        _timestamp(receipt["recorded_utc"])
        if receipt["governance"] != GUARD:
            raise InvalidExperiment("unapproved governance or provenance claims")
        _validate_rows(receipt["observations"], plan)
        if receipt["assessment"] != _aggregate(receipt["observations"], plan):
            raise InvalidExperiment("R8 model comparison metrics mismatch")
        return {
            "passed": True,
            "protocol_and_arithmetic_consistent": True,
            "historical_inference_authenticated": False,
            "model_weights_verified": False,
            "timings_independently_replicated": False,
            "automatic_promotion": False,
        }
    except (InvalidExperiment, ValueError, TypeError, KeyError, IndexError,
            ZeroDivisionError, OverflowError):
        return {
            "passed": False,
            "protocol_and_arithmetic_consistent": False,
            "historical_inference_authenticated": False,
            "model_weights_verified": False,
            "timings_independently_replicated": False,
            "automatic_promotion": False,
        }


def summary_for_browser(receipt: Any) -> dict[str, Any]:
    if not verify_pair(receipt)["passed"]:
        raise InvalidExperiment("cannot export a summary of invalid R8 receipt")
    summary = {
        "schema": SUMMARY_SCHEMA,
        "source_receipt_sha256": receipt["receipt_sha256"],
        "created_utc": receipt["recorded_utc"],
        "model_a_alias": receipt["plan"]["model_a"],
        "model_b_alias": receipt["plan"]["model_b"],
        "fixed_case_count": len(CASES),
        "rounds": receipt["plan"]["rounds"],
        "metrics": receipt["assessment"],
        "governance": dict(GUARD),
        "browser_only_shape_inspection": True,
        "report_is_not_authenticated": True,
    }
    summary["summary_sha256"] = digest(summary)
    return summary
