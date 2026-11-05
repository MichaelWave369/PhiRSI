"""R10 offline workstation acceptance against fake R9 inputs, no real models."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from phirsi.field_lab import CASES, make_plan as make_r9, run_field, verify_field
from phirsi.lab import InvalidExperiment, digest
from phirsi.workstation import (
    GOVERNANCE, build_dossier, browser_summary,
    make_plan, validate_plan, verify_dossier,
)
from phirsi.workstation_cli import main


def fake_local_reply(method, path, **kwargs):
    if path == "/health":
        return {"status": "ok"}
    if path == "/v1/models":
        return {"data": [{"id": "fixture-a"}, {"id": "fixture-b"}]}
    payload=kwargs["payload"]
    prompt=payload["messages"][-1]["content"]
    case=next(x for x in CASES if x["prompt"]==prompt)
    answer=case["expected"]
    if payload["model"] == "fixture-b" and case["id"]=="multiply":
        answer="NOT_THE_EXPECTED_VALUE"
    return {"choices": [{"message": {"content": answer}}],
            "usage": {"completion_tokens": 4}}


def rehash(item, field):
    item[field]=digest({k:v for k,v in item.items() if k!=field})


class WorkstationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config={
            "model_a":"fixture-a", "model_b":"fixture-b",
            "first_seed":369,"run_count":3,
            "rounds":1,"max_tokens":16,"timeout_seconds":5,
        }
        cls.plan=make_plan(**cls.config)
        with patch("phirsi.field_lab.request_json",side_effect=fake_local_reply), \
             patch("phirsi.field_lab.preflight",return_value={"passed":True}):
            cls.receipts=[
                run_field(make_r9(
                    model_a="fixture-a",model_b="fixture-b",
                    rounds=1,max_tokens=16,timeout_seconds=5,seed=369+i,
                ), approved=True)
                for i in range(3)
            ]
        cls.dossier=build_dossier(cls.plan,cls.receipts)

    def test_roundtrip_and_review_only_status(self):
        report=verify_dossier(self.dossier)
        self.assertTrue(report["passed"],report)
        self.assertEqual(report["status"],self.dossier["assessment"]["status"])
        self.assertFalse(report["historical_timings_authenticated"])
        self.assertFalse(report["real_hardware_verified"])
        self.assertFalse(report["automatic_promotion"])
        self.assertEqual(self.dossier["governance"],GOVERNANCE)
        self.assertEqual(len(self.dossier["original_r9_receipts"]),3)

    def test_original_receipts_preserved_with_distinct_seeds(self):
        assessment=self.dossier["assessment"]
        self.assertEqual(
            [item["seed"] for item in assessment["entries"]],[369,370,371])
        self.assertEqual(
            [item["operator_run_label"] for item in assessment["entries"]],
            ["initial","repeat","repeat"])
        self.assertTrue(assessment["run_order_labels_are_operator_declared_not_cold_warm_attestations"])
        self.assertTrue(all(verify_field(r)["passed"] for r in self.dossier["original_r9_receipts"]))
        self.assertFalse(assessment["qualified_as_independently_verified_workstation"])
        self.assertFalse(assessment["automatic_model_selection"])

    def test_fixed_public_quality_floor_and_repeat_stability(self):
        assessment=self.dossier["assessment"]
        self.assertEqual(assessment["minimum_exact_match_fraction_observed"]["A"],1.0)
        self.assertEqual(assessment["minimum_exact_match_fraction_observed"]["B"],.916667)
        self.assertTrue(assessment["quality_threshold_met"])
        self.assertIn(assessment["status"],{
            "MEETS_CONFIGURED_THRESHOLDS","DOES_NOT_MEET_CONFIGURED_THRESHOLDS"})
        self.assertGreaterEqual(assessment["repeat_only_max_over_min_latency_ratio"]["A"],1.0)
        high=make_plan(**{**self.config,"quality_floor":1.0})
        strict=build_dossier(high,self.receipts)
        self.assertFalse(strict["assessment"]["quality_threshold_met"])
        self.assertEqual(strict["assessment"]["status"],"DOES_NOT_MEET_CONFIGURED_THRESHOLDS")
        self.assertTrue(verify_dossier(strict)["passed"])

    def test_no_model_or_network_calls_during_review(self):
        with patch("phirsi.field_lab.request_json") as network, \
             patch("phirsi.field_lab.preflight") as preflight:
            self.assertTrue(verify_dossier(self.dossier)["passed"])
            browser_summary(self.dossier)
            network.assert_not_called()
            preflight.assert_not_called()

    def test_plan_rejects_unsafe_budgets_and_aliases(self):
        for change in [
            {"run_count":2}, {"run_count":7}, {"first_seed":-1},
            {"quality_floor":.2}, {"quality_floor":float("nan")},
            {"max_repeat_median_latency_spread":.99},
            {"model_a":"fixture-b"}, {"model_b":"../escape"},
            {"rounds":3},
        ]:
            with self.subTest(change=change):
                with self.assertRaises(InvalidExperiment):
                    make_plan(**{**self.config,**change})
        modified=deepcopy(self.plan)
        modified["quality_floor"]=.5
        with self.assertRaises(InvalidExperiment):
            validate_plan(modified)

    def test_wrong_order_missing_runs_and_mixed_configuration_rejected(self):
        for values in [
            self.receipts[:2],
            [self.receipts[1],self.receipts[0],self.receipts[2]],
            [self.receipts[0],self.receipts[0],self.receipts[2]],
        ]:
            with self.assertRaises(InvalidExperiment):
                build_dossier(self.plan,values)
        bad=deepcopy(self.receipts)
        bad[1]["plan"]["max_tokens"]=32
        rehash(bad[1]["plan"],"plan_sha256")
        rehash(bad[1],"receipt_sha256")
        with self.assertRaises(InvalidExperiment):
            build_dossier(self.plan,bad)

    def test_forged_policy_and_status_rejected_even_rehashed(self):
        for change in ["policy","status","raw_source","model_score","cold_attestation"]:
            altered=deepcopy(self.dossier)
            if change=="policy":
                altered["governance"]["automatic_promotion"]=True
            elif change=="status":
                altered["assessment"]["status"]="APPROVED_FOR_DEPLOYMENT"
            elif change=="raw_source":
                altered["original_r9_receipts"][0]["metrics"]["models"]["A"]["correct_count"]=0
                rehash(altered["original_r9_receipts"][0],"receipt_sha256")
            elif change=="model_score":
                altered["assessment"]["entries"][1]["model_b_accuracy"]=1.0
            else:
                altered["assessment"]["run_order_labels_are_operator_declared_not_cold_warm_attestations"]=False
            rehash(altered,"dossier_sha256")
            with self.subTest(change=change):
                self.assertFalse(verify_dossier(altered)["passed"])

    def test_partial_or_changed_gguf_fingerprints_rejected(self):
        partial=deepcopy(self.receipts)
        partial[0]["selected_local_file_fingerprints"]["A"]={
            "sha256":"a"*64, "size_bytes":128, "header":"GGUF",
            "declared_by_operator":True,"bound_to_running_phiserve_process":False,
        }
        rehash(partial[0],"receipt_sha256")
        with self.assertRaises(InvalidExperiment):
            build_dossier(self.plan,partial)
        complete=deepcopy(partial)
        for j in (1,2):
            complete[j]["selected_local_file_fingerprints"]["A"]=deepcopy(
                complete[0]["selected_local_file_fingerprints"]["A"])
            rehash(complete[j],"receipt_sha256")
        dossier=build_dossier(self.plan,complete)
        self.assertFalse(dossier["assessment"]["operator_selected_file_evidence"]["A"]["server_weight_binding_verified"])
        complete[2]["selected_local_file_fingerprints"]["A"]["sha256"]="b"*64
        rehash(complete[2],"receipt_sha256")
        with self.assertRaises(InvalidExperiment):
            build_dossier(self.plan,complete)

    def test_browser_report_excludes_original_answer_hashes(self):
        s=browser_summary(self.dossier)
        self.assertEqual(s["schema"],"phirsi.workstation_acceptance_summary.v1")
        self.assertTrue(s["original_receipts_not_in_browser_summary"])
        self.assertTrue(s["shape_only_browser_preview"])
        self.assertFalse(s["independently_authenticated"])
        self.assertNotIn("original_r9_receipts",s)
        self.assertFalse(s["governance"]["model_deployment_authorized"])

    def test_cli_plan_pack_verify_summary_and_overwrite(self):
        with TemporaryDirectory() as root:
            folder=Path(root)
            plan_path=folder/"plan.json"
            out=folder/"dossier.json"
            summary=folder/"summary.json"
            paths=[folder/f"r9-{i}.json" for i in range(3)]
            for path,receipt in zip(paths,self.receipts):
                path.write_text(json.dumps(receipt,sort_keys=True),encoding="utf-8")
            cmd=["plan","--model-a","fixture-a","--model-b","fixture-b",
                 "--rounds","1","--max-tokens","16","--timeout-seconds","5",
                 "--output",str(plan_path)]
            self.assertEqual(main(cmd),0)
            self.assertEqual(main(cmd),2)
            pack=["pack","--plan",str(plan_path)]
            for path in paths:
                pack.extend(["--receipt",str(path)])
            pack.extend(["--output",str(out)])
            self.assertEqual(main(pack),0)
            self.assertEqual(main(pack),2)
            self.assertEqual(main(["verify",str(out)]),0)
            self.assertEqual(main(["summary",str(out),"--output",str(summary)]),0)
            self.assertEqual(main(["summary",str(out),"--output",str(summary)]),2)
            self.assertFalse(json.loads(summary.read_text())["governance"]["automatic_promotion"])


if __name__=="__main__":
    unittest.main()
