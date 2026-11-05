"""R11 block-ordered fake PhiServe tests, not measurements of real model weights."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from phirsi.field_lab import CASES as R9_CASES
from phirsi.lab import InvalidExperiment, digest
from phirsi.switch_isolation import (
    CASES, GUARD, _expected_rows, browser_summary,
    make_plan, run_isolation, validate_plan, verify_isolation,
)
from phirsi.switch_cli import main

SENT=[]


def fake_request(method,route,**kwargs):
    if method!="POST" or route!="/v1/chat/completions":
        raise AssertionError("unauthorized mock endpoint")
    body=kwargs["payload"]
    if body["stream"] is not False or body["temperature"]!=0:
        raise AssertionError("not deterministic non-streaming protocol")
    prompt=body["messages"][-1]["content"]
    task=next(t for t in CASES if t["prompt"]==prompt)
    SENT.append((body["model"],task["id"],body["seed"],kwargs.get("token")))
    return {
        "choices":[{"message":{"content":task["expected"]}}],
        "usage":{"completion_tokens":3},
    }


def rehash(payload,field):
    payload[field]=digest({k:v for k,v in payload.items() if k!=field})


class IsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=make_plan(
            model_a="fixture-a",model_b="fixture-b",
            repeat_requests=2,max_tokens=16,timeout_seconds=5,
        )
        SENT.clear()
        with patch("phirsi.switch_isolation.request_json",side_effect=fake_request), \
             patch("phirsi.switch_isolation.preflight",return_value={"passed":True}):
            cls.receipt=run_isolation(cls.plan,approved=True,token="local-test-token")
        cls.calls=list(SENT)

    def test_four_block_schedule_uses_identical_prompt_within_block(self):
        self.assertEqual(len(CASES),2)
        self.assertEqual([t["id"] for t in CASES],["upper","add"])
        self.assertEqual(len(self.calls),12)
        self.assertEqual(
            [m for m,c,s,t in self.calls],
            ["fixture-a"]*3+["fixture-b"]*3+["fixture-a"]*3+["fixture-b"]*3)
        self.assertEqual(
            [c for m,c,s,t in self.calls],["upper"]*6+["add"]*6)
        self.assertTrue(all(seed==369 and token=="local-test-token"
                            for model,c,seed,token in self.calls))
        phases=[row["phase"] for row in self.receipt["observations"]]
        self.assertEqual(phases,["first_request","repeat_request","repeat_request"]*4)

    def test_alias_change_avoids_claiming_actual_model_switch(self):
        rows=[r for r in self.receipt["observations"] if r["phase"]=="first_request"]
        self.assertEqual([r["requested_alias_changed"] for r in rows],[False,True,True,True])
        self.assertEqual([r["previous_requested_alias"] for r in rows],
                         [None,"fixture-a","fixture-b","fixture-a"])
        m=self.receipt["assessment"]
        self.assertEqual(m["requested_alias_change_count"],3)
        self.assertIsNone(m["model_loading_time_ms"])
        self.assertIsNone(m["cold_start_time_ms"])
        self.assertFalse(self.receipt["governance"]["true_model_loading_ms_measured"])
        self.assertFalse(self.receipt["governance"]["warm_cache_verified"])

    def test_recompute_and_source_checks_succeed(self):
        check=verify_isolation(self.receipt)
        self.assertTrue(check["passed"],check)
        self.assertFalse(check["historical_inference_authenticated"])
        self.assertFalse(check["model_load_event_independently_observed"])
        self.assertEqual(self.receipt["assessment"]["block_count"],4)
        self.assertEqual(self.receipt["assessment"]["models"]["A"]["first_request_count"],2)
        self.assertEqual(self.receipt["assessment"]["models"]["B"]["repeat_request_count"],4)
        self.assertEqual(self.receipt["assessment"]["models"]["A"]["exact_match_count"],6)
        self.assertEqual(self.receipt["assessment"]["decision"],
                         "DESCRIPTIVE_ONLY_NO_MODEL_LOADING_CLAIM")

    def test_explicit_approval_blocks_all_traffic(self):
        with patch("phirsi.switch_isolation.request_json") as outbound, \
             patch("phirsi.switch_isolation.preflight") as preflight:
            with self.assertRaises(InvalidExperiment):
                run_isolation(self.plan)
            preflight.assert_not_called()
            outbound.assert_not_called()

    def test_plan_is_predeclared_and_bounded(self):
        bads=[
            {"model_b":"fixture-a"},
            {"model_a":"http://remote.example"},
            {"model_b":"../secret"},
            {"repeat_requests":1},
            {"repeat_requests":4},
            {"max_tokens":1000},
            {"timeout_seconds":90},
            {"first_role":"C"},
            {"seed":-1},
        ]
        for bad in bads:
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidExperiment):
                    make_plan(**{
                        "model_a":"fixture-a","model_b":"fixture-b",**bad
                    })
        altered=deepcopy(self.plan)
        altered["repeat_requests"]=3
        with self.assertRaises(InvalidExperiment):
            validate_plan(altered)

    def test_starting_with_b_reverses_order_without_becoming_new_proof(self):
        bplan=make_plan(
            model_a="fixture-a",model_b="fixture-b",first_role="B",
            repeat_requests=2,max_tokens=16,timeout_seconds=5,
        )
        fields=list(_expected_rows(bplan))
        self.assertEqual([row["role"] for row,task in fields[::3]],
                         ["B","A","B","A"])
        self.assertEqual([row["requested_alias_changed"] for row,task in fields[::3]],
                         [False,True,True,True])
        self.assertTrue(verify_isolation(self.receipt)["passed"])

    def test_forgeries_fail_even_when_digest_recomputed(self):
        changes={
            "role":lambda r:r["observations"][0].update(role="B"),
            "phase":lambda r:r["observations"][1].update(phase="first_request"),
            "switch":lambda r:r["observations"][3].update(requested_alias_changed=False),
            "previous":lambda r:r["observations"][3].update(previous_requested_alias=None),
            "score":lambda r:r["observations"][0].update(exact_match=False),
            "latency":lambda r:r["observations"][0].update(http_latency_ms=-1),
            "token":lambda r:r["observations"][0].update(provider_completion_tokens=-5),
            "authority":lambda r:r["governance"].update(automatic_promotion=True),
            "loading_claim":lambda r:r["governance"].update(true_model_loading_ms_measured=True),
            "metric":lambda r:r["assessment"]["models"]["A"].update(first_median_http_ms=999999),
            "decision":lambda r:r["assessment"].update(decision="B_WINS_DEPLOY"),
        }
        for name,change in changes.items():
            altered=deepcopy(self.receipt)
            change(altered)
            rehash(altered,"receipt_sha256")
            with self.subTest(name=name):
                self.assertFalse(verify_isolation(altered)["passed"])

    def test_no_responses_prompts_or_bearer_secrets_persist(self):
        s=json.dumps(self.receipt)
        self.assertNotIn("local-test-token",s)
        self.assertNotIn('"ORBIT"',s)
        self.assertNotIn("Write the word orbit",s)
        self.assertEqual(self.receipt["governance"],GUARD)
        self.assertFalse(self.receipt["assessment"]["automatic_promotion"])

    def test_missing_token_counts_remain_unknown(self):
        def no_usage(method,route,**kwargs):
            res=fake_request(method,route,**kwargs)
            res.pop("usage")
            return res
        with patch("phirsi.switch_isolation.request_json",side_effect=no_usage), \
             patch("phirsi.switch_isolation.preflight",return_value={"passed":True}):
            receipt=run_isolation(self.plan,approved=True)
        self.assertTrue(all(row["provider_completion_tokens"] is None
                            for row in receipt["observations"]))
        self.assertTrue(verify_isolation(receipt)["passed"])

    def test_browser_summary_contains_only_aggregates(self):
        summary=browser_summary(self.receipt)
        self.assertEqual(summary["schema"],"phirsi.switch_isolation_summary.v1")
        self.assertEqual(summary["repeat_requests_per_block"],2)
        self.assertTrue(summary["read_only_local_preview"])
        self.assertFalse(summary["source_authenticated"])
        self.assertNotIn("observations",summary)
        self.assertFalse(summary["governance"]["automatic_promotion"])

    def test_cli_roundtrip_refuses_overwrite_and_network_without_permission(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            p=root/"plan.json"
            r=root/"receipt.json"
            s=root/"summary.json"
            plan_args=[
                "plan","--model-a","fixture-a","--model-b","fixture-b",
                "--repeat-requests","2","--max-tokens","16",
                "--timeout-seconds","5","--output",str(p),
            ]
            self.assertEqual(main(plan_args),0)
            self.assertEqual(main(plan_args),2)
            args=["run","--plan",str(p),"--output",str(r)]
            with patch("phirsi.switch_isolation.request_json") as net:
                self.assertEqual(main(args),2)
                net.assert_not_called()
            with patch("phirsi.switch_isolation.request_json",side_effect=fake_request), \
                 patch("phirsi.switch_isolation.preflight",return_value={"passed":True}):
                self.assertEqual(main(args+["--approve-local-inference"]),0)
            self.assertEqual(main(args+["--approve-local-inference"]),2)
            self.assertEqual(main(["verify",str(r)]),0)
            self.assertEqual(main(["summary",str(r),"--output",str(s)]),0)
            self.assertEqual(main(["summary",str(r),"--output",str(s)]),2)


if __name__=="__main__":
    unittest.main()
