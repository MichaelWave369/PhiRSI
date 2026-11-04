"""R4 PhiServe CLI: explicit local inference, private summary-only receipts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .lab import InvalidExperiment
from .phiserve_bench import preflight, run_benchmark, verify_benchmark

MAX_RECEIPT_BYTES = 128_000


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="phirsi-phiserve",
        description="R4 local-only inference experiment; no model download or automatic promotion",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    doctor = sub.add_parser("doctor", help="read local PhiServe health and model catalog")
    doctor.add_argument("--model", required=True)
    doctor.add_argument("--port", type=int, default=11435)

    run = sub.add_parser("run", help="measure existing model with fixed, public toy prompts")
    run.add_argument("--model", required=True)
    run.add_argument("--port", type=int, default=11435)
    run.add_argument("--rounds", type=int, default=2)
    run.add_argument("--max-tokens", type=int, default=32)
    run.add_argument("--timeout-seconds", type=int, default=30)
    run.add_argument("--seed", type=int, default=369)
    run.add_argument("--approve-local-inference", action="store_true")
    run.add_argument("--output", type=Path, required=True)

    verify = sub.add_parser("verify", help="review internal consistency only; no inference")
    verify.add_argument("receipt", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.action == "verify":
            if args.receipt.stat().st_size > MAX_RECEIPT_BYTES:
                raise InvalidExperiment("receipt exceeds 128 KB")
            evidence = json.loads(args.receipt.read_text(encoding="utf-8"))
            status = verify_benchmark(evidence)
            print(json.dumps(status, indent=2, sort_keys=True))
            return 0 if status["passed"] else 2

        # Read a specifically named local secret, never accept a token on the CLI.
        token = os.environ.get("PHIRSI_PHISERVE_TOKEN")
        if args.action == "doctor":
            status = preflight(model=args.model, port=args.port, token=token)
            print(json.dumps(status, indent=2, sort_keys=True))
            return 0

        # Approval and destination checks must precede any network request.
        if args.approve_local_inference is not True:
            raise InvalidExperiment("explicit --approve-local-inference required")
        if args.output.exists():
            raise InvalidExperiment("refusing to overwrite existing evidence")
        result = run_benchmark(
            model=args.model, port=args.port, rounds=args.rounds,
            max_tokens=args.max_tokens, timeout_seconds=args.timeout_seconds,
            seed=args.seed, token=token, approved=True,
        )
        # Exclusive creation prevents accidental replacement.
        with args.output.open("x", encoding="utf-8") as out:
            json.dump(result, out, sort_keys=True, indent=2, allow_nan=False)
            out.write("\n")
        summary = result["assessment"]
        print(json.dumps({
            "saved": str(args.output),
            "exact_match_fraction_on_toy_tasks": summary["exact_match_fraction"],
            "median_end_to_end_latency_ms": summary["median_end_to_end_latency_ms"],
            "provider_reported_tokens_per_sec": summary["estimated_end_to_end_tokens_per_sec"],
            "gpu_vram_measured": False,
            "model_intelligence_gain_claim": False,
            "automatic_promotion": False,
        }, indent=2, sort_keys=True))
        return 0
    except (InvalidExperiment, OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        # No raw network errors or model responses are printed.
        message = str(exc) if isinstance(exc, InvalidExperiment) else "invalid local file or data"
        print(f"PhiRSI R4: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
