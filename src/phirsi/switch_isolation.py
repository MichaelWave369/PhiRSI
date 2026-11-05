"""R11: controlled first-request versus repeated-request local PhiServe observations.

Explicit operator permission is required for all loopback calls. The program
never purports to split real model-loading time from prompt prefill or caching.
An alias change is a *request sequence*, not evidence of a backend unload/load.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from typing import Any

from .field_lab import CASES
from .lab import InvalidExperiment, bounded_int, digest
from .phiserve_bench import (
    _config as r4_config, _extract_answer, _hash_answer,
    _validate_token, preflight, request_json,
)

PLAN_SCHEMA = "phirsi.switch_isolation_plan.v1"
RECEIPT_SCHEMA = "phirsi.switch_isolation_receipt.v1"
SUMMARY_SCHEMA = "phirsi.switch_isolation_summary.v1"
# The same prompt is used for the first and repeat requests within each block.
# Different rounds use different public fixed R9 tasks to reduce dependence on
# any one prompt; comparisons are within a single block only.
CASES = tuple(next(case for case in CASES if case["id"] == name)
              for name in ("upper", "add"))
FIXED_CASE_HASH = digest(list(CASES))
SYSTEM = "Reply only with the requested literal answer, without punctuation or explanation."
PLAN_FIELDS = frozenset({
    "schema", "model_a", "model_b", "port", "repeat_requests",
    "max_tokens", "timeout_seconds", "seed", "first_role",
    "fixed_case_sha256", "created_utc", "plan_sha256",
})
ROW_FIELDS = frozenset({
    "block", "round", "role", "model_alias", "case_id",
    "phase", "request_index_in_block", "previous_requested_alias",
    "requested_alias_changed", "answer_sha256", "exact_match",
    "http_latency_ms", "provider_completion_tokens",
})
RECEIPT_FIELDS = frozenset({
    "schema", "plan", "code_sha256", "recorded_utc",
    "observations", "assessment", "governance", "receipt_sha256",
})
GUARD = {
    "automatic_promotion": False,
    "human_review_required": True,
    "same_prompt_within_block": True,
    "alias_change_is_not_model_reload_proof": True,
    "cold_start_verified": False,
    "warm_cache_verified": False,
    "true_model_loading_ms_measured": False,
    "decode_only_latency_measured": False,
    "time_to_first_token_measured": False,
    "served_weights_authenticated": False,
    "gpu_execution_independently_verified": False,
    "statistical_significance_claim": False,
    "general_model_intelligence_gain_claim": False,
    "external_network_or_weight_changes": False,
}


def _timestamp(value: Any) -> None:
    if type(value) is not str or len(value) > 64:
        raise InvalidExperiment("invalid offset-aware timestamp")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidExperiment("invalid timestamp") from exc
    if timestamp.utcoffset() is None:
        raise InvalidExperiment("timestamp lacks timezone")


def _source_hash() -> str:
    return sha256(Path(__file__).read_bytes()).hexdigest()


def make_plan(*, model_a: str, model_b: str, port: int = 11435,
              repeat_requests: int = 2, max_tokens: int = 32,
              timeout_seconds: int = 30, seed: int = 369,
              first_role: str = "A") -> dict[str, Any]:
    r4_config(model_a, port, 1, max_tokens, timeout_seconds, seed)
    r4_config(model_b, port, 1, max_tokens, timeout_seconds, seed)
    bounded_int(repeat_requests, 2, 3, "repeat_requests")
    if model_a == model_b or first_role not in ("A", "B") or type(first_role) is not str:
        raise InvalidExperiment("distinct aliases and first role A/B required")
    plan = {
        "schema": PLAN_SCHEMA, "model_a": model_a, "model_b": model_b,
        "port": port, "repeat_requests": repeat_requests,
        "max_tokens": max_tokens, "timeout_seconds": timeout_seconds,
        "seed": seed, "first_role": first_role,
        "fixed_case_sha256": FIXED_CASE_HASH,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    plan["plan_sha256"] = digest(plan)
    return plan


def validate_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or set(plan) != PLAN_FIELDS or plan["schema"] != PLAN_SCHEMA:
        raise InvalidExperiment("invalid isolation plan shape or version")
    a = r4_config(plan["model_a"], plan["port"], 1, plan["max_tokens"],
                  plan["timeout_seconds"], plan["seed"])
    r4_config(plan["model_b"], plan["port"], 1, plan["max_tokens"],
              plan["timeout_seconds"], plan["seed"])
    if plan["model_a"] == plan["model_b"] or plan["first_role"] not in ("A", "B") \
       or type(plan["first_role"]) is not str:
        raise InvalidExperiment("invalid two-model protocol")
    bounded_int(plan["repeat_requests"], 2, 3, "repeat_requests")
    for name in ("port", "max_tokens", "timeout_seconds", "seed"):
        if type(plan[name]) is not int or a[name] != plan[name]:
            raise InvalidExperiment("noncanonical request bounds")
    if plan["fixed_case_sha256"] != FIXED_CASE_HASH:
        raise InvalidExperiment("fixed two-case schedule changed")
    _timestamp(plan["created_utc"])
    if plan["plan_sha256"] != digest({key:value for key,value in plan.items()
                                     if key != "plan_sha256"}):
        raise InvalidExperiment("plan checksum does not match")
    return plan


def _blocks(plan: dict[str, Any]):
    first = plan["first_role"]
    second = "B" if first == "A" else "A"
    for round_index, case in enumerate(CASES, start=1):
        for role in (first, second):
            yield (round_index, case, role)


def _expected_rows(plan: dict[str, Any]):
    previous = None
    for block, (round_index, case, role) in enumerate(_blocks(plan), start=1):
        alias = plan["model_a"] if role == "A" else plan["model_b"]
        changed = previous is not None and alias != previous
        for index in range(plan["repeat_requests"]+1):
            yield {
                "block": block, "round": round_index,
                "role": role, "model_alias": alias, "case_id": case["id"],
                "phase": "first_request" if index == 0 else "repeat_request",
                "request_index_in_block": index,
                "previous_requested_alias": previous if index == 0 else alias,
                "requested_alias_changed": changed if index == 0 else False,
            }, case
        previous = alias


def _aggregate(rows: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    blocks=[]
    for block in range(1, len(CASES)*2+1):
        samples=[row for row in rows if row["block"] == block]
        first=samples[0]
        repeated=samples[1:]
        first_ms=first["http_latency_ms"]
        repeat_median=round(median(x["http_latency_ms"] for x in repeated), 3)
        blocks.append({
            "block": block, "round": first["round"], "role": first["role"],
            "case_id": first["case_id"],
            "requested_alias_changed": first["requested_alias_changed"],
            "first_http_latency_ms": first_ms,
            "repeat_median_http_latency_ms": repeat_median,
            "observed_first_over_repeat_ratio": round(first_ms/repeat_median, 6),
            "first_exact_match": first["exact_match"],
            "repeats_exact_match_count": sum(x["exact_match"] for x in repeated),
        })
    models={}
    for role in ("A", "B"):
        selected=[row for row in rows if row["role"]==role]
        first=[row for row in selected if row["phase"]=="first_request"]
        repeats=[row for row in selected if row["phase"]=="repeat_request"]
        ratios=[b["observed_first_over_repeat_ratio"] for b in blocks if b["role"]==role]
        models[role]={
            "alias": plan["model_a"] if role == "A" else plan["model_b"],
            "request_count": len(selected),
            "exact_match_count": sum(row["exact_match"] for row in selected),
            "first_median_http_ms": round(median(x["http_latency_ms"] for x in first), 3),
            "repeat_median_http_ms": round(median(x["http_latency_ms"] for x in repeats), 3),
            "median_block_first_over_repeat_ratio": round(median(ratios), 6),
            "first_request_count": len(first),
            "repeat_request_count": len(repeats),
        }
    return {
        "request_count":len(rows),
        "block_count":len(blocks),
        "registered_model_count":2,
        "blocks":blocks,
        "models":models,
        "requested_alias_change_count":sum(b["requested_alias_changed"] for b in blocks),
        "decision":"DESCRIPTIVE_ONLY_NO_MODEL_LOADING_CLAIM",
        "model_loading_time_ms":None,
        "cold_start_time_ms":None,
        "decode_only_tokens_per_second":None,
        "automatic_promotion":False,
        "human_review_required":True,
    }


def _validate_rows(rows: Any, plan: dict[str, Any]) -> None:
    expected=list(_expected_rows(plan))
    if not isinstance(rows,list) or len(rows)!=len(expected):
        raise InvalidExperiment("missing or surplus isolation observations")
    for row,(fields,case) in zip(rows,expected):
        if not isinstance(row,dict) or set(row)!=ROW_FIELDS:
            raise InvalidExperiment("unexpected observation fields")
        if any(type(row[key]) is not type(value) or row[key]!=value for key,value in fields.items()):
            raise InvalidExperiment("role, block, request phase or previous alias inconsistent")
        signature=row["answer_sha256"]
        if type(signature) is not str or len(signature)!=64 or any(c not in "0123456789abcdef" for c in signature):
            raise InvalidExperiment("invalid answer digest")
        if type(row["exact_match"]) is not bool \
           or row["exact_match"] != (signature == _hash_answer(case["expected"])):
            raise InvalidExperiment("fixed-task exact match inconsistent")
        t=row["http_latency_ms"]
        if type(t) not in (int,float) or not isfinite(t) or not .0 < t <= plan["timeout_seconds"]*1000+1000:
            raise InvalidExperiment("invalid full HTTP latency")
        tokens=row["provider_completion_tokens"]
        if tokens is not None and (type(tokens) is not int or not 0<=tokens<=10000):
            raise InvalidExperiment("provider token count invalid")


def run_isolation(plan: Any, *, token: str | None=None, approved: bool=False) -> dict[str, Any]:
    validate_plan(plan)
    if approved is not True:
        raise InvalidExperiment("explicit --approve-local-inference is required")
    _validate_token(token)
    preflight(model=plan["model_a"], port=plan["port"], token=token)
    preflight(model=plan["model_b"], port=plan["port"], token=token)
    records=[]
    for fields,case in _expected_rows(plan):
        body={
            "model":fields["model_alias"], "stream":False, "temperature":0,
            "seed":plan["seed"], "max_tokens":plan["max_tokens"],
            "messages":[{"role":"system","content":SYSTEM},
                        {"role":"user","content":case["prompt"]}],
        }
        start=perf_counter_ns()
        result=request_json("POST","/v1/chat/completions",port=plan["port"],
                            timeout_seconds=plan["timeout_seconds"],
                            token=token,payload=body)
        latency=max(.001,round((perf_counter_ns()-start)/1_000_000,3))
        answer,tokens=_extract_answer(result)
        sig=_hash_answer(answer)
        records.append({
            **fields, "answer_sha256":sig,
            "exact_match":sig==_hash_answer(case["expected"]),
            "http_latency_ms":latency,
            "provider_completion_tokens":tokens,
        })
    receipt={
        "schema":RECEIPT_SCHEMA, "plan":plan, "code_sha256":_source_hash(),
        "recorded_utc":datetime.now(timezone.utc).isoformat(),
        "observations":records, "assessment":_aggregate(records,plan),
        "governance":dict(GUARD),
    }
    receipt["receipt_sha256"]=digest(receipt)
    return receipt


def verify_isolation(receipt: Any) -> dict[str, Any]:
    try:
        if not isinstance(receipt,dict) or set(receipt)!=RECEIPT_FIELDS \
           or receipt["schema"]!=RECEIPT_SCHEMA:
            raise InvalidExperiment("unknown R11 receipt")
        if receipt["receipt_sha256"] != digest({k:v for k,v in receipt.items()
                                                 if k!="receipt_sha256"}):
            raise InvalidExperiment("receipt checksum changed")
        plan=validate_plan(receipt["plan"])
        _timestamp(receipt["recorded_utc"])
        if receipt["code_sha256"]!=_source_hash() or receipt["governance"]!=GUARD:
            raise InvalidExperiment("source or governance changed")
        _validate_rows(receipt["observations"],plan)
        if receipt["assessment"]!=_aggregate(receipt["observations"],plan):
            raise InvalidExperiment("metrics are inconsistent with observations")
        return {
            "passed":True,"arithmetic_and_protocol_consistent":True,
            "historical_inference_authenticated":False,
            "model_load_event_independently_observed":False,
            "true_model_loading_time_ms_measured":False,
            "automatic_promotion":False,
        }
    except (InvalidExperiment,TypeError,ValueError,KeyError,IndexError,
            ZeroDivisionError,OverflowError):
        return {
            "passed":False,"arithmetic_and_protocol_consistent":False,
            "historical_inference_authenticated":False,
            "model_load_event_independently_observed":False,
            "true_model_loading_time_ms_measured":False,
            "automatic_promotion":False,
        }


def browser_summary(receipt: Any) -> dict[str, Any]:
    if not verify_isolation(receipt)["passed"]:
        raise InvalidExperiment("invalid R11 receipt cannot be exported")
    value={
        "schema":SUMMARY_SCHEMA,
        "source_receipt_sha256":receipt["receipt_sha256"],
        "case_set_sha256":receipt["plan"]["fixed_case_sha256"],
        "start_role":receipt["plan"]["first_role"],
        "repeat_requests_per_block":receipt["plan"]["repeat_requests"],
        "assessment":receipt["assessment"], "governance":dict(GUARD),
        "read_only_local_preview":True,"source_authenticated":False,
    }
    value["summary_sha256"]=digest(value)
    return value
