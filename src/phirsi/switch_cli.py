"""R11 CLI: predeclared blocked local model requests, offline verification."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .lab import InvalidExperiment
from .switch_isolation import (
    browser_summary, make_plan, run_isolation, validate_plan, verify_isolation,
)

MAX_PLAN_BYTES=16000
MAX_RECEIPT_BYTES=128000


def _read(path: Path, limit: int):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise InvalidExperiment("local JSON must be a bounded regular file")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write("\n")


def main(argv=None):
    parser=argparse.ArgumentParser(
        prog="phirsi-switch-isolation",
        description="R11 controlled local first-vs-repeated PhiServe HTTP requests",
    )
    sub=parser.add_subparsers(dest="command",required=True)
    plan=sub.add_parser("plan",help="predeclare fixed two-round request blocks")
    plan.add_argument("--model-a",required=True)
    plan.add_argument("--model-b",required=True)
    plan.add_argument("--port",type=int,default=11435)
    plan.add_argument("--repeat-requests",type=int,default=2)
    plan.add_argument("--max-tokens",type=int,default=32)
    plan.add_argument("--timeout-seconds",type=int,default=30)
    plan.add_argument("--seed",type=int,default=369)
    plan.add_argument("--first-role",choices=["A","B"],default="A")
    plan.add_argument("--output",required=True,type=Path)

    run=sub.add_parser("run",help="operator-approved 12-16 loopback inference requests")
    run.add_argument("--plan",required=True,type=Path)
    run.add_argument("--approve-local-inference",action="store_true")
    run.add_argument("--output",required=True,type=Path)

    verify=sub.add_parser("verify",help="check receipt and rederive metrics offline")
    verify.add_argument("receipt",type=Path)

    summary=sub.add_parser("summary",help="export local-only shape-preview JSON for React")
    summary.add_argument("receipt",type=Path)
    summary.add_argument("--output",required=True,type=Path)

    args=parser.parse_args(argv)
    try:
        if args.command=="plan":
            item=make_plan(
                model_a=args.model_a,model_b=args.model_b,
                port=args.port,repeat_requests=args.repeat_requests,
                max_tokens=args.max_tokens,timeout_seconds=args.timeout_seconds,
                seed=args.seed,first_role=args.first_role,
            )
            _write(args.output,item)
            print(f"R11 plan recorded: {args.output}. Review before starting inference.")
            return 0
        if args.command=="run":
            if args.approve_local_inference is not True:
                raise InvalidExperiment("--approve-local-inference required")
            if args.output.exists():
                raise InvalidExperiment("refusing to overwrite an existing R11 receipt")
            plan=validate_plan(_read(args.plan,MAX_PLAN_BYTES))
            result=run_isolation(plan,approved=True,
                token=os.environ.get("PHIRSI_PHISERVE_TOKEN"))
            _write(args.output,result)
            print(json.dumps({
                "receipt_saved":str(args.output),
                "total_requests":len(result["observations"]),
                "registered_alias_changes":result["assessment"]["requested_alias_change_count"],
                "real_model_load_time_measured":False,
                "automatic_promotion":False,
            },sort_keys=True))
            return 0
        item=_read(args.receipt,MAX_RECEIPT_BYTES)
        if args.command=="verify":
            result=verify_isolation(item)
            print(json.dumps(result,sort_keys=True,indent=2))
            return 0 if result["passed"] else 2
        if args.output.exists():
            raise InvalidExperiment("refusing to overwrite an existing R11 browser summary")
        data=browser_summary(item)
        _write(args.output,data)
        print(json.dumps({
            "browser_summary_saved":str(args.output),
            "source_authenticated":False,"no_auto_promotion":True,
        },sort_keys=True))
        return 0
    except (InvalidExperiment,ValueError,OSError,UnicodeError,TypeError) as exc:
        print("PhiRSI R11: "+(
            str(exc) if isinstance(exc,InvalidExperiment) else "invalid local file or data"
        ),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
