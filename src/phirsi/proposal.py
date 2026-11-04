"""R3 bounded proposal intake and explicitly approved Docker-only code probe.

Untrusted candidate Python is NEVER imported or executed in this host module.
Guest timing is untrusted; host correctness checks compare outputs to a
preinstalled reference. Docker is not a complete security boundary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from random import Random
from secrets import randbits
from typing import Any
import json
import re
import subprocess
import tempfile
import uuid

from .algorithms import reference_count
from .lab import InvalidExperiment, bounded_int, digest

PROPOSAL_SCHEMA = "phirsi.proposal.v1"
PROBE_SCHEMA = "phirsi.probe.v1"
PROPOSAL_KEYS = frozenset({"schema", "proposal_id", "hypothesis", "task", "origin",
                           "source", "source_sha256", "seed", "max_n", "cases", "proposal_sha256"})
IMAGE = re.compile(r"^python:3\.12-slim@sha256:[a-f0-9]{64}$")
PROPOSAL_ID = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
MAX_SOURCE = 20_000
MAX_LOG_BYTES = 1_100_000
TIMEOUT_SECONDS = 20


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _proposal_hash(data: dict[str, Any]) -> str:
    return digest({key: value for key, value in data.items() if key != "proposal_sha256"})


def _limits(seed: int, max_n: int, cases: int) -> list[int]:
    """R3 inputs are bounded and recorded; this is not a secret holdout."""
    rng = Random(seed ^ 0x36A0)
    step = max_n // (cases + 1)
    return [(i + 1) * step + rng.randrange(0, max(1, step // 3)) for i in range(cases)]


def prepare(*, source: str, proposal_id: str, hypothesis: str,
            origin: str = "model", seed: int = 369, max_n: int = 6000,
            cases: int = 4) -> dict[str, Any]:
    packet = {
        "schema": PROPOSAL_SCHEMA, "proposal_id": proposal_id,
        "hypothesis": hypothesis, "task": "prime-count", "origin": origin,
        "source": source, "source_sha256": _sha(source.encode("utf-8")),
        "seed": seed, "max_n": max_n, "cases": cases,
    }
    validate(packet, checksum_required=False)
    packet["proposal_sha256"] = _proposal_hash(packet)
    return packet


def validate(packet: Any, *, checksum_required: bool = True) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise InvalidExperiment("proposal must be a JSON object")
    expected = PROPOSAL_KEYS if checksum_required else PROPOSAL_KEYS - {"proposal_sha256"}
    if set(packet) != expected or packet.get("schema") != PROPOSAL_SCHEMA:
        raise InvalidExperiment("unsupported proposal schema or fields")
    if (type(packet["proposal_id"]) is not str
            or not PROPOSAL_ID.fullmatch(packet["proposal_id"])):
        raise InvalidExperiment("proposal_id must be a safe slug")
    if (type(packet["hypothesis"]) is not str
            or not 8 <= len(packet["hypothesis"].strip()) <= 240
            or packet["hypothesis"] != packet["hypothesis"].strip()):
        raise InvalidExperiment("hypothesis must be 8-240 characters, without outer whitespace")
    if packet["task"] != "prime-count" or packet["origin"] not in ("model", "human", "unknown"):
        raise InvalidExperiment("unsupported task or origin")
    source = packet["source"]
    if type(source) is not str or not 20 <= len(source.encode("utf-8")) <= MAX_SOURCE:
        raise InvalidExperiment("candidate source must be 20-20000 UTF-8 bytes")
    if "\x00" in source or "\r" in source:
        raise InvalidExperiment("source must not contain NUL or CR")
    if packet["source_sha256"] != _sha(source.encode("utf-8")):
        raise InvalidExperiment("source fingerprint mismatch")
    bounded_int(packet["seed"], 0, 2**32 - 1, "seed")
    bounded_int(packet["max_n"], 1000, 10000, "max_n")
    bounded_int(packet["cases"], 2, 6, "cases")
    if checksum_required and packet["proposal_sha256"] != _proposal_hash(packet):
        raise InvalidExperiment("proposal checksum mismatch (not a signature)")
    return packet


def inspect(packet: Any) -> dict[str, Any]:
    valid = validate(packet)
    return {
        "status": "HELD",
        "proposal_id": valid["proposal_id"],
        "source_sha256": valid["source_sha256"],
        "proposal_sha256": valid["proposal_sha256"],
        "execution_performed": False,
        "candidate_author_authenticated": False,
        "review_required": True,
        "note": "Source is untrusted; no code executed during intake.",
    }


def _docker(argv: list[str], *, timeout: int = 8) -> subprocess.CompletedProcess[str]:
    """Trusted controller invokes Docker CLI without shell or untrusted flags."""
    return subprocess.run(["docker", *argv], capture_output=True, text=True,
                          timeout=timeout, check=False)


def _worker_source() -> str:
    return (Path(__file__).resolve().parent / "sandbox_worker.py").read_text(encoding="utf-8")


def _parse_guest(output: str, limits: list[int]) -> dict[str, Any]:
    """Guest controls its stdout. Only host-side reference matching is meaningful."""
    if len(output.encode("utf-8")) > MAX_LOG_BYTES:
        raise InvalidExperiment("guest output exceeds receipt limit")
    marker = "PHIRSI_RESULT="
    lines = [line[len(marker):] for line in output.splitlines() if line.startswith(marker)]
    if len(lines) != 1:
        raise InvalidExperiment("guest must produce exactly one result marker")
    try:
        obj = json.loads(lines[0])
    except (ValueError, TypeError) as exc:
        raise InvalidExperiment("invalid guest JSON") from exc
    if (not isinstance(obj, dict) or set(obj) != {"limits", "results", "durations_ns"}
            or obj["limits"] != limits or not isinstance(obj["results"], list)
            or not isinstance(obj["durations_ns"], list)
            or len(obj["results"]) != len(limits)
            or len(obj["durations_ns"]) != len(limits)):
        raise InvalidExperiment("unexpected guest output shape")
    if any(type(result) is not int for result in obj["results"]):
        raise InvalidExperiment("candidate results must be integers")
    if any(type(t) is not int or t < 0 for t in obj["durations_ns"]):
        raise InvalidExperiment("guest timings invalid")
    return obj


def _docker_create_args(*, name: str, root: Path, image: str) -> list[str]:
    """Fixed limits, with only a pinned image selectable by the operator."""
    return [
        "create", "--name", name, "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "16", "--memory", "256m", "--cpus", "1",
        "--user", "65534:65534", "--ulimit", "nofile=64:64",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=8m",
        "--log-driver", "local", "--log-opt", "max-size=1m",
        "--log-opt", "max-file=1",
        "--mount", f"type=bind,src={root.resolve()},dst=/work,readonly",
        "--workdir", "/work", "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--pull", "never", "--entrypoint", "python", image,
        "-I", "-S", "/work/sandbox_worker.py",
    ]


def execute(packet: Any, *, image: str, approved: bool = False) -> dict[str, Any]:
    """Operator-approved disposable Docker probe. Candidate never runs on host.

    Docker's daemon and kernel remain trusted infrastructure. Never expose
    privileged Docker APIs or host secrets to untrusted candidate code.
    """
    packet = validate(packet)
    if approved is not True:
        raise InvalidExperiment("operator must explicitly authorize Docker experiment")
    if type(image) is not str or not IMAGE.fullmatch(image):
        raise InvalidExperiment("image must be an explicitly chosen python:3.12-slim SHA256 digest")

    # Randomized host challenge reduces hardcoded-answer gaming.
    challenge_seed = packet["seed"] ^ randbits(32)
    limits = _limits(challenge_seed, packet["max_n"], packet["cases"])
    name = f"phirsi-r3-{uuid.uuid4().hex[:16]}"
    timestamp = datetime.now(timezone.utc).isoformat()
    report = {
        "schema": PROBE_SCHEMA,
        "proposal_id": packet["proposal_id"],
        "proposal_sha256": packet["proposal_sha256"],
        "source_sha256": packet["source_sha256"],
        "trusted_worker_sha256": _sha(_worker_source().encode("utf-8")),
        "host_reference_module_sha256": _sha(
            (Path(__file__).resolve().parent / "algorithms.py").read_bytes()),
        "runner_image": image,
        "started_utc": timestamp,
        "challenge_seed": challenge_seed,
        "limits": limits,
        "runtime_policy": {
            "network": "none", "readonly_root": True, "cap_drop": "ALL",
            "no_new_privileges": True, "pids_limit": 16, "memory_mb": 256,
            "cpus": 1, "max_wait_seconds": TIMEOUT_SECONDS,
        },
        "outcome": "failed_closed",
        "host_reference_verified": False,
        "timings_independently_verified": False,
        "container_is_security_proof": False,
        "automatic_promotion": False,
        "human_review_required": True,
    }
    created = False
    try:
        with tempfile.TemporaryDirectory(prefix="phirsi-r3-") as temp:
            root = Path(temp)
            (root / "candidate.py").write_text(packet["source"], encoding="utf-8")
            (root / "sandbox_worker.py").write_text(_worker_source(), encoding="utf-8")
            (root / "inputs.json").write_text(json.dumps(limits), encoding="utf-8")
            # Non-root user must be able to traverse/read the read-only bind mount.
            root.chmod(0o755)
            for file in root.iterdir():
                file.chmod(0o644)
            created_res = _docker(_docker_create_args(name=name, root=root, image=image),
                                  timeout=12)
            if created_res.returncode != 0:
                raise InvalidExperiment("Docker create failed: inspect image/daemon")
            created = True
            start_res = _docker(["start", name], timeout=8)
            if start_res.returncode != 0:
                raise InvalidExperiment("Docker start failed")
            try:
                wait_res = _docker(["wait", name], timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                raise InvalidExperiment("container exceeded bounded execution time") from None
            if wait_res.returncode != 0 or wait_res.stdout.strip() != "0":
                raise InvalidExperiment("candidate exited nonzero or was stopped by limits")
            logs = _docker(["logs", "--tail", "50", name], timeout=8)
            if logs.returncode != 0:
                raise InvalidExperiment("could not read bounded Docker logs")
            result = _parse_guest(logs.stdout, limits)
            expected = [reference_count(n) for n in limits]
            report["guest_counts"] = result["results"]
            report["host_reference_counts"] = expected
            report["guest_reported_durations_ns"] = result["durations_ns"]
            report["host_reference_verified"] = result["results"] == expected
            report["outcome"] = (
                "advisory_correctness_passed" if report["host_reference_verified"]
                else "incorrect_candidate"
            )
    except (InvalidExperiment, OSError, subprocess.TimeoutExpired) as exc:
        report["failure_reason"] = str(exc)
    finally:
        if created:
            # Clean up even if timeout killed the Docker client.
            try:
                _docker(["kill", name], timeout=8)
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                _docker(["rm", "-f", name], timeout=8)
            except (OSError, subprocess.TimeoutExpired):
                pass
    report["probe_sha256"] = digest(report)
    return report
