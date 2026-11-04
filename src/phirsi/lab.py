"""R1 experiment runner and integrity/correctness verifier (not a time replicator)."""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from math import ceil, exp, log
from pathlib import Path
from random import Random
from statistics import median
from time import perf_counter_ns
from typing import Any
import json
import os
import platform
import sys
from .algorithms import ALGORITHMS, reference_count

SCHEMA = "phirsi.receipt.v1"

class InvalidExperiment(ValueError):
    pass

def bounded_int(value: Any, low: int, high: int, label: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise InvalidExperiment(f"{label} must be an integer in [{low}, {high}]")
    return value

def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def code_hash() -> str:
    h = sha256()
    folder = Path(__file__).resolve().parent
    for filename in ("algorithms.py", "lab.py"):
        h.update(filename.encode() + b"\0")
        h.update((folder / filename).read_bytes())
    return h.hexdigest()

def make_limits(seed: int, max_n: int, cases: int) -> list[int]:
    bounded_int(seed, 0, 2**32 - 1, "seed")
    bounded_int(max_n, 1000, 100000, "max_n")
    bounded_int(cases, 2, 10, "cases")
    rng = Random(seed)
    step = max_n // (cases + 1)
    limits = [(i + 1) * step + rng.randrange(max(1, step // 3)) for i in range(cases)]
    if len(set(limits)) != len(limits):
        raise InvalidExperiment("duplicate case input")
    return limits

def stats(samples: list[int], counts: list[int]) -> dict[str, Any]:
    ordered = sorted(samples)
    return {
        "timings_ns": samples, "counts": counts,
        "median_ns": median(samples),
        "p95_ns": ordered[ceil(0.95 * len(ordered)) - 1],
    }

def speedup(rows: list[dict[str, Any]]) -> float:
    return round(exp(sum(log(r["baseline"]["median_ns"] / r["candidate"]["median_ns"])
                         for r in rows) / len(rows)), 6)

def run_experiment(*, candidate: str = "sieve", seed: int = 369, max_n: int = 20000,
                   cases: int = 5, rounds: int = 5, warmups: int = 1) -> dict[str, Any]:
    if candidate not in ALGORITHMS:
        raise InvalidExperiment("unregistered candidate")
    bounded_int(rounds, 1, 10, "rounds")
    bounded_int(warmups, 0, 3, "warmups")
    limits = make_limits(seed, max_n, cases)
    rng = Random(seed ^ 0x369369)
    functions = {"baseline": ALGORITHMS["trial"], "candidate": ALGORITHMS[candidate]}
    observations = []
    for limit in limits:
        expected = reference_count(limit)
        timings = {key: [] for key in functions}
        counts = {key: [] for key in functions}
        for function in functions.values():
            for _ in range(warmups):
                function(limit)
        for _ in range(rounds):
            order = list(functions)
            rng.shuffle(order)
            for name in order:
                start = perf_counter_ns()
                result = functions[name](limit)
                elapsed = max(1, perf_counter_ns() - start)
                timings[name].append(elapsed)
                counts[name].append(result)
        rows = {key: stats(timings[key], counts[key]) for key in functions}
        observations.append({
            "limit": limit, "reference_count": expected, **rows,
            "correctness_passed": all(value == expected for group in counts.values() for value in group),
        })
    experiment = {
        "workload": "prime-count", "baseline": "trial", "candidate": candidate,
        "seed": seed, "max_n": max_n, "cases": cases, "rounds": rounds,
        "warmups": warmups, "limits": limits,
    }
    report = {
        "schema": SCHEMA,
        "experiment": experiment,
        "provenance": {
            "code_sha256": code_hash(),
            "input_sha256": digest({"seed": seed, "limits": limits}),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "machine": platform.machine(), "cpu_count": os.cpu_count()},
        "observations": observations,
        "summary": {
            "correctness_passed": all(r["correctness_passed"] for r in observations),
            "geomean_observed_speedup": speedup(observations),
            "timing_independently_verified": False,
            "model_intelligence_improvement_claim": False,
        },
        "governance": {"automatic_promotion": False, "human_approval_required": True},
    }
    report["receipt_sha256"] = digest(report)
    return report

def verify_receipt(report: Any) -> dict[str, Any]:
    """Check consistency and replay correctness. Cannot authenticate timing or authorship."""
    try:
        if not isinstance(report, dict):
            raise InvalidExperiment("receipt must be an object")
        payload = {k: v for k, v in report.items() if k != "receipt_sha256"}
        if report.get("receipt_sha256") != digest(payload):
            raise InvalidExperiment("receipt checksum mismatch; checksum is not a signature")
        if report["schema"] != SCHEMA:
            raise InvalidExperiment("schema mismatch")
        cfg = report["experiment"]
        if (cfg["workload"] != "prime-count" or cfg["baseline"] != "trial"
                or cfg["candidate"] not in ALGORITHMS):
            raise InvalidExperiment("unrecognized workload or algorithm")
        bounded_int(cfg["rounds"], 1, 10, "rounds")
        bounded_int(cfg["warmups"], 0, 3, "warmups")
        limits = make_limits(cfg["seed"], cfg["max_n"], cfg["cases"])
        if cfg["limits"] != limits:
            raise InvalidExperiment("seeded inputs mismatch")
        if report["provenance"]["code_sha256"] != code_hash():
            raise InvalidExperiment("source fingerprint mismatch")
        if report["provenance"]["input_sha256"] != digest({"seed": cfg["seed"], "limits": limits}):
            raise InvalidExperiment("input fingerprint mismatch")
        rows = report["observations"]
        if not isinstance(rows, list) or len(rows) != len(limits):
            raise InvalidExperiment("observation count mismatch")
        for limit, row in zip(limits, rows):
            expected = reference_count(limit)
            if row["limit"] != limit or row["reference_count"] != expected:
                raise InvalidExperiment("reference mismatch")
            for label, function in (("baseline", ALGORITHMS["trial"]),
                                    ("candidate", ALGORITHMS[cfg["candidate"]])):
                record = row[label]
                samples, counts = record["timings_ns"], record["counts"]
                if (not isinstance(samples, list) or not isinstance(counts, list)
                        or len(samples) != cfg["rounds"] or len(counts) != cfg["rounds"]
                        or any(type(t) is not int or t < 1 for t in samples)
                        or any(type(c) is not int for c in counts)):
                    raise InvalidExperiment("invalid timing/count samples")
                if (record["median_ns"] != median(samples)
                        or record["p95_ns"] != sorted(samples)[ceil(0.95 * len(samples)) - 1]):
                    raise InvalidExperiment("sample statistics mismatch")
                actual = function(limit)
                if any(c != actual or c != expected for c in counts):
                    raise InvalidExperiment("correctness replay failed")
            if row["correctness_passed"] is not True:
                raise InvalidExperiment("case correctness failed")
        summary = report["summary"]
        if (summary["correctness_passed"] is not True
                or summary["geomean_observed_speedup"] != speedup(rows)
                or summary["timing_independently_verified"] is not False
                or summary["model_intelligence_improvement_claim"] is not False):
            raise InvalidExperiment("summary mismatch")
        if report["governance"] != {"automatic_promotion": False, "human_approval_required": True}:
            raise InvalidExperiment("promotion boundary violated")
        return {"passed": True, "correctness_replayed": True, "timings_reproduced": False,
                "origin_authenticated": False}
    except (InvalidExperiment, KeyError, TypeError, ValueError, OverflowError,
            ZeroDivisionError, IndexError) as e:
        return {"passed": False, "reason": str(e), "timings_reproduced": False,
                "origin_authenticated": False}
