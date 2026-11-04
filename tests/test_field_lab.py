"""R9 fake PhiServe evaluation and conservative field evidence tests."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from phirsi.field_lab import (
    CASES, NO_AUTHORITY, make_plan, validate_plan, fingerprint_gguf,
    field_observation, run_field, verify_field, browser_summary, _order,
)
from phirsi.field_cli import main
from phirsi.lab import InvalidExperiment, digest

PLAN = {"model_a":"fixture-a","model_b":"fixture-b","rounds":1,"max_tokens":16,
        "timeout_seconds":5}
def fake_request(method,route,**kwargs):
    if route=="/health":return {"status":"ok"}
    if route=="/v1/models":return {"data":[{"id":"fixture-a"},{"id":"fixture-b"}]}
    payload=kwargs["payload"]
    prompt=payload["messages"][-1]["content"]
    item=next(c for c in CASES if c["prompt"]==prompt)
    answer=item["expected"]
    if payload["model"]=="fixture-b" and item["id"]=="multiply":answer="wrong"
    return {"choices":[{"message":{"content":answer}}],"usage":{"completion_tokens":4}}

FAKE_FIELD={
    "schema":"PHISERVE_LOCAL_INFERENCE_RECEIPT_V1",
    "status":"LOCAL_TEXT_OUTPUT_OBSERVED",
    "model_alias":"fixture-a",
    "raw_prompt_or_output_stored":False,
    "gpu_execution_verified":False,
    "gpu_process_telemetry":{
        "schema":"PHISERVE_NVIDIA_PROCESS_SAMPLE_V1",
        "status":"PROCESS_MEMORY_DRIVER_SELF_REPORT",
        "sample_attempts":3,"matching_pid_samples":2,"numeric_memory_samples":2,
        "peak_driver_reported_process_memory_mib":4352,
        "cuda_kernel_execution_independently_verified":False,
        "gpu_model_weights_residency_verified":False,
        "physical_hardware_witnessed":False,
    }
}


class R9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=make_plan(**PLAN)
        with patch("phirsi.field_lab.request_json",side_effect=fake_request), \
             patch("phirsi.field_lab.preflight",return_value={"passed":True}):
            cls.receipt=run_field(cls.plan,approved=True,
                phiserve_fields={"A":FAKE_FIELD})

    def test_24_requests_same_12_tasks_and_order(self):
        self.assertEqual(len(CASES),12)
        self.assertEqual(len(self.receipt["observations"]),24)
        self.assertEqual(self.receipt["observations"][0]["role"],"A")
        self.assertEqual(self.receipt["observations"][1]["role"],"B")
        self.assertEqual(self.receipt["observations"][2]["role"],"B")
        self.assertEqual(self.receipt["observations"][3]["role"],"A")
        self.assertEqual(_order(0,0),("A","B"))
        self.assertEqual(_order(0,1),("B","A"))
        self.assertEqual(_order(1,0),("A","B"))
        self.assertEqual(self.receipt["metrics"]["models"]["A"]["correct_count"],12)
        self.assertEqual(self.receipt["metrics"]["models"]["B"]["correct_count"],11)
        self.assertEqual(self.receipt["metrics"]["decision"],"DESCRIPTIVE_ONLY_NO_WINNER")

    def test_receipt_correctness_and_privacy(self):
        verification=verify_field(self.receipt)
        self.assertTrue(verification["passed"],verification)
        self.assertFalse(verification["weight_binding_verified"])
        self.assertEqual(self.receipt["governance"],NO_AUTHORITY)
        string=json.dumps(self.receipt)
        self.assertNotIn('"ORBIT"',string)
        self.assertNotIn('"wrong"',string)
        self.assertNotIn("fixture-token-secret",string)

    def test_forbid_unapproved_network(self):
        with patch("phirsi.field_lab.preflight") as network, \
             patch("phirsi.field_lab.request_json") as inference:
            with self.assertRaises(InvalidExperiment):
                run_field(self.plan,approved=False)
            network.assert_not_called()
            inference.assert_not_called()

    def test_invalid_plan(self):
        for bad in (
            dict(model_a="same",model_b="same"),
            dict(model_a="http://bad",model_b="fixture-b"),
            dict(model_a="fixture-a",model_b="../other"),
            dict(model_a="fixture-a",model_b="fixture-b",rounds=3),
            dict(model_a="fixture-a",model_b="fixture-b",max_tokens=1024),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidExperiment):
                    make_plan(**bad)
        wrong=deepcopy(self.plan)
        wrong["task_sha256"]="0"*64
        wrong["plan_sha256"]=digest({k:v for k,v in wrong.items() if k!="plan_sha256"})
        with self.assertRaises(InvalidExperiment):
            validate_plan(wrong)

    def test_metadata_forgery_rejected_even_rehashed(self):
        for target in ("role","correct","latency","authority","metric","fingerprint","driver"):
            altered=deepcopy(self.receipt)
            if target=="role":altered["observations"][0]["role"]="B"
            if target=="correct":altered["observations"][0]["exact_match"]=False
            if target=="latency":altered["observations"][0]["http_elapsed_ms"]=-1
            if target=="authority":altered["governance"]["automatic_promotion"]=True
            if target=="metric":altered["metrics"]["models"]["B"]["correct_count"]=12
            if target=="fingerprint":
                altered["selected_local_file_fingerprints"]["A"]={
                    "sha256":"0"*64,"size_bytes":100,"header":"GGUF",
                    "declared_by_operator":True,
                    "bound_to_running_phiserve_process":True}
            if target=="driver":
                altered["separate_phiserve_field_observations"]["A"]["independently_attested"]=True
            altered["receipt_sha256"]=digest({k:v for k,v in altered.items() if k!="receipt_sha256"})
            with self.subTest(target=target):
                self.assertFalse(verify_field(altered)["passed"])

    def test_fingerprint_local_file_only(self):
        with TemporaryDirectory() as temp:
            f=Path(temp)/"test.gguf"
            f.write_bytes(b"GGUF"+b"X"*124)
            value=fingerprint_gguf(f)
            self.assertEqual(value["size_bytes"],128)
            self.assertFalse(value["bound_to_running_phiserve_process"])
            alias=Path(temp)/"symlink.gguf"
            alias.symlink_to(f)
            with self.assertRaises(InvalidExperiment):
                fingerprint_gguf(alias)
            f.write_bytes(b"WRNG"+b"X"*124)
            with self.assertRaises(InvalidExperiment):
                fingerprint_gguf(f)

    def test_reject_driver_attestation_and_impossible_samples(self):
        result=field_observation(FAKE_FIELD,"fixture-a")
        self.assertEqual(result["driver_peak_process_memory_mib"],4352)
        self.assertFalse(result["independently_attested"])
        self.assertFalse(result["same_execution_as_r9"])
        bad=deepcopy(FAKE_FIELD)
        bad["gpu_process_telemetry"]["physical_hardware_witnessed"]=True
        with self.assertRaises(InvalidExperiment):
            field_observation(bad,"fixture-a")
        bad=deepcopy(FAKE_FIELD)
        bad["gpu_process_telemetry"]["numeric_memory_samples"]=4
        with self.assertRaises(InvalidExperiment):
            field_observation(bad,"fixture-a")
        with self.assertRaises(InvalidExperiment):
            field_observation(FAKE_FIELD,"fixture-b")

    def test_missing_token_usage_remains_unknown(self):
        def missing_usage(method,route,**kwargs):
            result=fake_request(method,route,**kwargs)
            if "choices" in result:result.pop("usage")
            return result
        with patch("phirsi.field_lab.request_json",side_effect=missing_usage), \
             patch("phirsi.field_lab.preflight",return_value={"passed":True}):
            result=run_field(self.plan,approved=True)
        self.assertIsNone(result["metrics"]["models"]["A"]["provider_tokens_total"])
        self.assertIsNone(result["metrics"]["models"]["B"]["approx_total_http_tokens_per_second"])
        self.assertTrue(verify_field(result)["passed"])

    def test_browser_summary_does_not_invent_gpu_values(self):
        result=browser_summary(self.receipt)
        self.assertEqual(result["schema"],"phirsi.field_summary.v1")
        self.assertTrue(result["not_authenticating_source"])
        self.assertFalse(result["governance"]["vram_from_independently_witnessed_measurement"])
        self.assertFalse(result["governance"]["automatic_promotion"])

    def test_cli_full_roundtrip(self):
        with TemporaryDirectory() as temp:
            path=Path(temp)
            p=path/"plan.json"; r=path/"receipt.json"; s=path/"summary.json"
            cmd=["plan","--model-a","fixture-a","--model-b","fixture-b",
                 "--rounds","1","--timeout-seconds","5","--output",str(p)]
            self.assertEqual(main(cmd),0)
            self.assertEqual(main(cmd),2)
            run=["run","--plan",str(p),"--output",str(r)]
            with patch("phirsi.field_lab.request_json") as net:
                self.assertEqual(main(run),2)
                net.assert_not_called()
            with patch("phirsi.field_lab.request_json",side_effect=fake_request), \
                 patch("phirsi.field_lab.preflight",return_value={"passed":True}):
                self.assertEqual(main(run+["--approve-local-inference"]),0)
            self.assertEqual(main(run+["--approve-local-inference"]),2)
            self.assertEqual(main(["verify",str(r)]),0)
            self.assertEqual(main(["summary",str(r),"--output",str(s)]),0)
            self.assertEqual(main(["summary",str(r),"--output",str(s)]),2)
            self.assertFalse(json.loads(s.read_text())["governance"]["automatic_promotion"])


if __name__=="__main__":
    unittest.main()
