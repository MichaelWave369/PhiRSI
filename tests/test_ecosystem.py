"""R5 tests: source-bound handoffs, no-authority invariants and real GET-only fixture."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from phirsi.lab import InvalidExperiment, digest, run_experiment
from phirsi.study import make_plan, run_study
from phirsi.proposal import prepare as make_proposal
from phirsi.phiserve_bench import run_benchmark
from phirsi.ecosystem import (
    NO_AUTHORITY, REVIEW_TARGETS, agentora_doctor,
    make_handoff, verify_handoff, _get_agentora,
)
from phirsi.ecosystem_cli import main

SOURCE = "def count_primes(limit):\n    return sum(1 for n in range(2, limit+1) if all(n%d for d in range(2,int(n**0.5)+1)))\n"


def _fake_phiserve(method, route, **kwargs):
    if route == "/health":
        return {"status": "ok"}
    if route == "/v1/models":
        return {"data": [{"id": "fixture-model"}]}
    text = kwargs["payload"]["messages"][-1]["content"]
    answer = "MINT" if "mint" in text else "42" if "17 + 25" in text else "apple"
    return {"choices": [{"message": {"content": answer}}], "usage": {"completion_tokens": 2}}


class FakeAgentora(BaseHTTPRequestHandler):
    events = []

    def log_message(self, *args):
        pass

    def _send(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        FakeAgentora.events.append(("GET", self.path))
        if self.path == "/api/health":
            return self._send(200, {"ok": True, "service": "agentora"})
        if self.path == "/api/system/version":
            return self._send(200, {"ok": True, "service": "Agentora Studio", "version": "1.0.0"})
        return self._send(404, {"error": "unknown"})

    def do_POST(self):
        FakeAgentora.events.append(("POST", self.path))
        self._send(405, {"error": "method not allowed"})


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r1 = run_experiment(max_n=1000, cases=2, rounds=1, warmups=0)
        cls.r2 = run_study(make_plan(max_n=1000, cases=2, rounds=1, warmups=0))
        cls.r3 = make_proposal(
            source=SOURCE, proposal_id="safe-candidate-369",
            hypothesis="A candidate proposal will remain held",
        )
        with patch("phirsi.phiserve_bench.request_json", side_effect=_fake_phiserve):
            cls.r4 = run_benchmark(model="fixture-model", rounds=1, approved=True)
        cls.sources = {"r1": cls.r1, "r2": cls.r2, "r3": cls.r3, "r4": cls.r4}

    def test_all_four_adapters_accept_existing_real_validators(self):
        for kind, source in self.sources.items():
            with self.subTest(kind=kind):
                handoff = make_handoff(kind, source)
                self.assertTrue(verify_handoff(handoff, kind, source)["passed"])
                self.assertEqual(handoff["disposition"], "REVIEW_ONLY")
                self.assertEqual(handoff["policy"], NO_AUTHORITY)
                self.assertEqual(handoff["targets"], REVIEW_TARGETS)
                self.assertFalse(handoff["handoff_is_receipt_of_external_execution"])
                self.assertFalse(handoff["source_checks"]["origin_authenticated"])
                self.assertNotIn("source", handoff)
                self.assertNotIn("choices", json.dumps(handoff))

    def test_tampered_source_rejected_even_when_handoff_untouched(self):
        for kind, original in self.sources.items():
            with self.subTest(kind=kind):
                handoff = make_handoff(kind, original)
                changed = deepcopy(original)
                changed["fictitious_approval"] = True
                self.assertFalse(verify_handoff(handoff, kind, changed)["passed"])

    def test_forged_policy_rejected_even_when_rehashed(self):
        packet = make_handoff("r2", self.r2)
        for key, value in (
            ("execution_authorized", True),
            ("writeback_authorized", True),
            ("authorized_actions", ["launch_mission"]),
            ("human_review_required", False),
        ):
            with self.subTest(key=key):
                modified = deepcopy(packet)
                modified["policy"][key] = value
                modified["handoff_sha256"] = digest({
                    k: v for k, v in modified.items() if k != "handoff_sha256"
                })
                self.assertFalse(verify_handoff(modified, "r2", self.r2)["passed"])

    def test_changed_or_forged_summary_rejected(self):
        packet = make_handoff("r4", self.r4)
        packet["summary"]["exact_match_fraction"] = 2.0
        packet["handoff_sha256"] = digest({
            k: v for k, v in packet.items() if k != "handoff_sha256"
        })
        self.assertFalse(verify_handoff(packet, "r4", self.r4)["passed"])

    def test_reject_incorrect_kind(self):
        with self.assertRaises(InvalidExperiment):
            make_handoff("r5", self.r1)
        self.assertFalse(verify_handoff(make_handoff("r1", self.r1), "r2", self.r1)["passed"])

    def test_invalid_source_rejected(self):
        for kind in self.sources:
            with self.subTest(kind=kind):
                with self.assertRaises(InvalidExperiment):
                    make_handoff(kind, {"trust_me": True})

    def test_cli_roundtrip_refuses_overwrite(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.json"
            dest = Path(tmp) / "handoff.json"
            source.write_text(json.dumps(self.r1), encoding="utf-8")
            args = ["prepare", "--kind", "r1", "--source", str(source), "--output", str(dest)]
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 2)
            self.assertEqual(main([
                "verify", "--kind", "r1", "--source", str(source), "--handoff", str(dest),
            ]), 0)
            self.assertFalse(json.loads(dest.read_text())["policy"]["merge_authorized"])

    def test_no_network_during_handoff(self):
        with patch("phirsi.ecosystem._get_agentora") as external:
            make_handoff("r3", self.r3)
            verify_handoff(make_handoff("r1", self.r1), "r1", self.r1)
            external.assert_not_called()


class AgentoraDoctorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = HTTPServer(("127.0.0.1", 0), FakeAgentora)
        cls.port = cls.http.server_address[1]
        cls.thread = Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=5)

    def test_agentora_real_get_only_loopback(self):
        FakeAgentora.events.clear()
        result = agentora_doctor(port=self.port)
        self.assertTrue(result["health_ok"])
        self.assertTrue(result["read_only_local_preflight"])
        self.assertFalse(result["mission_dispatched"])
        self.assertEqual(result["agentora_compatible_for_research_missions"], "UNVERIFIED")
        self.assertEqual(FakeAgentora.events, [
            ("GET", "/api/health"), ("GET", "/api/system/version"),
        ])

    def test_route_and_port_restrictions(self):
        with self.assertRaises(InvalidExperiment):
            _get_agentora("/api/integrations/runs/launch", self.port, 3)
        with self.assertRaises(InvalidExperiment):
            _get_agentora("/api/health", -1, 3)
        with self.assertRaises(InvalidExperiment):
            _get_agentora("/api/health", self.port, 30)

    def test_cli_doctor(self):
        self.assertEqual(main(["agentora-doctor", "--port", str(self.port)]), 0)


if __name__ == "__main__":
    unittest.main()
