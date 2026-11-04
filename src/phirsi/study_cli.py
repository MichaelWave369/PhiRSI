"""R2 command-line workflow: plan -> run -> verify.

Run "python -m phirsi.study_cli --help" for usage.
"""
import argparse
import json
import sys
from pathlib import Path
from .lab import InvalidExperiment
from .study import make_plan, run_study, verify_study

MAX_BYTES = 4_000_000

def read_json(path: Path):
    if path.stat().st_size > MAX_BYTES:
        raise InvalidExperiment("JSON input exceeds 4 MB")
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="phirsi-study",
                                     description="R2 precommitted evaluation; no automatic promotion")
    commands = parser.add_subparsers(dest="action", required=True)
    plan = commands.add_parser("plan", help="save an explicit precommitment before running")
    plan.add_argument("--candidate", choices=["trial", "sieve"], default="sieve")
    plan.add_argument("--hypothesis", default="Sieve reduces prime-count runtime")
    plan.add_argument("--seed", type=int, default=369)
    plan.add_argument("--max-n", type=int, default=20000)
    plan.add_argument("--cases", type=int, default=5)
    plan.add_argument("--rounds", type=int, default=5)
    plan.add_argument("--warmups", type=int, default=1)
    plan.add_argument("--min-speedup", type=float, default=1.2)
    plan.add_argument("--min-case-fraction", type=float, default=0.6)
    plan.add_argument("--output", type=Path, required=True)
    study = commands.add_parser("run", help="run both precommitted splits")
    study.add_argument("--plan", type=Path, required=True)
    study.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify", help="replay and check study evidence")
    verify.add_argument("study", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            result = make_plan(
                candidate=args.candidate, hypothesis=args.hypothesis, seed=args.seed,
                max_n=args.max_n, cases=args.cases, rounds=args.rounds,
                warmups=args.warmups, min_speedup=args.min_speedup,
                min_case_fraction=args.min_case_fraction,
            )
            if args.output.exists():
                raise InvalidExperiment("refusing to overwrite existing plan; create a new path")
            write_json(args.output, result)
            print(f"Plan saved at {args.output}; commit this file before experimenting.")
            return 0
        if args.action == "run":
            if args.output.exists():
                raise InvalidExperiment("refusing to overwrite existing evidence")
            result = run_study(read_json(args.plan))
            write_json(args.output, result)
            print(f"Recorded {result['assessment']['status']} in {args.output}")
            print("Caution: historical timing is not independently verified or authenticated.")
            return 0
        result = verify_study(read_json(args.study))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    except (InvalidExperiment, OSError, json.JSONDecodeError) as error:
        print(f"PhiRSI R2 error: {error}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
