"""R5 operator CLI: offline governed handoff and optional local read-only check."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from .ecosystem import (
    MAX_HANDOFF_BYTES, MAX_SOURCE_BYTES, SOURCE_KINDS,
    agentora_doctor, make_handoff, read_json, verify_handoff,
)
from .lab import InvalidExperiment


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="phirsi-ecosystem",
        description="R5 review-only evidence handoff; never dispatch or grant authority",
    )
    cmds = parser.add_subparsers(dest="command", required=True)

    prepare = cmds.add_parser("prepare", help="validate existing evidence and export review-only packet")
    prepare.add_argument("--kind", required=True, choices=SOURCE_KINDS)
    prepare.add_argument("--source", required=True, type=Path)
    prepare.add_argument("--output", required=True, type=Path)

    verify = cmds.add_parser("verify", help="recheck handoff against original local evidence")
    verify.add_argument("--kind", required=True, choices=SOURCE_KINDS)
    verify.add_argument("--source", required=True, type=Path)
    verify.add_argument("--handoff", required=True, type=Path)

    doctor = cmds.add_parser("agentora-doctor", help="GET-only health/version check on local Agentora")
    doctor.add_argument("--port", type=int, default=8088)

    args = parser.parse_args(argv)
    try:
        if args.command == "agentora-doctor":
            status = agentora_doctor(port=args.port)
            print(json.dumps(status, indent=2, sort_keys=True))
            return 0
        source = read_json(args.source, limit=MAX_SOURCE_BYTES)
        if args.command == "prepare":
            # No overwrite, no temp file, no external service call.
            handoff = make_handoff(args.kind, source)
            with args.output.open("x", encoding="utf-8") as out:
                json.dump(handoff, out, indent=2, sort_keys=True, allow_nan=False)
                out.write("\n")
            print(json.dumps({
                "saved": str(args.output),
                "disposition": "REVIEW_ONLY",
                "source_kind": args.kind,
                "authority_granted": False,
            }, indent=2, sort_keys=True))
            return 0
        handoff = read_json(args.handoff, limit=MAX_HANDOFF_BYTES)
        result = verify_handoff(handoff, args.kind, source)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    except (InvalidExperiment, OSError, ValueError, TypeError, UnicodeError) as e:
        # No raw evidence content, tokens or detailed network exceptions.
        print(f"PhiRSI R5: {str(e) if isinstance(e, InvalidExperiment) else 'invalid local input'}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
