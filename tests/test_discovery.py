"""R6 tests for bounded search, controls, holdout reuse and fail-closed ledger replay."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from phirsi.discovery import (
    CANDIDATES, GOVERNANCE, _derive, _event, make_plan, run_discovery,
    validate_plan, verify_discovery,
)
from phirsi.discovery_cli import main
from phirsi.lab import InvalidExperiment, digest, run_experiment

SMALL = {"max_n": 1000, "cases": 2, "rounds": 1, "warmups": 0}


def rehash(obj, field):
    obj[field] = digest({k: v for k, v in obj.items() if k != field})


class DiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(**SMALL)
        cls.ledger = run_discovery(cls.plan, approved=True)

    def test_replay_verification(self):
        result = verify_discovery(self.ledger)
        self.assertTrue(result["passed"], result)
        self.assertFalse(result["historical_timings_authenticated"])
        self.assertFalse(result["automatic_promotion"])
        self.assertEqual(self.ledger["governance"], GOVERNANCE)

    def test_negative_control_cannot_be_selected(self):
        self.assertEqual(self.ledger["events"][0]["candidate"], "trial")
        self.assertEqual(self.ledger["events"][0]["phase"], "development")
        self.assertNotEqual(self.ledger["decision"]["selected_candidate"], "trial")
        self.assertTrue(self.ledger["decision"]["negative_control_executed"])

    def test_at_most_one_evaluation_and_two_developments(self):
        events = self.ledger["events"]
        self.assertLessEqual(len(events), 3)
        self.assertEqual(
            [e["candidate"] for e in events if e["phase"] == "development"], CANDIDATES
        )
        self.assertLessEqual(len([e for e in events if e["phase"] == "evaluation"]), 1)
        for item in events:
            self.assertFalse(item["receipt"]["governance"]["automatic_promotion"])

    def test_denied_before_any_run(self):
        with patch("phirsi.discovery._run_one") as mock_run:
            with self.assertRaises(InvalidExperiment):
                run_discovery(self.plan, approved=False)
            mock_run.assert_not_called()

    def test_no_overbudget_or_unknown_candidates(self):
        for change in (
            {"max_n": 12001}, {"cases": 6}, {"rounds": 4},
            {"warmups": 2}, {"max_wall_seconds": 4},
            {"min_dev_speedup": 1.0}, {"min_eval_speedup": float("nan")},
            {"seed": -1},
        ):
            with self.subTest(change=change):
                with self.assertRaises(InvalidExperiment):
                    make_plan(**change)

        forged = deepcopy(self.plan)
        forged["candidates"] = ["trial", "evil-plugin"]
        rehash(forged, "plan_sha256")
        with self.assertRaises(InvalidExperiment):
            validate_plan(forged)

    def test_soft_budget_stops_before_first_measurement(self):
        clock_values = iter([0.0, 31.0, 31.0])
        with patch("phirsi.discovery._run_one") as runner:
            stopped = run_discovery(self.plan, approved=True, clock=lambda: next(clock_values))
            runner.assert_not_called()
        self.assertEqual(stopped["events"], [])
        self.assertEqual(stopped["decision"]["status"], "BUDGET_STOPPED")
        self.assertTrue(verify_discovery(stopped)["passed"])

    def test_chained_hash_detects_event_mutation(self):
        forged = deepcopy(self.ledger)
        forged["events"][0]["candidate"] = "sieve"
        rehash(forged["events"][0], "event_sha256")
        rehash(forged, "ledger_sha256")
        self.assertFalse(verify_discovery(forged)["passed"])

    def test_forged_promotion_is_rejected(self):
        changed = deepcopy(self.ledger)
        changed["governance"]["automatic_promotion"] = True
        rehash(changed, "ledger_sha256")
        self.assertFalse(verify_discovery(changed)["passed"])

    def test_forged_decision_rejected_even_when_rehashed(self):
        changed = deepcopy(self.ledger)
        changed["decision"]["status"] = "CERTIFIED_INTELLIGENCE_UPGRADE"
        rehash(changed, "ledger_sha256")
        self.assertFalse(verify_discovery(changed)["passed"])

    def test_negative_control_cannot_turn_into_evaluation(self):
        bad = deepcopy(self.ledger)
        if len(bad["events"]) == 3:
            bad["events"][2]["candidate"] = "trial"
            rehash(bad["events"][2], "event_sha256")
            rehash(bad, "ledger_sha256")
            self.assertFalse(verify_discovery(bad)["passed"])

    def test_forged_configuration_rejected(self):
        changed = deepcopy(self.ledger)
        changed["events"][0]["receipt"]["experiment"]["seed"] = 1
        rehash(changed["events"][0]["receipt"], "receipt_sha256")
        rehash(changed["events"][0], "event_sha256")
        rehash(changed, "ledger_sha256")
        self.assertFalse(verify_discovery(changed)["passed"])

    def test_evaluation_is_only_after_development_selection(self):
        if len(self.ledger["events"]) == 3:
            self.assertEqual(self.ledger["events"][-1]["phase"], "evaluation")
            self.assertEqual(self.ledger["events"][-1]["candidate"], "sieve")

    def test_cli_plan_run_verify_and_no_overwrite(self):
        with TemporaryDirectory() as temp:
            plan_path = Path(temp) / "plan.json"
            ledger_path = Path(temp) / "ledger.json"
            cmd = [
                "plan", "--max-n", "1000", "--cases", "2", "--rounds", "1",
                "--warmups", "0", "--output", str(plan_path),
            ]
            self.assertEqual(main(cmd), 0)
            self.assertEqual(main(cmd), 2)
            run = ["run", "--plan", str(plan_path), "--output", str(ledger_path)]
            self.assertEqual(main(run), 2)
            self.assertFalse(ledger_path.exists())
            self.assertEqual(main(run + ["--approve-bounded-search"]), 0)
            self.assertEqual(main(run + ["--approve-bounded-search"]), 2)
            self.assertEqual(main(["verify", str(ledger_path)]), 0)
            payload = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertFalse(payload["governance"]["model_weight_changes"])
            self.assertEqual(payload["decision"]["automatic_promotion"], False)


if __name__ == "__main__":
    unittest.main()
