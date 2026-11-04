"""R3 CLI: inert review by default, explicit Docker-only evaluation on approval."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from .lab import InvalidExperiment
from .proposal import execute, inspect, prepare

MAX_JSON_BYTES = 90000


def _read_json(path: Path):
    if path.stat().st_size > MAX_JSON_BYTES:
        raise InvalidExperiment("proposal exceeds 90 KB")
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, obj):
    if path.exists():
        raise InvalidExperiment(f"refusing to overwrite existing file: {path}")
    path.write_text(json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="phirsi-proposal", description="R3 safe intake and approved container probe")
    commands = parser.add_subparsers(dest="command", required=True)
    draft = commands.add_parser("draft", help="store source proposal without execution")
    draft.add_argument("--source", required=True, type=Path)
    draft.add_argument("--id", required=True)
    draft.add_argument("--hypothesis", required=True)
    draft.add_argument("--origin", choices=["model", "human", "unknown"], default="model")
    draft.add_argument("--seed", type=int, default=369)
    draft.add_argument("--max-n", type=int, default=6000)
    draft.add_argument("--cases", type=int, default=4)
    draft.add_argument("--output", required=True, type=Path)
    review = commands.add_parser("review", help="structural inspection: never executes candidate")
    review.add_argument("--proposal", required=True, type=Path)
    probe = commands.add_parser("probe", help="explicit, bounded Docker execution")
    probe.add_argument("--proposal", required=True, type=Path)
    probe.add_argument("--image", required=True,
                       help="pinned python:3.12-slim@sha256:<digest> already installed")
    probe.add_argument("--approve-isolated-run", action="store_true",
                       help="explicitly authorize local Docker execution")
    probe.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "draft":
            if args.source.stat().st_size > 20000:
                raise InvalidExperiment("source exceeds 20 KB")
            source = args.source.read_text(encoding="utf-8")
            packet = prepare(source=source, proposal_id=args.id, hypothesis=args.hypothesis,
                             origin=args.origin, seed=args.seed,
                             max_n=args.max_n, cases=args.cases)
            _save(args.output, packet)
            print("Saved inert proposal:", args.output)
            return 0
        if args.command == "review":
            print(json.dumps(inspect(_read_json(args.proposal)), indent=2, sort_keys=True))
            return 0
        if args.output.exists():
            raise InvalidExperiment("refusing to overwrite existing probe evidence")
        outcome = execute(_read_json(args.proposal), image=args.image,
                          approved=args.approve_isolated_run)
        _save(args.output, outcome)
        print(json.dumps({"outcome": outcome["outcome"], "receipt": str(args.output)},
                         sort_keys=True))
        return 0 if outcome["outcome"] == "advisory_correctness_passed" else 2
    except (InvalidExperiment, OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"PhiRSI R3 error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
