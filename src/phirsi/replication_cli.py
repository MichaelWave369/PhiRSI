"""R7 pack, verify and summary-export CLI. No remote submission or extraction."""
import argparse
import json
from pathlib import Path
import sys

from .lab import InvalidExperiment
from .replication import (
    MAX_PACKET_BYTES, MAX_LEDGER_BYTES, _canonical,
    create_packet, verify_packet,
)


def _read_run(path: Path):
    if path.stat().st_size > MAX_LEDGER_BYTES:
        raise InvalidExperiment("source ledger exceeds 1 MB")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_packet(path: Path):
    if path.stat().st_size > MAX_PACKET_BYTES:
        raise InvalidExperiment("packet exceeds 8 MB")
    return path.read_bytes()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="phirsi-replication",
        description="R7 comparison packet: review-only, distinct-seed R6 evidence",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack", help="package 2-6 valid, distinct-seed R6 ledgers")
    pack.add_argument("--ledger", action="append", type=Path, required=True)
    pack.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify", help="replay all embedded R6 evidence without extraction")
    verify.add_argument("packet", type=Path)
    summary = sub.add_parser("summary", help="export a small review-only JSON comparison")
    summary.add_argument("packet", type=Path)
    summary.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "pack":
            if args.output.exists():
                raise InvalidExperiment("refusing to overwrite existing comparison packet")
            evidence = [_read_run(path) for path in args.ledger]
            packet_bytes = create_packet(evidence)
            with args.output.open("xb") as stream:
                stream.write(packet_bytes)
            print(json.dumps({
                "saved": str(args.output), "inputs": len(evidence),
                "signed_or_authenticated": False, "automatic_promotion": False,
            }, sort_keys=True))
            return 0
        verified = verify_packet(_read_packet(args.packet))
        if args.command == "verify":
            print(json.dumps({
                "passed": verified["passed"],
                "embedded_r6_ledger_verification": verified["embedded_r6_ledger_verification"],
                "run_count": verified["manifest"]["summary"]["run_count"]
                             if verified["passed"] else 0,
                "independent_hosts_authenticated": False,
                "historical_timings_authenticated": False,
                "automatic_promotion": False,
            }, sort_keys=True, indent=2))
            return 0 if verified["passed"] else 2
        if not verified["passed"]:
            raise InvalidExperiment("cannot export summary from invalid packet")
        if args.output.exists():
            raise InvalidExperiment("refusing to overwrite existing summary")
        with args.output.open("xb") as stream:
            stream.write(_canonical(verified["manifest"]))
        print(json.dumps({
            "summary_saved": str(args.output),
            "browser_review_only": True,
            "independent_replication_authenticated": False,
        }, sort_keys=True))
        return 0
    except (InvalidExperiment, OSError, UnicodeError, ValueError, TypeError) as error:
        print("PhiRSI R7:",
              str(error) if isinstance(error, InvalidExperiment) else "invalid local input",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
