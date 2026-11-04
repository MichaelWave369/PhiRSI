"""R2 tests covering precommitment, negative control and evidence tampering."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from phirsi.lab import InvalidExperiment, digest
from phirsi.study import make_plan, run_study, verify_study, validate_plan
from phirsi.study_cli import main

SMALL = {"max_n": 1500, "cases": 3, "rounds": 2, "warmups": 0}

def rehash(record, field):
    record[field] = digest({k: v for k, v in record.items() if k != field})

class R2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_plan(**SMALL)
        cls.study = run_study(cls.plan)

    def test_registered_plan_roundtrips(self):
        self.assertEqual(validate_plan(self.plan), self.plan)

    def test_plan_seed_is_distinct(self):
        self.assertNotEqual(self.plan["seed_development"], self.plan["seed_evaluation"])

    def test_study_verifies(self):
        outcome = verify_study(self.study)
        self.assertTrue(outcome["passed"], outcome)
        self.assertFalse(outcome["automatic_promotion"])
        self.assertFalse(outcome["timings_independently_reproduced"])
        self.assertFalse(outcome["origin_authenticated"])

    def test_rehashed_plan_substitution_fails(self):
        fake = deepcopy(self.study)
        fake["plan"]["seed_evaluation"] += 1
        rehash(fake["plan"], "plan_sha256")
        rehash(fake, "study_sha256")
        self.assertFalse(verify_study(fake)["passed"])

    def test_tampered_observation_fails_even_rehashed(self):
        fake = deepcopy(self.study)
        run = fake["runs"]["evaluation"]
        run["observations"][0]["candidate"]["counts"][0] = -369
        rehash(run, "receipt_sha256")
        rehash(fake, "study_sha256")
        self.assertFalse(verify_study(fake)["passed"])

    def test_forged_verdict_fails(self):
        fake = deepcopy(self.study)
        fake["assessment"]["status"] = "unconditional_success"
        rehash(fake, "study_sha256")
        self.assertFalse(verify_study(fake)["passed"])

    def test_mismatched_split_configuration_fails(self):
        fake = deepcopy(self.study)
        fake["runs"]["evaluation"]["experiment"]["candidate"] = "trial"
        rehash(fake["runs"]["evaluation"], "receipt_sha256")
        rehash(fake, "study_sha256")
        self.assertFalse(verify_study(fake)["passed"])

    def test_negative_control_is_never_supported(self):
        plan = make_plan(candidate="trial", hypothesis="Trial versus itself is negative control",
                         **SMALL)
        evidence = run_study(plan)
        self.assertEqual(evidence["assessment"]["status"], "negative_control")
        self.assertTrue(verify_study(evidence)["passed"])
        self.assertFalse(evidence["assessment"]["automatic_promotion"])

    def test_high_threshold_is_inconclusive(self):
        plan = make_plan(min_speedup=10.0, **SMALL)
        evidence = run_study(plan)
        self.assertIn(evidence["assessment"]["status"], ("not_supported", "observational_support"))
        self.assertTrue(verify_study(evidence)["passed"])

    def test_reject_invalid_protocol(self):
        for change in ({"cases": 1}, {"seed": -1}, {"candidate": "arbitrary"},
                       {"min_speedup": 1.0}, {"min_speedup": float("nan")},
                       {"min_case_fraction": True}, {"hypothesis": "x"}):
            with self.subTest(change=change):
                with self.assertRaises(InvalidExperiment):
                    make_plan(**change)

    def test_verify_invalid_evidence(self):
        self.assertFalse(verify_study(None)["passed"])
        self.assertFalse(verify_study({})["passed"])

    def test_cli_full_flow_and_refuses_plan_overwrite(self):
        with TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            study = Path(directory) / "study.json"
            args = ["plan", "--output", str(plan), "--max-n", "1500",
                    "--cases", "3", "--rounds", "2", "--warmups", "0"]
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 2)
            self.assertEqual(main(["run", "--plan", str(plan), "--output", str(study)]), 0)
            self.assertEqual(main(["verify", str(study)]), 0)
            self.assertIn("assessment", json.loads(study.read_text(encoding="utf-8")))
            self.assertEqual(main(["run", "--plan", str(plan), "--output", str(study)]), 2)

if __name__ == "__main__":
    unittest.main()
