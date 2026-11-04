"""R4 tests: true loopback protocol to a FAKE server, never actual model weights."""
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
from phirsi.phiserve_bench import (
    _extract_answer, _config, _hash_answer, preflight, request_json,
    run_benchmark, verify_benchmark, CASES,
)
from phirsi.phiserve_cli import main


class FakePhiServe(BaseHTTPRequestHandler):
    requests_seen = []

    def log_message(self, *args):
        pass

    def _json(self, status, obj):
        content = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path == "/health":
            return self._json(200, {"status": "ok", "runtime": "fake-fixture"})
        if self.path == "/v1/models":
            return self._json(200, {"data": [{"id": "fixture-model", "object": "model"}]})
        return self._json(404, {"error": "unavailable"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self._json(404, {"error": "unavailable"})
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        FakePhiServe.requests_seen.append({
            "authorization": self.headers.get("Authorization"),
            "model": request.get("model"), "stream": request.get("stream"),
            "max_tokens": request.get("max_tokens"), "temperature": request.get("temperature"),
        })
        question = request["messages"][-1]["content"]
        if "mint" in question:
            answer = "MINT"
        elif "17 + 25" in question:
            answer = "42"
        else:
            answer = "apple"
        return self._json(200, {
            "choices": [{"message": {"role": "assistant", "content": answer}}],
            "usage": {"completion_tokens": 2},
        })


class R4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakePhiServe)
        cls.port = cls.server.server_address[1]
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_direct_loopback_and_auth(self):
        data = request_json("GET", "/health", port=self.port, timeout_seconds=5,
                            token="local-test-secret")
        self.assertEqual(data["status"], "ok")
        self.assertTrue(preflight(model="fixture-model", port=self.port)["passed"])
        with self.assertRaises(InvalidExperiment):
            preflight(model="wrong-model", port=self.port)

    def test_no_unregistered_route_or_external_hosts(self):
        with self.assertRaises(InvalidExperiment):
            request_json("GET", "https://example.com", port=self.port,
                         timeout_seconds=5, token=None)
        with self.assertRaises(InvalidExperiment):
            request_json("GET", "/api/generate", port=self.port,
                         timeout_seconds=5, token=None)

    def test_approval_gate_before_network(self):
        with patch("phirsi.phiserve_bench.request_json") as mocked:
            with self.assertRaises(InvalidExperiment):
                run_benchmark(model="fixture-model", port=self.port, approved=False)
            mocked.assert_not_called()

    def test_real_http_fake_model_receipt(self):
        FakePhiServe.requests_seen.clear()
        evidence = run_benchmark(model="fixture-model", port=self.port, rounds=2,
                                 max_tokens=16, timeout_seconds=5, token="local-test-secret",
                                 approved=True)
        self.assertEqual(len(evidence["observations"]), 6)
        self.assertEqual(evidence["assessment"]["exact_match_fraction"], 1.0)
        self.assertTrue(verify_benchmark(evidence)["passed"])
        self.assertFalse(verify_benchmark(evidence)["latency_replicated"])
        self.assertFalse(evidence["assessment"]["gpu_measurement_performed"])
        self.assertFalse(evidence["assessment"]["model_intelligence_gain_claim"])
        self.assertEqual(evidence["assessment"]["reported_completion_tokens_total"], 12)
        self.assertEqual(len(FakePhiServe.requests_seen), 6)
        for row in FakePhiServe.requests_seen:
            self.assertEqual(row["authorization"], "Bearer local-test-secret")
            self.assertEqual(row["model"], "fixture-model")
            self.assertFalse(row["stream"])
            self.assertEqual(row["temperature"], 0)
        dumped = json.dumps(evidence)
        self.assertNotIn("local-test-secret", dumped)
        for task in CASES:
            self.assertNotIn(task["prompt"], dumped)
        self.assertNotIn("MINT", dumped)
        self.assertNotIn('"apple"', dumped)
        self.__class__.receipt = evidence

    def test_missing_usage_is_unknown_not_zero(self):
        def fake(method, route, **kwargs):
            if route == "/health":
                return {"status": "ok"}
            if route == "/v1/models":
                return {"data": [{"id": "fixture-model"}]}
            question = kwargs["payload"]["messages"][-1]["content"]
            answer = ("MINT" if "mint" in question else
                      "42" if "17 + 25" in question else "apple")
            return {"choices": [{"message": {"content": answer}}]}
        with patch("phirsi.phiserve_bench.request_json", side_effect=fake):
            receipt = run_benchmark(model="fixture-model", rounds=1, approved=True)
        self.assertIsNone(receipt["assessment"]["reported_completion_tokens_total"])
        self.assertIsNone(receipt["assessment"]["estimated_end_to_end_tokens_per_sec"])
        self.assertTrue(verify_benchmark(receipt)["passed"])

    def test_untrusted_or_missing_responses_fail_closed(self):
        for reply in (
            {"choices": []},
            {"choices": [{"message": {"content": 123}}]},
            {"choices": [{"message": {"content": "good"}}], "usage": {"completion_tokens": -1}},
            {"choices": [{"message": {"content": "good"}}], "usage": {"completion_tokens": True}},
        ):
            with self.subTest(reply=reply):
                with self.assertRaises(InvalidExperiment):
                    _extract_answer(reply)

    def test_bad_configuration_and_token(self):
        for config in (
            {"model": "http://evil.host"},
            {"model": "../model"},
            {"model": "fixture-model", "port": True},
            {"model": "fixture-model", "rounds": 4},
            {"model": "fixture-model", "max_tokens": 1024},
        ):
            with self.subTest(config=config):
                with self.assertRaises(InvalidExperiment):
                    _config(config.get("model", "fixture-model"), config.get("port", 11435),
                            config.get("rounds", 1), config.get("max_tokens", 16), 5, 369)
        with self.assertRaises(InvalidExperiment):
            request_json("GET", "/health", port=self.port, timeout_seconds=5,
                         token="token\ninjection")

    def test_receipt_hash_cannot_fake_correctness_or_authority(self):
        receipt = run_benchmark(model="fixture-model", port=self.port, rounds=1,
                                timeout_seconds=5, approved=True)
        change = deepcopy(receipt)
        change["observations"][0]["exact_match"] = False
        change["receipt_sha256"] = digest({k: v for k, v in change.items() if k != "receipt_sha256"})
        self.assertFalse(verify_benchmark(change)["passed"])
        change = deepcopy(receipt)
        change["assessment"]["automatic_promotion"] = True
        change["receipt_sha256"] = digest({k: v for k, v in change.items() if k != "receipt_sha256"})
        self.assertFalse(verify_benchmark(change)["passed"])

    def test_cli_denied_without_approval_and_no_overwrite(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "sample.json"
            with patch("phirsi.phiserve_cli.run_benchmark") as mocked:
                self.assertEqual(main(["run", "--model", "fixture-model",
                                       "--port", str(self.port), "--output", str(dest)]), 2)
                mocked.assert_not_called()
            with patch.dict(os.environ, {"PHIRSI_PHISERVE_TOKEN": "local-test-secret"}):
                self.assertEqual(main(["doctor", "--model", "fixture-model",
                                       "--port", str(self.port)]), 0)
                args = ["run", "--model", "fixture-model", "--port", str(self.port),
                        "--rounds", "1", "--approve-local-inference", "--output", str(dest)]
                self.assertEqual(main(args), 0)
                self.assertEqual(main(args), 2)
                self.assertEqual(main(["verify", str(dest)]), 0)
                self.assertNotIn("local-test-secret", dest.read_text())

if __name__ == "__main__":
    unittest.main()
