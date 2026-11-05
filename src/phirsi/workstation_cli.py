"""R10: entirely offline acceptance plan, dossier verification and summary export."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lab import InvalidExperiment
from .workstation import make_plan, validate_plan, build_dossier, verify_dossier, browser_summary

MAX_R9_RECEIPT_BYTES = 256_000
MAX_PLAN_BYTES = 32_000
MAX_DOSSIER_BYTES = 2_000_000


def _read(path: Path, maximum: int):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise InvalidExperiment("evidence must be a bounded regular local file")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value):
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")


def main(argv=None):
    parser=argparse.ArgumentParser(
        prog="phirsi-workstation",
        description="R10 offline R9 repeat-run acceptance; no inference or promotion",
    )
    commands=parser.add_subparsers(dest="command", required=True)
    p=commands.add_parser("plan", help="predeclare aliases, seeds, bounds and thresholds")
    p.add_argument("--model-a",required=True)
    p.add_argument("--model-b",required=True)
    p.add_argument("--port",type=int,default=11435)
    p.add_argument("--rounds",type=int,default=1)
    p.add_argument("--max-tokens",type=int,default=32)
    p.add_argument("--timeout-seconds",type=int,default=30)
    p.add_argument("--first-seed",type=int,default=369)
    p.add_argument("--run-count",type=int,default=3)
    p.add_argument("--quality-floor",type=float,default=.75)
    p.add_argument("--max-repeat-median-latency-spread",type=float,default=2.0)
    p.add_argument("--output",required=True,type=Path)

    pack=commands.add_parser("pack",help="bind original R9 receipt files to plan in declared order")
    pack.add_argument("--plan",required=True,type=Path)
    pack.add_argument("--receipt",required=True,action="append",type=Path)
    pack.add_argument("--output",required=True,type=Path)

    check=commands.add_parser("verify",help="replay embedded R9 receipts and derived thresholds")
    check.add_argument("dossier",type=Path)

    summary=commands.add_parser("summary",help="write shape-only review JSON for static React lab")
    summary.add_argument("dossier",type=Path)
    summary.add_argument("--output",required=True,type=Path)

    args=parser.parse_args(argv)
    try:
        if args.command=="plan":
            data=make_plan(
                model_a=args.model_a,model_b=args.model_b,
                port=args.port,rounds=args.rounds,max_tokens=args.max_tokens,
                timeout_seconds=args.timeout_seconds,first_seed=args.first_seed,
                run_count=args.run_count,quality_floor=args.quality_floor,
                max_repeat_median_latency_spread=args.max_repeat_median_latency_spread,
            )
            _write_new(args.output,data)
            print(f"Recorded operator acceptance plan: {args.output}")
            return 0
        if args.command=="pack":
            if args.output.exists():
                raise InvalidExperiment("refusing to overwrite existing dossier")
            plan=validate_plan(_read(args.plan,MAX_PLAN_BYTES))
            if len(args.receipt) != plan["run_count"]:
                raise InvalidExperiment("must pass exactly one R9 receipt for every declared run")
            receipts=[_read(path,MAX_R9_RECEIPT_BYTES) for path in args.receipt]
            dossier=build_dossier(plan,receipts)
            _write_new(args.output,dossier)
            print(json.dumps({
                "dossier_saved":str(args.output),
                "status":dossier["assessment"]["status"],
                "source_receipts":len(receipts),
                "independently_verified_hardware":False,
                "automatic_promotion":False,
            },sort_keys=True))
            return 0
        dossier=_read(args.dossier,MAX_DOSSIER_BYTES)
        if args.command=="verify":
            result=verify_dossier(dossier)
            print(json.dumps(result,indent=2,sort_keys=True))
            return 0 if result["passed"] else 2
        if args.output.exists():
            raise InvalidExperiment("refusing to overwrite existing browser summary")
        data=browser_summary(dossier)
        _write_new(args.output,data)
        print(json.dumps({
            "summary_saved":str(args.output),
            "source_attested":False,
            "browser_verification":False,
            "promotion_authorized":False,
        },sort_keys=True))
        return 0
    except (InvalidExperiment,ValueError,TypeError,UnicodeError,OSError) as exc:
        print("PhiRSI R10: "+(str(exc) if isinstance(exc,InvalidExperiment)
                              else "invalid local evidence or file"),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
