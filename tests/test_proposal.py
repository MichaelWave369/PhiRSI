"""R3 intake and no-authority gates.

Mocked Docker operations validate controller policy, NOT real container isolation.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from phirsi.lab import InvalidExperiment
from phirsi.proposal import (
    execute, inspect, prepare, validate, _docker_create_args, _limits, _parse_guest,
)
from phirsi.proposal_cli import main

IMAGE = "python:3.12-slim@sha256:" + "a" * 64
SOURCE = (
    "def count_primes(limit):\n"
    "    return sum(all(n % d for d in range(2, int(n**0.5)+1)) "
    "for n in range(2, limit+1))\n"
)


class IntakeTests(TestCase):
    def setUp(self):
        self.packet = prepare(
            source=SOURCE, proposal_id="candidate-369",
            hypothesis="A controlled reference candidate",
        )

    def test_review_is_held_no_execution(self):
        self.assertEqual(inspect(self.packet)["status"], "HELD")
        self.assertFalse(inspect(self.packet)["execution_performed"])
        with patch("phirsi.proposal._docker") as docker:
            inspect(self.packet)
            docker.assert_not_called()

    def test_changes_fail_closed(self):
        for field, value in (
            ("source", "def count_primes(limit): return 0\n"),
            ("proposal_id", "../traversal"),
            ("max_n", 900000), ("task", "shell-command"), ("seed", True),
        ):
            with self.subTest(field=field):
                changed = deepcopy(self.packet)
                changed[field] = value
                with self.assertRaises(InvalidExperiment):
                    validate(changed)

    def test_invalid_sources_rejected(self):
        for source in (
            "x", "def count_primes(x):\r\n    return 0\n", "a" * 20001,
        ):
            with self.subTest(length=len(source)):
                with self.assertRaises(InvalidExperiment):
                    prepare(source=source, proposal_id="candidate-369",
                            hypothesis="A controlled experiment")

    def test_no_authority_without_approval(self):
        with patch("phirsi.proposal._docker") as docker:
            with self.assertRaises(InvalidExperiment):
                execute(self.packet, image=IMAGE)
            docker.assert_not_called()

    def test_no_unpinned_image(self):
        with patch("phirsi.proposal._docker") as docker:
            with self.assertRaises(InvalidExperiment):
                execute(self.packet, image="python:3.12-slim", approved=True)
            docker.assert_not_called()

    def test_restrictive_docker_flags(self):
        command = _docker_create_args(name="phirsi-r3-test", root=Path("/tmp/a"), image=IMAGE)
        joined = " ".join(command)
        for required in (
            "--network none", "--read-only", "--cap-drop ALL",
            "--security-opt no-new-privileges", "--pids-limit 16",
            "--memory 256m", "--cpus 1", "--user 65534:65534",
            "--pull never", "readonly", "--log-driver local",
        ):
            self.assertIn(required, joined)
        self.assertNotIn("--privileged", command)
        self.assertNotIn("docker.sock", joined)

    def test_guest_output_checked_against_limits(self):
        limits = [200, 400]
        payload = {"limits": limits, "results": [46, 78], "durations_ns": [300, 400]}
        output = "PHIRSI_RESULT=" + json.dumps(payload)
        self.assertEqual(_parse_guest(output, limits)["results"], [46, 78])
        with self.assertRaises(InvalidExperiment):
            _parse_guest(output, [201, 400])
        with self.assertRaises(InvalidExperiment):
            _parse_guest(output + "\n" + output, limits)

    def test_container_success_only_gives_advisory_verdict(self):
        limits = _limits(self.packet["seed"], self.packet["max_n"], self.packet["cases"])
        from phirsi.algorithms import reference_count
        payload = {
            "limits": limits, "results": [reference_count(n) for n in limits],
            "durations_ns": [300] * len(limits),
        }
        fake = "PHIRSI_RESULT=" + json.dumps(payload) + "\n"
        calls = []

        def mock_docker(args, *, timeout=8):
            calls.append(args)
            if args[0] == "wait":
                return subprocess.CompletedProcess(args, 0, "0\n", "")
            if args[0] == "logs":
                return subprocess.CompletedProcess(args, 0, fake, "")
            return subprocess.CompletedProcess(args, 0, "ok", "")

        with patch("phirsi.proposal.randbits", return_value=0), \
             patch("phirsi.proposal._docker", side_effect=mock_docker):
            receipt = execute(self.packet, image=IMAGE, approved=True)
        self.assertEqual(receipt["outcome"], "advisory_correctness_passed")
        self.assertTrue(receipt["host_reference_verified"])
        self.assertFalse(receipt["timings_independently_verified"])
        self.assertFalse(receipt["automatic_promotion"])
        self.assertIn("rm", [call[0] for call in calls])

    def test_container_wrong_output_remains_failure(self):
        limits = _limits(self.packet["seed"], self.packet["max_n"], self.packet["cases"])
        fake = "PHIRSI_RESULT=" + json.dumps({
            "limits": limits, "results": [0] * len(limits),
            "durations_ns": [10] * len(limits),
        })

        def mock_docker(args, *, timeout=8):
            if args[0] == "wait":
                return subprocess.CompletedProcess(args, 0, "0\n", "")
            if args[0] == "logs":
                return subprocess.CompletedProcess(args, 0, fake, "")
            return subprocess.CompletedProcess(args, 0, "ok", "")

        with patch("phirsi.proposal.randbits", return_value=0), \
             patch("phirsi.proposal._docker", side_effect=mock_docker):
            receipt = execute(self.packet, image=IMAGE, approved=True)
        self.assertEqual(receipt["outcome"], "incorrect_candidate")
        self.assertFalse(receipt["host_reference_verified"])

    def test_cli_draft_review_without_docker(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "candidate.py"
            proposal = folder / "proposal.json"
            source.write_text(SOURCE, encoding="utf-8")
            args = [
                "draft", "--source", str(source), "--id", "candidate-369",
                "--hypothesis", "A controlled reference candidate",
                "--output", str(proposal),
            ]
            with patch("phirsi.proposal._docker") as docker:
                self.assertEqual(main(args), 0)
                self.assertEqual(main(args), 2)
                self.assertEqual(main(["review", "--proposal", str(proposal)]), 0)
                docker.assert_not_called()
