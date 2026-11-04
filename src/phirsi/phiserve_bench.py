"""R4 local PhiServe inference bench, not a model-quality certification.

Deliberately direct HTTP to 127.0.0.1 only. No URLs supplied by model/users,
no redirects, no credential logging, no model downloads or backend start.
Prompt/response text is not persisted; outputs are scored on narrow fixed tasks.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from math import ceil, isfinite
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from typing import Any
import http.client
import json
import re

from .lab import InvalidExperiment, bounded_int, digest

SCHEMA = "phirsi.phiserve_benchmark.v1"
MODEL_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:/+\-]{0,127}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
MAX_REPLY_BYTES = 96_000
MAX_ANSWER_CHARS = 20_000
CASES = (
    {
        "id": "uppercase",
        "prompt": "Convert the word mint to uppercase. Reply with the converted word only.",
        "expected": "MINT",
    },
    {
        "id": "arithmetic",
        "prompt": "Compute 17 + 25. Reply with digits only.",
        "expected": "42",
    },
    {
        "id": "alphabetical",
        "prompt": "Which comes first alphabetically: plum, apple, banana? Reply with the word only.",
        "expected": "apple",
    },
)
SYSTEM = "Answer only in the exact format requested. Do not add commentary."


def _hash_answer(text: str) -> str:
    return sha256(text.strip().encode("utf-8")).hexdigest()


def _validate_token(token: str | None) -> str | None:
    if token is None or token == "":
        return None
    if (type(token) is not str or len(token) > 2048 or any(ord(c) < 33 or ord(c) > 126 for c in token)):
        raise InvalidExperiment("local bearer token must use visible ASCII; do not log it")
    return token


def _config(model: str, port: int, rounds: int, max_tokens: int,
            timeout_seconds: int, seed: int) -> dict[str, Any]:
    if (type(model) is not str or not MODEL_ID.fullmatch(model)
            or "//" in model or ".." in model):
        raise InvalidExperiment("invalid model alias")
    bounded_int(port, 1, 65535, "port")
    bounded_int(rounds, 1, 3, "rounds")
    bounded_int(max_tokens, 8, 64, "max_tokens")
    bounded_int(timeout_seconds, 5, 60, "timeout_seconds")
    bounded_int(seed, 0, 2**32 - 1, "seed")
    return {
        "model": model, "loopback": "127.0.0.1", "port": port, "rounds": rounds,
        "max_tokens": max_tokens, "timeout_seconds": timeout_seconds,
        "seed": seed, "temperature": 0, "stream": False,
    }


def request_json(method: str, route: str, *, port: int, timeout_seconds: int,
                 token: str | None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Use no proxy, DNS, URL parsing, redirects, cookies or non-loopback hosts."""
    if (method, route) not in {
        ("GET", "/health"), ("GET", "/v1/models"),
        ("POST", "/v1/chat/completions"),
    }:
        raise InvalidExperiment("unregistered local endpoint")
    bounded_int(port, 1, 65535, "port")
    bounded_int(timeout_seconds, 1, 60, "timeout_seconds")
    headers = {"Accept": "application/json", "Connection": "close"}
    credential = _validate_token(token)
    if credential:
        headers["Authorization"] = "Bearer " + credential
    body = None
    if method == "POST":
        if not isinstance(payload, dict):
            raise InvalidExperiment("POST payload must be an object")
        body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(body) > 8192:
            raise InvalidExperiment("request exceeds budget")
        headers["Content-Type"] = "application/json"
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout_seconds)
    try:
        conn.request(method, route, body=body, headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            # No response body logged: error payload might contain sensitive text.
            raise InvalidExperiment(f"local PhiServe returned HTTP {response.status}")
        if not response.getheader("Content-Type", "").lower().startswith("application/json"):
            raise InvalidExperiment("local endpoint did not return JSON")
        raw = response.read(MAX_REPLY_BYTES + 1)
        if len(raw) > MAX_REPLY_BYTES:
            raise InvalidExperiment("local endpoint response exceeds 96KB")
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise InvalidExperiment("PhiServe response must be JSON object")
        return parsed
    except (OSError, http.client.HTTPException, UnicodeError, ValueError) as exc:
        if isinstance(exc, InvalidExperiment):
            raise
        # Avoid exposing response contents, connection strings, or credentials.
        raise InvalidExperiment("local PhiServe request failed or response invalid") from None
    finally:
        conn.close()


def preflight(*, model: str, port: int = 11435, token: str | None = None) -> dict[str, Any]:
    """Reads only /health and /v1/models; does not load model weights."""
    _config(model, port, 1, 16, 10, 369)
    health = request_json("GET", "/health", port=port, timeout_seconds=5, token=token)
    if health.get("status") != "ok":
        raise InvalidExperiment("PhiServe health was not ok")
    catalog = request_json("GET", "/v1/models", port=port, timeout_seconds=5, token=token)
    items = catalog.get("data")
    if not isinstance(items, list) or len(items) > 512:
        raise InvalidExperiment("model catalog malformed")
    aliases = [item.get("id") for item in items if isinstance(item, dict)]
    if model not in aliases:
        raise InvalidExperiment("requested alias is not registered in local PhiServe")
    return {
        "passed": True, "model_registered": True, "health_ok": True,
        "model_loaded_or_active": False,  # readiness alone cannot prove this
        "weights_executed": False,
    }


def _extract_answer(reply: dict[str, Any]) -> tuple[str, int | None]:
    choices = reply.get("choices")
    if not isinstance(choices, list) or len(choices) < 1:
        raise InvalidExperiment("missing completion choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise InvalidExperiment("malformed completion choice")
    message = first.get("message")
    if not isinstance(message, dict):
        raise InvalidExperiment("missing response message")
    content = message.get("content")
    if type(content) is not str or len(content) > MAX_ANSWER_CHARS:
        raise InvalidExperiment("unexpected completion text shape or size")
    usage = reply.get("usage")
    tokens = None
    if usage is not None:
        if not isinstance(usage, dict):
            raise InvalidExperiment("usage must be an object when present")
        reported = usage.get("completion_tokens")
        if reported is not None:
            if type(reported) is not int or not 0 <= reported <= 10000:
                raise InvalidExperiment("invalid provider-reported completion token count")
            tokens = reported
    return content.strip(), tokens


def _assessment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [row["latency_ms"] for row in rows]
    observed = [row["reported_completion_tokens"] for row in rows]
    all_usage = all(value is not None for value in observed)
    return {
        "case_count": len(CASES),
        "request_count": len(rows),
        "exact_match_count": sum(row["exact_match"] for row in rows),
        "exact_match_fraction": round(sum(row["exact_match"] for row in rows) / len(rows), 6),
        "median_end_to_end_latency_ms": round(median(latencies), 3),
        "p95_end_to_end_latency_ms": sorted(latencies)[ceil(0.95 * len(latencies)) - 1],
        "reported_completion_tokens_total": sum(observed) if all_usage else None,
        "estimated_end_to_end_tokens_per_sec": (
            round(sum(observed) / (sum(latencies) / 1000), 3)
            if all_usage else None
        ),
        "gpu_vram_mib": None,
        "gpu_measurement_performed": False,
        "time_to_first_token_measured": False,
        "quality_is_only_fixed_exact_match": True,
        "model_intelligence_gain_claim": False,
        "independent_inference_replication": False,
        "automatic_promotion": False,
        "human_review_required": True,
    }


def run_benchmark(*, model: str, port: int = 11435, rounds: int = 2,
                  max_tokens: int = 32, timeout_seconds: int = 30,
                  seed: int = 369, token: str | None = None,
                  approved: bool = False) -> dict[str, Any]:
    """Operator-authorized calls to an already-running loopback PhiServe only."""
    config = _config(model, port, rounds, max_tokens, timeout_seconds, seed)
    if approved is not True:
        raise InvalidExperiment("local model inference requires explicit approval")
    _validate_token(token)
    preflight(model=model, port=port, token=token)
    rows: list[dict[str, Any]] = []
    for _round in range(rounds):
        for case in CASES:
            body = {
                "model": model,
                "stream": False,
                "temperature": 0,
                "seed": seed,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": case["prompt"]},
                ],
            }
            start = perf_counter_ns()
            answer_json = request_json("POST", "/v1/chat/completions", port=port,
                                       timeout_seconds=timeout_seconds,
                                       token=token, payload=body)
            elapsed_ms = max(0.001, round((perf_counter_ns() - start) / 1_000_000, 3))
            answer, provider_tokens = _extract_answer(answer_json)
            answer_hash = _hash_answer(answer)
            rows.append({
                "case_id": case["id"], "round": _round + 1,
                "response_sha256": answer_hash,
                "exact_match": answer_hash == _hash_answer(case["expected"]),
                "latency_ms": elapsed_ms,
                "reported_completion_tokens": provider_tokens,
            })
    receipt = {
        "schema": SCHEMA,
        "configuration": config,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "code_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "fixed_case_set_sha256": digest(list(CASES)),
        "dataset_class": "public fixed toy tasks; not hidden holdout",
        "model_provenance_authenticated": False,
        "actual_model_weights_verified": False,
        "observations": rows,
        "assessment": _assessment(rows),
        "authorization": {"operator_initiated": True, "no_model_downloads": True},
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_benchmark(receipt: Any) -> dict[str, Any]:
    """Verify self-consistency; cannot authenticate an inference run or timings."""
    try:
        if not isinstance(receipt, dict) or set(receipt) != {
            "schema", "configuration", "recorded_utc", "code_sha256", "fixed_case_set_sha256",
            "dataset_class", "model_provenance_authenticated", "actual_model_weights_verified",
            "observations", "assessment", "authorization", "receipt_sha256",
        }:
            raise InvalidExperiment("receipt schema/shape mismatch")
        if receipt["schema"] != SCHEMA or receipt["receipt_sha256"] != digest({
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        }):
            raise InvalidExperiment("receipt checksum or schema mismatch")
        cfg = receipt["configuration"]
        if cfg != _config(cfg["model"], cfg["port"], cfg["rounds"],
                          cfg["max_tokens"], cfg["timeout_seconds"], cfg["seed"]):
            raise InvalidExperiment("invalid recorded configuration")
        if receipt["code_sha256"] != sha256(Path(__file__).read_bytes()).hexdigest():
            raise InvalidExperiment("local source fingerprint differs")
        if receipt["fixed_case_set_sha256"] != digest(list(CASES)):
            raise InvalidExperiment("fixed case set fingerprint differs")
        if (receipt["dataset_class"] != "public fixed toy tasks; not hidden holdout"
                or receipt["model_provenance_authenticated"] is not False
                or receipt["actual_model_weights_verified"] is not False
                or receipt["authorization"] != {
                    "operator_initiated": True, "no_model_downloads": True,
                }):
            raise InvalidExperiment("misleading evidence or authorization claim")
        if type(receipt["recorded_utc"]) is not str or len(receipt["recorded_utc"]) > 64:
            raise InvalidExperiment("invalid timestamp shape")
        rows = receipt["observations"]
        if not isinstance(rows, list) or len(rows) != len(CASES) * cfg["rounds"]:
            raise InvalidExperiment("invalid number of observations")
        for idx, row in enumerate(rows):
            case = CASES[idx % len(CASES)]
            expected_round = idx // len(CASES) + 1
            if not isinstance(row, dict) or set(row) != {
                "case_id", "round", "response_sha256", "exact_match",
                "latency_ms", "reported_completion_tokens",
            }:
                raise InvalidExperiment("invalid observation shape")
            if row["case_id"] != case["id"] or row["round"] != expected_round:
                raise InvalidExperiment("case order or round does not match protocol")
            if type(row["response_sha256"]) is not str or not HEX64.fullmatch(row["response_sha256"]):
                raise InvalidExperiment("invalid response hash")
            if type(row["exact_match"]) is not bool or row["exact_match"] != (
                row["response_sha256"] == _hash_answer(case["expected"])
            ):
                raise InvalidExperiment("case exact-match claim inconsistent")
            latency = row["latency_ms"]
            if (type(latency) not in (int, float) or not isfinite(latency)
                    or not 0 < latency <= cfg["timeout_seconds"] * 1000 + 1000):
                raise InvalidExperiment("invalid end-to-end latency")
            usage = row["reported_completion_tokens"]
            if usage is not None and (type(usage) is not int or not 0 <= usage <= 10000):
                raise InvalidExperiment("invalid reported token count")
        if _assessment(rows) != receipt["assessment"]:
            raise InvalidExperiment("inconsistent aggregate metrics or evidence limits")
        return {
            "passed": True, "receipt_consistency_checked": True,
            "model_execution_independently_attested": False,
            "latency_replicated": False,
            "automatic_promotion": False,
        }
    except (InvalidExperiment, KeyError, TypeError, ValueError, ZeroDivisionError,
            OverflowError, IndexError):
        return {
            "passed": False, "receipt_consistency_checked": False,
            "model_execution_independently_attested": False,
            "latency_replicated": False, "automatic_promotion": False,
        }
