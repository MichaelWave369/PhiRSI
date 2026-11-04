"""PhiRSI R8: local PhiServe A/B plan, controlled run, replay, browser summary."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .lab import InvalidExperiment
from .model_pair import make_plan, run_pair, summary_for_browser, validate_plan, verify_pair

MAX_RECEIPT_BYTES = 128_000
MAX_PLAN_BYTES = 16_000


def _read(path: Path, limit: int):
    if path.stat().st_size > limit:
        raise InvalidExperiment("local file exceeds permitted size")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value):
    # Exclusive creation: never silently overwrite an experiment or research receipt.
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="phirsi-model-pair",
        description="R8 bounded model A/B, loopback-only PhiServe, no autonomous promotion",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="record two registered model aliases and paired test budget")
    plan.add_argument("--model-a", required=True)
    plan.add_argument("--model-b", required=True)
    plan.add_argument("--port", type=int, default=11435)
    plan.add_argument("--rounds", type=int, default=1)
    plan.add_argument("--max-tokens", type=int, default=32)
    plan.add_argument("--timeout-seconds", type=int, default=30)
    plan.add_argument("--seed", type=int, default=369)
    plan.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", help="run approved fixed-task inference on local PhiServe only")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--approve-local-inference", action="store_true")
    run.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("verify", help="check receipt arithmetic and protocol, no network")
    check.add_argument("receipt", type=Path)
    view = commands.add_parser("summary", help="export no-secret, review-only React viewer JSON")
    view.add_argument("receipt", type=Path)
    view.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            item = make_plan(
                model_a=args.model_a, model_b=args.model_b,
                port=args.port, rounds=args.rounds,
                max_tokens=args.max_tokens,
                timeout_seconds=args.timeout_seconds, seed=args.seed,
            )
            _write_new(args.output, item)
            print(f"Plan recorded at {args.output}; review/commit before looking at results.")
            return 0
        if args.command == "run":
            if args.approve_local_inference is not True:
                raise InvalidExperiment("explicit --approve-local-inference required")
            if args.output.exists():
                raise InvalidExperiment("refusing to overwrite an existing receipt")
            item = validate_plan(_read(args.plan, MAX_PLAN_BYTES))
            # Token is not accepted as a CLI argument, printed or written to receipt.
            result = run_pair(
                item, approved=True, token=os.environ.get("PHIRSI_PHISERVE_TOKEN"),
            )
            _write_new(args.output, result)
            print(json.dumps({
                "receipt_saved": str(args.output),
                "paired_task_count": result["assessment"]["paired_task_count"],
                "status": result["assessment"]["decision"],
                "automatic_promotion": False,
            }, sort_keys=True))
            return 0
        receipt = _read(args.receipt, MAX_RECEIPT_BYTES)
        if args.command == "verify":
            result = verify_pair(receipt)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["passed"] else 2
        if args.output.exists():
            raise InvalidExperiment("refusing to overwrite an existing model summary")
        summary = summary_for_browser(receipt)
        _write_new(args.output, summary)
        print(json.dumps({
            "summary_saved": str(args.output),
            "browser_only_shape_inspection": True,
            "authenticated_historical_measurements": False,
        }, sort_keys=True))
        return 0
    except (InvalidExperiment, OSError, UnicodeError, ValueError, TypeError) as error:
        # Do not echo model responses, raw network exceptions or bearer tokens.
        message = str(error) if isinstance(error, InvalidExperiment) else "invalid local input"
        print("PhiRSI R8:", message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
