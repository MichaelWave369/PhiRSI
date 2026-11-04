"""R9 CLI: reviewed local A/B benchmark and offline hardware-evidence import."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

from .field_lab import (
    make_plan, validate_plan, run_field, verify_field, browser_summary,
)
from .lab import InvalidExperiment

MAX_RECEIPT = 256_000
MAX_FIELD = 1_000_000


def _read(path: Path, limit: int):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise InvalidExperiment("invalid, linked, or oversized evidence input")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data):
    with path.open("x", encoding="utf-8") as out:
        json.dump(data, out, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")


def main(argv=None):
    parser=argparse.ArgumentParser(
        prog="phirsi-field", description="R9 fixed public task validation + operator-supplied GGUF/field evidence",
    )
    commands=parser.add_subparsers(dest="action",required=True)
    p=commands.add_parser("plan",help="save bounded experiment protocol")
    p.add_argument("--model-a",required=True)
    p.add_argument("--model-b",required=True)
    p.add_argument("--port",type=int,default=11435)
    p.add_argument("--rounds",type=int,default=1)
    p.add_argument("--max-tokens",type=int,default=32)
    p.add_argument("--timeout-seconds",type=int,default=30)
    p.add_argument("--seed",type=int,default=369)
    p.add_argument("--output",type=Path,required=True)

    run=commands.add_parser("run",help="execute 12 public toy tasks x 2 aliases locally")
    run.add_argument("--plan",type=Path,required=True)
    run.add_argument("--approve-local-inference",action="store_true")
    run.add_argument("--model-a-gguf",type=Path)
    run.add_argument("--model-b-gguf",type=Path)
    run.add_argument("--field-a-receipt",type=Path)
    run.add_argument("--field-b-receipt",type=Path)
    run.add_argument("--output",type=Path,required=True)

    v=commands.add_parser("verify",help="offline arithmetic and source consistency only")
    v.add_argument("receipt",type=Path)
    summary=commands.add_parser("summary",help="export local-only read-only JSON for React")
    summary.add_argument("receipt",type=Path)
    summary.add_argument("--output",type=Path,required=True)

    args=parser.parse_args(argv)
    try:
        if args.action=="plan":
            _write(args.output,make_plan(
                model_a=args.model_a,model_b=args.model_b,port=args.port,
                rounds=args.rounds,max_tokens=args.max_tokens,
                timeout_seconds=args.timeout_seconds,seed=args.seed,
            ))
            print(f"Recorded predeclared R9 plan at {args.output}")
            return 0
        if args.action=="run":
            if not args.approve_local_inference:
                raise InvalidExperiment("explicit --approve-local-inference required")
            if args.output.exists():
                raise InvalidExperiment("refusing to overwrite previous experiment evidence")
            plan=validate_plan(_read(args.plan,16_000))
            paths={}
            separate={}
            for role,attribute in (("A","model_a_gguf"),("B","model_b_gguf")):
                if getattr(args,attribute) is not None:
                    paths[role]=getattr(args,attribute)
            for role,attribute in (("A","field_a_receipt"),("B","field_b_receipt")):
                if getattr(args,attribute) is not None:
                    separate[role]=_read(getattr(args,attribute),MAX_FIELD)
            receipt=run_field(plan,approved=True,
                              token=os.environ.get("PHIRSI_PHISERVE_TOKEN"),
                              gguf_paths=paths,phiserve_fields=separate)
            _write(args.output,receipt)
            print(json.dumps({"saved":str(args.output),
                "requests":len(receipt["observations"]),"review_only":True,
                "weight_binding_verified":False,"auto_promotion":False},sort_keys=True))
            return 0
        receipt=_read(args.receipt,MAX_RECEIPT)
        if args.action=="verify":
            report=verify_field(receipt)
            print(json.dumps(report,indent=2,sort_keys=True))
            return 0 if report["passed"] else 2
        if args.output.exists():
            raise InvalidExperiment("refusing to overwrite prior R9 summary")
        result=browser_summary(receipt)
        _write(args.output,result)
        print(json.dumps({"saved":str(args.output),
            "source_replayed_in_browser":False,
            "independent_hardware_proof":False},sort_keys=True))
        return 0
    except (InvalidExperiment,ValueError,OSError,UnicodeError,TypeError) as exc:
        msg=str(exc) if isinstance(exc,InvalidExperiment) else "invalid local file or data"
        print(f"PhiRSI R9: {msg}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
