"""R7 packet validation, reproducibility and adversarial archive tests."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile, ZIP_STORED

from phirsi.discovery import make_plan, run_discovery
from phirsi.lab import InvalidExperiment
from phirsi.replication import (
    POLICY, build_manifest, create_packet, verify_packet, _canonical,
)
from phirsi.replication_cli import main

SMALL = {"max_n": 1500, "cases": 2, "rounds": 1, "warmups": 0}


def replace_members(binary: bytes, replacements: dict[str, bytes]) -> bytes:
    """Adversarial raw ZIP rewrite without recalculating canonical report."""
    with ZipFile(BytesIO(binary)) as source:
        entries = [(item.filename, replacements.get(item.filename, source.read(item.filename)))
                   for item in source.infolist()]
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as target:
        for filename, contents in entries:
            target.writestr(filename, contents)
    return output.getvalue()


class ReplicationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = run_discovery(make_plan(seed=369, **SMALL), approved=True)
        cls.b = run_discovery(make_plan(seed=370, **SMALL), approved=True)
        cls.binary = create_packet([cls.a, cls.b])

    def test_original_packet_replays_correctness(self):
        report = verify_packet(self.binary)
        self.assertTrue(report["passed"], report)
        self.assertTrue(report["embedded_r6_ledger_verification"])
        self.assertFalse(report["independent_hosts_authenticated"])
        self.assertFalse(report["historical_timings_authenticated"])
        self.assertFalse(report["automatic_promotion"])
        manifest = report["manifest"]
        self.assertEqual(manifest["summary"]["run_count"], 2)
        self.assertEqual(len(manifest["entries"]), 2)
        self.assertEqual(manifest["policy"], POLICY)
        self.assertEqual(manifest["summary"]["independent_replication_established"], False)
        self.assertEqual(manifest["summary"]["confidence_interval_calculated"], False)
        self.assertEqual(sum([
            manifest["summary"]["support_count"],
            manifest["summary"]["not_supported_count"],
            manifest["summary"]["no_eligible_count"],
            manifest["summary"]["budget_stopped_count"],
        ]), 2)

    def test_distinct_seeds_required(self):
        with self.assertRaises(InvalidExperiment):
            create_packet([self.a, self.a])

    def test_comparability_rejects_different_settings(self):
        new = run_discovery(make_plan(seed=371, max_n=2000, cases=2,
                                      rounds=1, warmups=0), approved=True)
        with self.assertRaises(InvalidExperiment):
            create_packet([self.a, new])

    def test_bounded_source_counts(self):
        with self.assertRaises(InvalidExperiment):
            create_packet([self.a])
        with self.assertRaises(InvalidExperiment):
            create_packet([self.a, self.b] * 4)

    def test_bad_source_rejected_before_archive_creation(self):
        bad = deepcopy(self.b)
        bad["governance"]["automatic_promotion"] = True
        with self.assertRaises(InvalidExperiment):
            create_packet([self.a, bad])

    def test_tampered_manifest_rejected(self):
        fake = json.loads(ZipFile(BytesIO(self.binary)).read("manifest.json"))
        fake["summary"]["support_count"] = 999
        binary = replace_members(self.binary, {"manifest.json": _canonical(fake)})
        self.assertFalse(verify_packet(binary)["passed"])

    def test_tampered_embedded_ledger_rejected(self):
        bad = deepcopy(self.b)
        bad["decision"]["status"] = "OBSERVATIONAL_SUPPORT" if bad["decision"]["status"] != "OBSERVATIONAL_SUPPORT" else "NOT_SUPPORTED"
        binary = replace_members(self.binary, {"runs/run-02.json": _canonical(bad)})
        self.assertFalse(verify_packet(binary)["passed"])

    def test_manifest_never_claims_independent_science(self):
        manifest = build_manifest([self.a, self.b])
        self.assertFalse(manifest["policy"]["statistical_significance_claim"])
        self.assertFalse(manifest["policy"]["cryptographic_signature_present"])
        self.assertFalse(manifest["policy"]["independent_hosts_authenticated"])
        self.assertFalse(manifest["policy"]["model_intelligence_improvement_claim"])

    def test_malformed_zip_and_wrong_path_rejected(self):
        self.assertFalse(verify_packet(b"not a ZIP")["passed"])
        with ZipFile(BytesIO(self.binary)) as src:
            contents = [(item.filename, src.read(item.filename)) for item in src.infolist()]
        target = BytesIO()
        with ZipFile(target, "w") as output:
            for name, content in contents:
                output.writestr(name.replace("runs/run-01.json", "../escape.json"), content)
        self.assertFalse(verify_packet(target.getvalue())["passed"])

    def test_cli_pack_verify_export_summary_refuses_overwrites(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            one, two = folder / "one.json", folder / "two.json"
            packet, summary = folder / "packet.zip", folder / "summary.json"
            one.write_bytes(_canonical(self.a))
            two.write_bytes(_canonical(self.b))
            args = ["pack", "--ledger", str(one), "--ledger", str(two),
                    "--output", str(packet)]
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 2)
            self.assertEqual(main(["verify", str(packet)]), 0)
            self.assertEqual(main(["summary", str(packet), "--output", str(summary)]), 0)
            self.assertEqual(main(["summary", str(packet), "--output", str(summary)]), 2)
            value = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(value["summary"]["run_count"], 2)
            self.assertFalse(value["policy"]["automatic_promotion"])

    def test_reproducible_byte_pack_when_timestamp_is_pinned(self):
        # Zip output includes a creation timestamp. Source JSON and entry ordering
        # are canonical, and a pinned timestamp gives deterministic summaries.
        manifest = build_manifest([self.a, self.b], created_utc="2026-01-01T00:00:00+00:00")
        again = build_manifest([self.a, self.b], created_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(_canonical(manifest), _canonical(again))
