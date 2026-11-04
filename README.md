# ΦRSI | Recursive Systems Intelligence

**Improve. Verify. Remember. Repeat.**

ΦRSI is an open-source, local-first lab for **measurable AI-systems improvement**. Rung 1 is a reproducible, standard-library-only Python experiment harness. It is **not** an autonomous self-improving model, an AGI claim or an AI coding agent.

## Working Rung 1 experiment

The first workload compares two explicitly registered prime-counting algorithms: odd-number trial division (baseline) and the sieve of Eratosthenes (candidate). A separately structured reference checks correctness. This demonstrates the *measurement infrastructure*, **not improved model intelligence**.

Requirements: Python 3.11+. Install in editable mode and run:

    python -m pip install -e .
    python -m unittest discover -s tests -v
    python -m phirsi run --seed 369 --max-n 20000 --cases 5 --rounds 5 --output receipt.json
    python -m phirsi verify receipt.json

Omit --output to print the JSON receipt to stdout. Optionally use --candidate trial to compare the baseline with itself.

The run records timing samples in nanoseconds, median/p95 measurements, correctness, environment, seeded inputs, file fingerprints and a geometric-mean **observed** speedup. The verifier reconstructs inputs, validates consistency and replays correctness against the current local code. It **does not** independently reproduce past timings, authenticate their origin or certify scientific significance.

## R1 boundaries

- Allowlisted algorithms only. No arbitrary downloaded code, dynamic plugins, network calls or shell execution.
- Strict limits: maximum input from 1,000 to 100,000; 2–10 cases; 1–10 measured rounds; 0–3 warmups.
- Every receipt explicitly prohibits automatic promotion and requires human approval.
- Receipt SHA-256 is an **unkeyed checksum**, not a signature. Source fingerprints do not prove author identity.
- Local speedup is sensitive to CPU load and environment. Repetition and independent replication are required before drawing strong conclusions.
- GitHub Actions unit tests and smoke benchmark are software checks, not external scientific verification.

## Rung 2: precommitted two-split evaluation

R2 adds a study-plan format, deterministic development/evaluation splits, explicit acceptance thresholds, a **same-algorithm negative control**, and a study verifier. The R1 CLI remains unchanged.

    mkdir -p artifacts
    python -m phirsi.study_cli plan --candidate sieve --hypothesis "Sieve improves prime counting over trial division" --output artifacts/plan.json
    # Commit and timestamp the plan before reviewing any evaluation data.
    python -m phirsi.study_cli run --plan artifacts/plan.json --output artifacts/study.json
    python -m phirsi.study_cli verify artifacts/study.json

Possible results: `observational_support`, `not_supported` or `negative_control`. **No result grants deployment authority.** The split is precommitted but not secret; the tool cannot authenticate when a plan was written or independently reproduce historical timing. See [R2 Protocol](docs/R2_PROTOCOL.md).

## Rung 3: bounded AI-code proposal intake

R3 introduces an **inert proposal packet**, an independent host-reference check, and an **explicitly approved Docker-only probe** for one known prime-counting task. The default action never executes the proposed source. CI deliberately mocks Docker rather than running untrusted code.

    python -m phirsi.proposal_cli draft --source examples/sieve_candidate.py --id candidate-sieve-369 --hypothesis "Investigate candidate prime counting" --output r3-proposal.json
    python -m phirsi.proposal_cli review --proposal r3-proposal.json

The review returns **HELD**. Optional operator-authorized live execution requires a securely configured Docker host and an explicitly pinned, locally installed Python container image; it does not occur automatically. See [R3 protocol and exact trust boundaries](docs/R3_PROTOCOL.md).

No benchmark gain, container-security proof, authenticated authorship, permission elevation, or deployment authority is claimed. The project is still a research harness, not a recursive self-improving AI.

## Φ369 ecosystem roadmap

**Agentora** may later propose and orchestrate experiments. **PhiServe** may supply actual model-serving benchmarks. **PhiOS** will handle permission and verification boundaries. **CompAware** can contribute adversarial controls. **PhiMadaPrime** can visualize read-only results. None of those integrations is active or required in R1, R2 or R3.

Research foundations: [Charter](docs/CHARTER.md), [Receipt contract](docs/RECEIPT_V1.md), [Roadmap](docs/ROADMAP.md).

**Capability is not authority. Observation is not proof. Measurable improvement beats hype.**

MIT licensed, see LICENSE.
