"""Tests: correctness, determinism, fail-closed evidence and permissions."""
from copy import deepcopy
import unittest
from phirsi.algorithms import trial_count, sieve_count, reference_count
from phirsi.lab import InvalidExperiment, digest, make_limits, run_experiment, verify_receipt

class AlgorithmTests(unittest.TestCase):
    def test_known_counts(self):
        for n, expected in [(0, 0), (1, 0), (2, 1), (10, 4), (100, 25), (1000, 168)]:
            with self.subTest(n=n):
                for f in (trial_count, sieve_count, reference_count):
                    self.assertEqual(f(n), expected)

    def test_seeded_cases(self):
        self.assertEqual(make_limits(369, 1000, 3), make_limits(369, 1000, 3))
        self.assertNotEqual(make_limits(369, 1000, 3), make_limits(370, 1000, 3))

    def test_limits_fail_closed(self):
        for options in ({"max_n": 999}, {"max_n": 100001}, {"cases": 1},
                        {"cases": 11}, {"rounds": 0}, {"rounds": 11},
                        {"warmups": 4}, {"seed": -1}, {"seed": True}):
            with self.subTest(options=options):
                with self.assertRaises(InvalidExperiment):
                    run_experiment(**options)

    def test_unregistered_candidate(self):
        with self.assertRaises(InvalidExperiment):
            run_experiment(candidate="external-python")

class ReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = run_experiment(max_n=1500, cases=3, rounds=2, warmups=0)

    def test_verify_real_run(self):
        result = verify_receipt(self.receipt)
        self.assertTrue(result["passed"], result)
        self.assertFalse(result["timings_reproduced"])
        self.assertFalse(result["origin_authenticated"])

    def test_checksum_tampering(self):
        copy = deepcopy(self.receipt)
        copy["observations"][0]["candidate"]["counts"][0] = -1
        self.assertFalse(verify_receipt(copy)["passed"])

    def test_rehashed_false_claim(self):
        copy = deepcopy(self.receipt)
        copy["observations"][0]["candidate"]["counts"][0] = -1
        copy["receipt_sha256"] = digest({k:v for k,v in copy.items() if k != "receipt_sha256"})
        self.assertFalse(verify_receipt(copy)["passed"])

    def test_rehashed_governance_claim(self):
        copy = deepcopy(self.receipt)
        copy["governance"]["automatic_promotion"] = True
        copy["receipt_sha256"] = digest({k:v for k,v in copy.items() if k != "receipt_sha256"})
        self.assertFalse(verify_receipt(copy)["passed"])

    def test_baseline_as_candidate(self):
        receipt = run_experiment(candidate="trial", max_n=1000, cases=2, rounds=1, warmups=0)
        self.assertTrue(verify_receipt(receipt)["passed"])

    def test_bad_input(self):
        self.assertFalse(verify_receipt(None)["passed"])
        self.assertFalse(verify_receipt({})["passed"])

if __name__ == "__main__":
    unittest.main()
