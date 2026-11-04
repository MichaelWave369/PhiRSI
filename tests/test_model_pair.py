"""R8 tests against a FAKE loopback PhiServe server, never actual model weights."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from phirsi.lab import InvalidExperiment, digest
from phirsi.model_pair import (
    GUARD, make_plan, validate_plan, run_pair,
    verify_pair, summary_for_browser, _order,
)
from phirsi.model_pair_cli import main


class FakeService(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def reply(self, status, obj):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        FakeService.seen.append(("GET", self.path, None, None))
        if self.path == "/health":
            return self.reply(200, {"status": "ok"})
        if self.path == "/v1/models":
            return self.reply(200, {"data": [{"id": "model-a"}, {"id": "model-b"}]})
        return self.reply(404, {"error": "unsupported"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.reply(404, {"error": "unsupported"})
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        data = json.loads(raw)
        FakeService.seen.append((
            "POST", self.path, data["model"], self.headers.get("Authorization"),
        ))
        question = data["messages"][-1]["content"]
        answer = "MINT" if "mint" in question else "42" if "17 + 25" in question else "apple"
        if data["model"] == "model-b" and "17 + 25" in question:
            answer = "forty two"  # one intentionally imperfect toy response
        return self.reply(200, {
            "choices": [{"message": {"role": "assistant", "content": answer}}],
            "usage": {"completion_tokens": 2},
        })


class PairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeService)
        cls.port = cls.server.server_address[1]
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.plan = make_plan(
            model_a="model-a", model_b="model-b", port=cls.port,
            rounds=2, max_tokens=16, timeout_seconds=5,
        )
        FakeService.seen.clear()
        cls.receipt = run_pair(cls.plan, approved=True, token="local-only-test-token")
        cls.initial_requests = list(FakeService.seen)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_real_loopback_protocol_and_balanced_requests(self):
        posts = [line for line in self.initial_requests if line[0] == "POST"]
        self.assertEqual(len(posts), 12)
        self.assertEqual([x[2] for x in posts[:6]], [
            "model-a", "model-b", "model-b", "model-a", "model-a", "model-b"
        ])
        self.assertTrue(all(x[1] == "/v1/chat/completions" for x in posts))
        self.assertTrue(all(x[3] == "Bearer local-only-test-token" for x in posts))
        self.assertEqual(sum(x[0] == "GET" for x in self.initial_requests), 4)
        self.assertEqual(len(self.receipt["observations"]), 12)
        self.assertEqual(self.receipt["assessment"]["paired_task_count"], 6)

    def test_scores_are_narrow_fixed_task_comparisons(self):
        score = self.receipt["assessment"]
        self.assertEqual(score["models"]["A"]["exact_match_fraction"], 1.0)
        self.assertEqual(score["models"]["B"]["exact_match_fraction"], 0.666667)
        self.assertEqual(score["decision"], "DESCRIPTIVE_ONLY_NO_WINNER")
        self.assertFalse(score["task_quality_generalization_claim"])
        self.assertFalse(score["gpu_vram_measured"])
        self.assertIsInstance(score["median_observed_a_over_b_latency_ratio"], float)
        self.assertTrue(verify_pair(self.receipt)["passed"])

    def test_no_secret_or_completion_text_in_receipt(self):
        encoded = json.dumps(self.receipt)
        self.assertNotIn("local-only-test-token", encoded)
        self.assertNotIn("forty two", encoded)
        self.assertNotIn('"MINT"', encoded)
        self.assertFalse(self.receipt["governance"]["model_intelligence_improvement_claim"])
        self.assertEqual(self.receipt["governance"], GUARD)
        self.assertFalse(verify_pair(self.receipt)["historical_inference_authenticated"])

    def test_denied_inference_cannot_call_server(self):
        with patch("phirsi.model_pair.request_json") as outbound, \
             patch("phirsi.model_pair.preflight") as preflight:
            with self.assertRaises(InvalidExperiment):
                run_pair(self.plan)
            outbound.assert_not_called()
            preflight.assert_not_called()

    def test_unknown_or_same_model_alias_rejected(self):
        for args in [
            {"model_a": "same", "model_b": "same"},
            {"model_a": "http://evil.tld", "model_b": "model-b"},
            {"model_a": "model-a", "model_b": "../secret"},
            {"model_a": "model-a", "model_b": "model-b", "rounds": 3},
            {"model_a": "model-a", "model_b": "model-b", "port": True},
            {"model_a": "model-a", "model_b": "model-b", "timeout_seconds": 100},
        ]:
            with self.subTest(args=args):
                with self.assertRaises(InvalidExperiment):
                    make_plan(**args)

    def test_plan_checksum_binding(self):
        broken = deepcopy(self.plan)
        broken["model_b"] = "other"
        with self.assertRaises(InvalidExperiment):
            validate_plan(broken)

    def test_order_or_response_forgery_fails_even_rehashed(self):
        for change in ("role", "exact_match", "latency", "promotion", "summary"):
            altered = deepcopy(self.receipt)
            if change == "role":
                altered["observations"][0]["role"] = "B"
            if change == "exact_match":
                altered["observations"][0]["exact_match"] = False
            if change == "latency":
                altered["observations"][0]["end_to_end_latency_ms"] = -1
            if change == "promotion":
                altered["governance"]["automatic_promotion"] = True
            if change == "summary":
                altered["assessment"]["decision"] = "MODEL_B_WINS_AND_MERGES"
            altered["receipt_sha256"] = digest({
                k: v for k, v in altered.items() if k != "receipt_sha256"
            })
            with self.subTest(change=change):
                self.assertFalse(verify_pair(altered)["passed"])

    def test_alternation_and_unreported_usage(self):
        self.assertEqual(_order(0, 0), ("A", "B"))
        self.assertEqual(_order(0, 1), ("B", "A"))
        self.assertEqual(_order(1, 0), ("B", "A"))
        def fake(method, route, **kwargs):
            if route == "/health":
                return {"status": "ok"}
            if route == "/v1/models":
                return {"data": [{"id": "model-a"}, {"id": "model-b"}]}
            question = kwargs["payload"]["messages"][-1]["content"]
            answer = "MINT" if "mint" in question else "42" if "17 + 25" in question else "apple"
            return {"choices": [{"message": {"content": answer}}]}
        with patch("phirsi.model_pair.request_json", side_effect=fake), \
             patch("phirsi.model_pair.preflight", return_value={"passed": True}):
            receipt = run_pair(make_plan(
                model_a="model-a", model_b="model-b",
                rounds=1,
            ), approved=True)
        self.assertIsNone(receipt["assessment"]["models"]["A"]["estimated_end_to_end_tokens_per_sec"])
        self.assertIsNone(receipt["assessment"]["models"]["B"]["provider_reported_completion_tokens"])
        self.assertTrue(verify_pair(receipt)["passed"])

    def test_browser_summary_contains_no_raw_messages_or_promotion(self):
        view = summary_for_browser(self.receipt)
        self.assertEqual(view["schema"], "phirsi.phiserve_pair_summary.v1")
        self.assertEqual(view["model_a_alias"], "model-a")
        self.assertFalse(view["governance"]["automatic_promotion"])
        self.assertTrue(view["report_is_not_authenticated"])
        self.assertNotIn("local-only-test-token", json.dumps(view))

    def test_cli_roundtrip_approval_no_overwrite_and_summary(self):
        with TemporaryDirectory() as root:
            p = Path(root)
            plan_path = p / "plan.json"
            receipt_path = p / "pair.json"
            summary_path = p / "summary.json"
            cmd = [
                "plan", "--model-a", "model-a", "--model-b", "model-b",
                "--port", str(self.port), "--rounds", "1", "--timeout-seconds", "5",
                "--output", str(plan_path),
            ]
            self.assertEqual(main(cmd), 0)
            self.assertEqual(main(cmd), 2)
            call = ["run", "--plan", str(plan_path), "--output", str(receipt_path)]
            with patch("phirsi.model_pair.request_json") as outbound:
                self.assertEqual(main(call), 2)
                outbound.assert_not_called()
            with patch.dict(os.environ, {"PHIRSI_PHISERVE_TOKEN": "local-only-test-token"}):
                self.assertEqual(main(call + ["--approve-local-inference"]), 0)
            self.assertEqual(main(call + ["--approve-local-inference"]), 2)
            self.assertEqual(main(["verify", str(receipt_path)]), 0)
            self.assertEqual(main(["summary", str(receipt_path), "--output", str(summary_path)]), 0)
            self.assertEqual(main(["summary", str(receipt_path), "--output", str(summary_path)]), 2)
            self.assertNotIn("local-only-test-token", summary_path.read_text())


if __name__ == "__main__":
    unittest.main()
