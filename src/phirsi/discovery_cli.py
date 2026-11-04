"""R6 CLI for explicit, bounded search plans and offline ledger replay."""
import argparse
import json
from pathlib import Path
import sys

from .discovery import make_plan, run_discovery, verify_discovery, validate_plan
from .lab import InvalidExperiment

MAX_INPUT_BYTES = 2_000_000


def _read(path: Path):
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise InvalidExperiment("input JSON exceeds 2 MB")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, data):
    # Exclusive creation, never clobber a plan or history.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="phirsi-discovery", description="R6 bounded registered-algorithm discovery"
    )
    cmd = parser.add_subparsers(dest="command", required=True)
    draft = cmd.add_parser("plan", help="freeze candidates, criteria and budgets before running")
    draft.add_argument("--hypothesis", default="Sieve can improve measured prime counting over trial division")
    draft.add_argument("--seed", type=int, default=369)
    draft.add_argument("--max-n", type=int, default=5000)
    draft.add_argument("--cases", type=int, default=3)
    draft.add_argument("--rounds", type=int, default=2)
    draft.add_argument("--warmups", type=int, default=0)
    draft.add_argument("--min-dev-speedup", type=float, default=1.05)
    draft.add_argument("--min-eval-speedup", type=float, default=1.2)
    draft.add_argument("--min-eval-case-fraction", type=float, default=0.6)
    draft.add_argument("--max-wall-seconds", type=int, default=30)
    draft.add_argument("--output", required=True, type=Path)

    execute = cmd.add_parser("run", help="execute registered experiments with explicit approval")
    execute.add_argument("--plan", required=True, type=Path)
    execute.add_argument("--approve-bounded-search", action="store_true")
    execute.add_argument("--output", required=True, type=Path)

    review = cmd.add_parser("verify", help="check original ledger and replay known R1 correctness")
    review.add_argument("ledger", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            candidate = make_plan(
                hypothesis=args.hypothesis, seed=args.seed, max_n=args.max_n,
                cases=args.cases, rounds=args.rounds, warmups=args.warmups,
                min_dev_speedup=args.min_dev_speedup,
                min_eval_speedup=args.min_eval_speedup,
                min_eval_case_fraction=args.min_eval_case_fraction,
                max_wall_seconds=args.max_wall_seconds,
            )
            _write_new(args.output, candidate)
            print(f"Plan created: {args.output} (commit it before interpreting measurements)")
            return 0
        if args.command == "run":
            if args.approve_bounded_search is not True:
                raise InvalidExperiment("--approve-bounded-search required")
            if args.output.exists():
                raise InvalidExperiment("refusing to overwrite existing discovery ledger")
            plan = validate_plan(_read(args.plan))
            result = run_discovery(plan, approved=True)
            _write_new(args.output, result)
            print(json.dumps({
                "saved": str(args.output), "decision": result["decision"]["status"],
                "candidate": result["decision"]["selected_candidate"],
                "events": len(result["events"]), "automatic_promotion": False,
            }, sort_keys=True))
            return 0
        result = verify_discovery(_read(args.ledger))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    except (InvalidExperiment, OSError, UnicodeError, ValueError, TypeError) as error:
        message = str(error) if isinstance(error, InvalidExperiment) else "invalid local input"
        print("PhiRSI R6:", message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
