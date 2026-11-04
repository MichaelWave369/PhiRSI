"""R7 comparative evidence packets for multiple R6 discovery ledgers.

Verification replays R6 and embedded R1 correctness with CURRENT trusted code.
Recorded timings, machine identities, chronology, independence and provenance
remain unauthenticated. ZIP files are inert data, never extracted or executed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from statistics import median
from typing import Any
from zipfile import ZipFile, ZipInfo, ZIP_STORED, BadZipFile
import io
import json
import re
import stat

from .discovery import verify_discovery
from .lab import InvalidExperiment, digest

SCHEMA = "phirsi.replication_packet.v1"
MIN_RUNS = 2
MAX_RUNS = 6
MAX_LEDGER_BYTES = 1_000_000
MAX_PACKET_BYTES = 8_000_000
MAX_MANIFEST_BYTES = 32_000
POLICY = {
    "review_only": True,
    "human_review_required": True,
    "automatic_promotion": False,
    "writes_to_other_repositories": False,
    "external_experiments_launched": False,
    "model_intelligence_improvement_claim": False,
    "statistical_significance_claim": False,
    "independent_hosts_authenticated": False,
    "historical_timings_authenticated": False,
    "cryptographic_signature_present": False,
}
RUN_STATUS = ("OBSERVATIONAL_SUPPORT", "NOT_SUPPORTED",
              "NO_ELIGIBLE_CANDIDATE", "BUDGET_STOPPED")
HEX64 = re.compile(r"^[a-f0-9]{64}$")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _timestamp(value: Any) -> str:
    if type(value) is not str or len(value) > 64:
        raise InvalidExperiment("invalid UTC packet timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidExperiment("invalid packet timestamp") from exc
    if parsed.utcoffset() is None:
        raise InvalidExperiment("timestamp must have timezone")
    return value


def _plan_comparison(plan: dict[str, Any]) -> dict[str, Any]:
    """Hold constant all scientific settings except the run seed and timestamp."""
    excluded = {"seed_development", "seed_evaluation",
                "created_utc", "plan_sha256"}
    return {name: val for name, val in plan.items() if name not in excluded}


def _environment(ledger: dict[str, Any]) -> dict[str, Any] | None:
    events = ledger["events"]
    if not events:
        return None
    source = events[0]["receipt"]["environment"]
    # Environment is a self-report. Never collect hostname, username or IP.
    return {
        "python": source.get("python"),
        "platform": source.get("platform"),
        "machine": source.get("machine"),
        "cpu_count": source.get("cpu_count"),
    }


def _check_sources(ledgers: Any) -> tuple[str, str]:
    if not isinstance(ledgers, list) or not MIN_RUNS <= len(ledgers) <= MAX_RUNS:
        raise InvalidExperiment("requires 2-6 run ledgers")
    fingerprints, seeds, hashes, settings = set(), set(), set(), set()
    for ledger in ledgers:
        if not isinstance(ledger, dict) or not verify_discovery(ledger)["passed"]:
            raise InvalidExperiment("R6 verifier rejected a source ledger")
        raw = _canonical(ledger)
        if len(raw) > MAX_LEDGER_BYTES:
            raise InvalidExperiment("a source R6 ledger exceeds 1 MB")
        name = ledger.get("ledger_sha256")
        if name in hashes:
            raise InvalidExperiment("duplicate R6 ledger")
        hashes.add(name)
        seed = ledger["plan"]["seed_development"]
        if seed in seeds:
            raise InvalidExperiment("run seeds must be distinct, not duplicated")
        seeds.add(seed)
        fingerprints.add(ledger["runner_code_sha256"])
        settings.add(digest(_plan_comparison(ledger["plan"])))
    if len(fingerprints) != 1:
        raise InvalidExperiment("cannot compare runs from different R6 code revisions")
    if len(settings) != 1:
        raise InvalidExperiment("cannot compare differing experiment designs")
    return fingerprints.pop(), settings.pop()


def build_manifest(ledgers: list[dict[str, Any]], *,
                   created_utc: str | None = None) -> dict[str, Any]:
    """Build a limited, review-only report; preserve all negative results."""
    fingerprint, design_hash = _check_sources(ledgers)
    timestamp = _timestamp(created_utc or datetime.now(timezone.utc).isoformat())
    entries = []
    valid_evaluations: list[float] = []
    for index, ledger in enumerate(ledgers, start=1):
        decision = ledger["decision"]
        status = decision["status"]
        if status not in RUN_STATUS:
            raise InvalidExperiment("unrecognized recorded R6 outcome")
        # Only completed evaluations are comparable performance observations.
        eval_event = next((e for e in ledger["events"]
                           if e["phase"] == "evaluation"), None)
        evaluation_ratio = (
            eval_event["receipt"]["summary"]["geomean_observed_speedup"]
            if eval_event is not None and status in
            ("OBSERVATIONAL_SUPPORT", "NOT_SUPPORTED") else None
        )
        if evaluation_ratio is not None:
            if type(evaluation_ratio) not in (int, float) or not isfinite(evaluation_ratio):
                raise InvalidExperiment("invalid observed evaluation speedup")
            valid_evaluations.append(float(evaluation_ratio))
        control = ledger["events"][0] if ledger["events"] else None
        entries.append({
            "id": "run-%02d" % index,
            "archive_path": "runs/run-%02d.json" % index,
            "canonical_source_sha256": _sha(_canonical(ledger)),
            "ledger_sha256": ledger["ledger_sha256"],
            "plan_sha256": ledger["plan"]["plan_sha256"],
            "development_seed": ledger["plan"]["seed_development"],
            "reported_status": status,
            "event_count": len(ledger["events"]),
            "control_observed_ratio": (
                control["receipt"]["summary"]["geomean_observed_speedup"]
                if control is not None else None
            ),
            "evaluation_observed_ratio": evaluation_ratio,
            "environment_reported": _environment(ledger),
        })
    statuses = {name: sum(e["reported_status"] == name for e in entries)
                for name in RUN_STATUS}
    summary = {
        "run_count": len(entries),
        "evaluated_run_count": len(valid_evaluations),
        "support_count": statuses["OBSERVATIONAL_SUPPORT"],
        "not_supported_count": statuses["NOT_SUPPORTED"],
        "no_eligible_count": statuses["NO_ELIGIBLE_CANDIDATE"],
        "budget_stopped_count": statuses["BUDGET_STOPPED"],
        "evaluation_median_observed_ratio": (
            round(median(valid_evaluations), 6) if valid_evaluations else None
        ),
        "evaluation_min_observed_ratio": (
            min(valid_evaluations) if valid_evaluations else None
        ),
        "evaluation_max_observed_ratio": (
            max(valid_evaluations) if valid_evaluations else None
        ),
        "independent_replication_established": False,
        "confidence_interval_calculated": False,
        "quality_of_model_measured": False,
    }
    packet = {
        "schema": SCHEMA,
        "created_utc": timestamp,
        "protocol": "fixed prime-count trial-vs-sieve with R6 correctness replay",
        "r6_runner_code_sha256": fingerprint,
        "comparison_settings_sha256": design_hash,
        "entries": entries,
        "summary": summary,
        "policy": dict(POLICY),
    }
    packet["manifest_sha256"] = digest(packet)
    if len(_canonical(packet)) > MAX_MANIFEST_BYTES:
        raise InvalidExperiment("manifest too large")
    return packet


def _zip_member(name: str, data: bytes) -> tuple[ZipInfo, bytes]:
    info = ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info, data


def create_packet(ledgers: list[dict[str, Any]]) -> bytes:
    """No extraction, plugins, deserialization hooks or arbitrary code loading."""
    manifest = build_manifest(ledgers)
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED, allowZip64=False) as archive:
        info, body = _zip_member("manifest.json", _canonical(manifest))
        archive.writestr(info, body)
        for entry, source in zip(manifest["entries"], ledgers):
            info, body = _zip_member(entry["archive_path"], _canonical(source))
            archive.writestr(info, body)
    binary = output.getvalue()
    if len(binary) > MAX_PACKET_BYTES:
        raise InvalidExperiment("packet exceeds 8 MB")
    return binary


def verify_packet(binary: bytes) -> dict[str, Any]:
    """Re-validate each embedded R6 ledger and compare derived manifest.

    Packet bytes and JSON are untrusted. All archive members are read only,
    never extracted, and limited by size/count/path/type.
    """
    try:
        if type(binary) is not bytes or len(binary) > MAX_PACKET_BYTES:
            raise InvalidExperiment("invalid or oversized packet bytes")
        with ZipFile(io.BytesIO(binary), "r") as archive:
            members = archive.infolist()
            if not MIN_RUNS + 1 <= len(members) <= MAX_RUNS + 1:
                raise InvalidExperiment("invalid archive entry count")
            names = [item.filename for item in members]
            if len(set(names)) != len(names):
                raise InvalidExperiment("duplicate zip entry")
            expected_names = ["manifest.json"] + [
                "runs/run-%02d.json" % i for i in range(1, len(members))
            ]
            if names != expected_names:
                raise InvalidExperiment("unexpected paths or order in ZIP")
            if any(item.compress_type != ZIP_STORED or item.is_dir()
                   or item.file_size > (MAX_MANIFEST_BYTES if index == 0 else MAX_LEDGER_BYTES)
                   or item.compress_size != item.file_size
                   or (item.external_attr >> 16) & 0o170000 not in (0, stat.S_IFREG)
                   for index, item in enumerate(members)):
                raise InvalidExperiment("invalid ZIP member type, compression or size")
            if sum(member.file_size for member in members) > MAX_PACKET_BYTES:
                raise InvalidExperiment("expanded ZIP exceeds allowed budget")
            raw_manifest = archive.read("manifest.json")
            if len(raw_manifest) > MAX_MANIFEST_BYTES:
                raise InvalidExperiment("manifest too large")
            stored = json.loads(raw_manifest)
            if not isinstance(stored, dict):
                raise InvalidExperiment("invalid manifest JSON")
            sources = []
            for index, name in enumerate(expected_names[1:], start=1):
                raw = archive.read(name)
                if len(raw) > MAX_LEDGER_BYTES:
                    raise InvalidExperiment("source ledger too large")
                obj = json.loads(raw)
                sources.append(obj)
            regenerated = build_manifest(sources, created_utc=stored.get("created_utc"))
            if stored != regenerated:
                raise InvalidExperiment("manifest not derived from verified source evidence")
            if raw_manifest != _canonical(stored):
                raise InvalidExperiment("manifest is not canonical JSON")
            if any(archive.read(item["archive_path"]) != _canonical(obj)
                   for item, obj in zip(stored["entries"], sources)):
                raise InvalidExperiment("noncanonical embedded R6 source")
            return {
                "passed": True,
                "manifest": stored,
                "embedded_r6_ledger_verification": True,
                "individual_correctness_replayed": True,
                "independent_hosts_authenticated": False,
                "historical_timings_authenticated": False,
                "model_intelligence_improvement_claim": False,
                "automatic_promotion": False,
            }
    except (InvalidExperiment, BadZipFile, OSError, ValueError, TypeError,
            KeyError, IndexError, OverflowError, ZeroDivisionError, EOFError):
        return {
            "passed": False,
            "manifest": None,
            "embedded_r6_ledger_verification": False,
            "independent_hosts_authenticated": False,
            "historical_timings_authenticated": False,
            "model_intelligence_improvement_claim": False,
            "automatic_promotion": False,
        }
