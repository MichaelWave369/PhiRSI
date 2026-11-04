"""PhiRSI R5: evidence-derived, zero-authority ecosystem handoff.

Imports R1/R2/R3/R4 validators instead of trusting labels supplied by a file.
A handoff never confers execution or governance authority. Agentora health
preflight is GET-only on a fixed loopback host. PhiOS and PhiMadaPrime
contracts are *offline, proposal-only* until their own adapters exist.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import http.client
import json
from pathlib import Path
from typing import Any

from .lab import InvalidExperiment, digest, verify_receipt
from .study import verify_study
from .proposal import inspect as inspect_proposal
from .phiserve_bench import verify_benchmark

SCHEMA = "phirsi.ecosystem_handoff.v1"
SOURCE_KINDS = ("r1", "r2", "r3", "r4")
MAX_SOURCE_BYTES = 2_000_000
MAX_HANDOFF_BYTES = 20_000
NO_AUTHORITY = {
    "authorized_actions": [],
    "execution_authorized": False,
    "merge_authorized": False,
    "deployment_authorized": False,
    "model_weight_change_authorized": False,
    "writeback_authorized": False,
    "human_review_required": True,
}
REVIEW_TARGETS = {
    "agentora": {"mode": "offline_review_only", "dispatch_enabled": False},
    "phios": {"mode": "offline_policy_review_only", "authority_granted": False},
    "phimadaprime": {"mode": "local_import_candidate_only", "public_publishing_allowed": False},
    "compaware": {"mode": "offline_adversarial_review_candidate", "scientific_claim_verified": False},
}


def _check_kind(kind: str) -> str:
    if type(kind) is not str or kind not in SOURCE_KINDS:
        raise InvalidExperiment("unsupported evidence kind; choose r1, r2, r3 or r4")
    return kind


def read_json(path: Path, *, limit: int = MAX_SOURCE_BYTES) -> Any:
    if type(limit) is not int or limit < 1:
        raise InvalidExperiment("invalid file-size limit")
    if path.stat().st_size > limit:
        raise InvalidExperiment("evidence file exceeds allowed size")
    return json.loads(path.read_text(encoding="utf-8"))


def _validated_summary(kind: str, source: Any) -> dict[str, Any]:
    _check_kind(kind)
    if not isinstance(source, dict):
        raise InvalidExperiment("evidence must be a JSON object")
    if kind == "r1":
        result = verify_receipt(source)
        if result["passed"] is not True:
            raise InvalidExperiment("R1 receipt failed existing correctness verification")
        summary = source["summary"]
        return {
            "status": "CORRECTNESS_REPLAYED",
            "workload": "prime-count",
            "observed_speedup": summary["geomean_observed_speedup"],
            "timings_independently_verified": False,
        }
    if kind == "r2":
        result = verify_study(source)
        if result["passed"] is not True:
            raise InvalidExperiment("R2 study failed existing study verification")
        assessment = source["assessment"]
        return {
            "status": str(assessment["status"]),
            "workload": "prime-count",
            "evaluation_observed_speedup": assessment["evaluation_observed_geomean_speedup"],
            "timings_independently_verified": False,
        }
    if kind == "r3":
        result = inspect_proposal(source)
        if result["status"] != "HELD" or result["execution_performed"] is not False:
            raise InvalidExperiment("R3 proposal was not held")
        return {
            "status": "HELD",
            "workload": "prime-count-proposal",
            "source_sha256": result["source_sha256"],
            "candidate_execution_verified": False,
        }
    result = verify_benchmark(source)
    if result["passed"] is not True:
        raise InvalidExperiment("R4 benchmark failed existing receipt verification")
    assessment = source["assessment"]
    return {
        "status": "OBSERVATION_CONSISTENT",
        "workload": "phiserve-fixed-toy-prompts",
        "exact_match_fraction": assessment["exact_match_fraction"],
        "median_end_to_end_latency_ms": assessment["median_end_to_end_latency_ms"],
        "reported_end_to_end_tokens_per_sec": assessment["estimated_end_to_end_tokens_per_sec"],
        "model_identity_authenticated": False,
        "timings_independently_verified": False,
    }


def make_handoff(kind: str, source: Any) -> dict[str, Any]:
    """Review-only local artifact; source is validated, not copied into output."""
    kind = _check_kind(kind)
    summary = _validated_summary(kind, source)
    # Never serialize raw prompts, responses, user-provided source, or tokens here.
    # The full source evidence remains on the operator's machine.
    result = {
        "schema": SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_kind": kind,
        "source_sha256": digest(source),
        "source_checks": {
            "rung_validator_passed": True,
            "independently_replicated": False,
            "origin_authenticated": False,
            "source_included_in_handoff": False,
        },
        "summary": summary,
        "policy": dict(NO_AUTHORITY),
        "targets": {key: dict(value) for key, value in REVIEW_TARGETS.items()},
        "disposition": "REVIEW_ONLY",
        "handoff_is_receipt_of_external_execution": False,
    }
    result["handoff_sha256"] = digest(result)
    if len(json.dumps(result, sort_keys=True).encode("utf-8")) > MAX_HANDOFF_BYTES:
        raise InvalidExperiment("handoff exceeds allowed size")
    return result


def verify_handoff(handoff: Any, kind: str, source: Any) -> dict[str, Any]:
    """Offline source binding, summary recomputation, and fail-closed policy."""
    try:
        _check_kind(kind)
        if not isinstance(handoff, dict) or set(handoff) != {
            "schema", "created_utc", "source_kind", "source_sha256",
            "source_checks", "summary", "policy", "targets", "disposition",
            "handoff_is_receipt_of_external_execution", "handoff_sha256",
        }:
            raise InvalidExperiment("handoff shape invalid")
        if handoff["schema"] != SCHEMA or handoff["source_kind"] != kind:
            raise InvalidExperiment("handoff schema or rung mismatch")
        if handoff["handoff_sha256"] != digest({
            key: value for key, value in handoff.items() if key != "handoff_sha256"
        }):
            raise InvalidExperiment("handoff checksum mismatch")
        if handoff["source_sha256"] != digest(source):
            raise InvalidExperiment("source file does not match handoff")
        if type(handoff["created_utc"]) is not str or len(handoff["created_utc"]) > 64:
            raise InvalidExperiment("invalid timestamp")
        when = datetime.fromisoformat(handoff["created_utc"])
        if when.utcoffset() is None:
            raise InvalidExperiment("timestamp lacks timezone")
        if handoff["source_checks"] != {
            "rung_validator_passed": True,
            "independently_replicated": False,
            "origin_authenticated": False,
            "source_included_in_handoff": False,
        }:
            raise InvalidExperiment("invalid source provenance claim")
        if handoff["policy"] != NO_AUTHORITY or handoff["targets"] != REVIEW_TARGETS:
            raise InvalidExperiment("handoff attempted to grant authority")
        if (handoff["disposition"] != "REVIEW_ONLY"
                or handoff["handoff_is_receipt_of_external_execution"] is not False):
            raise InvalidExperiment("invalid disposition")
        if handoff["summary"] != _validated_summary(kind, source):
            raise InvalidExperiment("summary does not match verified evidence")
        return {
            "passed": True, "disposition": "REVIEW_ONLY",
            "rung_validator_passed": True, "source_binding_checked": True,
            "origin_authenticated": False, "external_adapters_called": False,
            "permission_granted": False,
        }
    except (InvalidExperiment, ValueError, KeyError, TypeError, OverflowError,
            ZeroDivisionError, IndexError):
        return {
            "passed": False, "disposition": "REJECTED",
            "origin_authenticated": False, "external_adapters_called": False,
            "permission_granted": False,
        }


def _get_agentora(route: str, port: int, timeout_seconds: int) -> dict[str, Any]:
    """Actual Agentora GET contract, fixed loopback; never any write or mission launch."""
    if route not in ("/api/health", "/api/system/version"):
        raise InvalidExperiment("unapproved Agentora route")
    if type(port) is not int or not 1 <= port <= 65535:
        raise InvalidExperiment("invalid local port")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 10:
        raise InvalidExperiment("invalid local timeout")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout_seconds)
    try:
        conn.request("GET", route, headers={"Accept": "application/json", "Connection": "close"})
        response = conn.getresponse()
        if response.status != 200:
            raise InvalidExperiment("Agentora did not return HTTP 200")
        if not response.getheader("Content-Type", "").lower().startswith("application/json"):
            raise InvalidExperiment("Agentora response was not JSON")
        raw = response.read(8193)
        if len(raw) > 8192:
            raise InvalidExperiment("Agentora response too large")
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise InvalidExperiment("Agentora response must be an object")
        return parsed
    except (OSError, http.client.HTTPException, ValueError, UnicodeError) as e:
        if isinstance(e, InvalidExperiment):
            raise
        raise InvalidExperiment("Agentora local preflight failed") from None
    finally:
        conn.close()


def agentora_doctor(port: int = 8088) -> dict[str, Any]:
    """Real read-only local integration; no credentials, mission actions, or POST."""
    health = _get_agentora("/api/health", port, 3)
    version = _get_agentora("/api/system/version", port, 3)
    if health.get("ok") is not True or health.get("service") != "agentora":
        raise InvalidExperiment("unexpected Agentora health identity")
    if version.get("ok") is not True:
        raise InvalidExperiment("unexpected Agentora version response")
    identity = version.get("service")
    if not isinstance(identity, str) or not identity.strip():
        raise InvalidExperiment("invalid Agentora service identity")
    return {
        "service": "agentora", "read_only_local_preflight": True,
        "version_reported": str(version.get("version", "unknown"))[:64],
        "health_ok": True, "mission_dispatched": False,
        "phios_authority_assumed": False,
        "agentora_compatible_for_research_missions": "UNVERIFIED",
    }
