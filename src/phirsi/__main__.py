"""CLI for registered experiments and receipt replay."""
import argparse
import json
import sys
from pathlib import Path
from .algorithms import ALGORITHMS
from .lab import InvalidExperiment, run_experiment, verify_receipt

def main(argv=None):
    parser = argparse.ArgumentParser(prog="phirsi", description="ΦRSI bounded experiments")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--candidate", choices=sorted(ALGORITHMS), default="sieve")
    run.add_argument("--seed", type=int, default=369)
    run.add_argument("--max-n", type=int, default=20000)
    run.add_argument("--cases", type=int, default=5)
    run.add_argument("--rounds", type=int, default=5)
    run.add_argument("--warmups", type=int, default=1)
    run.add_argument("--output", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            report = run_experiment(candidate=args.candidate, seed=args.seed,
                                    max_n=args.max_n, cases=args.cases,
                                    rounds=args.rounds, warmups=args.warmups)
            content = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
            if args.output:
                args.output.write_text(content, encoding="utf-8")
                print("Wrote:", args.output)
            else:
                print(content, end="")
            return 0 if report["summary"]["correctness_passed"] else 2
        if args.receipt.stat().st_size > 2_000_000:
            raise InvalidExperiment("receipt exceeds 2 MB")
        outcome = verify_receipt(json.loads(args.receipt.read_text(encoding="utf-8")))
        print(json.dumps(outcome, indent=2, sort_keys=True))
        return 0 if outcome["passed"] else 2
    except (InvalidExperiment, OSError, json.JSONDecodeError) as e:
        print("PhiRSI error:", e, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
