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

## Rung 4: local PhiServe inference measurements

R4 adds a **read-only preflight and explicitly approved non-streaming inference benchmark** against an already-running PhiServe server on 127.0.0.1 (default port 11435). It does not download models, manage PhiServe, contact the internet or start inference on GitHub CI. The model must already be registered locally.

    python -m phirsi.phiserve_cli doctor --model qwen3:4b
    # Review the bounded experiment first; use your real registered model alias.
    mkdir -p artifacts
    python -m phirsi.phiserve_cli run --model qwen3:4b --approve-local-inference --output artifacts/r4.json
    python -m phirsi.phiserve_cli verify artifacts/r4.json

The three public, deterministic toy prompts produce only a **narrow exact-match fraction**, local end-to-end HTTP latency, and throughput calculated **only when the provider reports completion tokens**. No prompts, model text, or bearer credentials are saved; response hashes are recorded instead. **VRAM, power and TTFT are not measured**; no model-intelligence gain or independent replication is claimed.

CI uses a fake loopback HTTP server, **not** a real PhiServe process or GGUF weights. For the operating protocol, local bearer-token guidance and exact limitations see [R4 Protocol](docs/R4_PROTOCOL.md).

## Rung 5: Φ Ecosystem Handoff (review-only)

R5 consolidates R1/R2/R3/R4 evidence into a small **zero-authority, source-bound review packet**. It validates the original evidence using the existing rung validators and explicitly forbids auto-execution, mission dispatch, merge, deployment, and writeback.

    python -m phirsi.ecosystem_cli prepare --kind r2 --source artifacts/study.json --output artifacts/review-handoff.json
    python -m phirsi.ecosystem_cli verify --kind r2 --source artifacts/study.json --handoff artifacts/review-handoff.json

One **real GET-only integration** is included: check an already-running Agentora service at its local address.

    python -m phirsi.ecosystem_cli agentora-doctor --port 8088

**Important:** Agentora mission dispatch, PhiOS ledger ingestion, PhiMadaPrime visualization, and CompAware scientific review are *not wired yet*. They are documented offline review targets, not active integrations. The handoff never includes original source code, raw prompts, completion text, tokens, or credentials. It is not authenticated independent evidence.

See [R5 handoff protocol](docs/R5_PROTOCOL.md) for schema, scope, test coverage and limitations.

## ΦRSI Live Lab (React research website)

A responsive, public-facing React site is now included under [web/](web/). It features an interactive R1–R7 research roadmap, a **real bounded prime-count comparison running entirely inside your browser**, and a **local-only R5 evidence-handoff shape inspector**. The browser demo is not a Python experiment receipt or model benchmark, and the inspector does not authenticate evidence. The website never runs a model, opens a privileged Agentora/PhiOS connection, or grants merge/deployment authority.

After the separate site workflow passes on main and GitHub Pages is configured for **GitHub Actions** publication, the target is [PhiRSI Live Lab](https://michaelwave369.github.io/PhiRSI/). That address is **not proof of deployment** until GitHub Pages confirms the deployment and a browser test succeeds.

To run locally:

    cd web
    npm install
    npm test
    npm run dev
    npm run build

For scope, expected behavior and post-deployment checks, see [Live Lab contract](docs/LIVE_SITE_R1.md) and [web README](web/README.md).

## Rung 6: bounded iterative discovery and ledger

R6 introduces an **explicitly approved, bounded algorithm-selection loop** with a mandatory negative control, a fixed reviewed candidate shortlist, a development-only selection gate, at-most-once evaluation on distinct seeded inputs and hash-chained research evidence. It is **not** an autonomous AI-writing or self-improving model.

    mkdir -p artifacts
    python -m phirsi.discovery_cli plan --max-n 5000 --cases 3 --rounds 2 --output artifacts/r6-plan.json
    # Review/commit the plan before using its evaluation results.
    python -m phirsi.discovery_cli run --plan artifacts/r6-plan.json --approve-bounded-search --output artifacts/r6-ledger.json
    python -m phirsi.discovery_cli verify artifacts/r6-ledger.json

The ledger always records no automatic promotion, no model-weight changes and human review. Existing R1–R5 commands remain unchanged. The new [R6 research protocol](docs/R6_PROTOCOL.md) explains the soft budget, non-secret evaluation split, experimental biases and lack of independent timing authentication.

The React Live Lab now includes a **local JSON Discovery Ledger timeline**. It displays the reported observations without uploading them, but cannot independently authenticate the receipt or replay Python correctness. It is not a network-connected research dispatcher.
## Rung 7: open comparison and reproducible research packets

R7 creates bounded, independently **checkable** research packets from **2–6 distinct-seed R6 ledgers** with the same experiment design. It validates each original R6 receipt, preserves negative and budget-stopped results, checks source comparability, stores original evidence in a safe ZIP, and exports a compact review-only manifest for the React Live Lab.

    python -m phirsi.replication_cli pack --ledger artifacts/ledger-369.json --ledger artifacts/ledger-370.json --output artifacts/r7-packet.zip
    python -m phirsi.replication_cli verify artifacts/r7-packet.zip
    python -m phirsi.replication_cli summary artifacts/r7-packet.zip --output artifacts/r7-summary.json

**Distinct input seeds do not prove independent laboratories.** Neither the Python verifier nor React viewer can authenticate past timings, hardware, experimenter or external provenance. No confidence interval, statistical significance, model intelligence improvement, or authority to promote is claimed. The ZIP retains its original experiment receipts. Review the packet for sensitive metadata before deciding to share it.

See [R7 Protocol](docs/R7_PROTOCOL.md) for a complete two-run example, export format, safe bounds and independent-replication requirements. On the public site, the Open Replication desk reads a summary locally without uploading it or verifying its original source.
## Rung 8: controlled, real-model local A/B comparisons

R8 adds an explicitly authorized, loopback-only **paired PhiServe model experiment** for two already registered aliases. Across the same three public toy questions it alternates A/B and B/A order, measures request latency and exact-match results, and records answer **hashes rather than generated texts**.

    python -m phirsi.model_pair_cli plan --model-a YOUR_FIRST_ALIAS --model-b YOUR_SECOND_ALIAS --rounds 1 --output artifacts/r8-plan.json
    python -m phirsi.model_pair_cli run --plan artifacts/r8-plan.json --approve-local-inference --output artifacts/r8-receipt.json
    python -m phirsi.model_pair_cli verify artifacts/r8-receipt.json
    python -m phirsi.model_pair_cli summary artifacts/r8-receipt.json --output artifacts/r8-summary.json

Run those commands only on a computer where PhiServe is already serving the selected local models. **GitHub CI uses a fake loopback server; no real local model validation or GPU measurement is claimed.** There are no downloads, automated upgrades, external network calls, raw response texts or bearer credentials in the receipts.

R8 reports descriptive timing and toy-task exact-match numbers but **never declares a general intelligence winner**. It does not attest model weights, independent timing, VRAM, TTFT or statistical significance. React's new Model A/B desk reads the exported summary locally and does not connect to PhiServe or verify historical model execution.

See [R8 Protocol](docs/R8_PROTOCOL.md) for exact limits and real-hardware field steps.
## Rung 9: expanded local model evaluation and separate hardware evidence

R9 adds a 12-task, fixed public evaluation across two registered local PhiServe aliases, using alternate request order and explicitly approved loopback-only inference. It optionally fingerprints operator-selected local GGUF files and attaches **separate** PhiServe GPU process-memory observations. Neither fingerprint nor memory observation proves which model weights executed.

    python -m phirsi.field_cli plan --model-a YOUR_FIRST_ALIAS --model-b YOUR_SECOND_ALIAS --output artifacts/r9-plan.json
    python -m phirsi.field_cli run --plan artifacts/r9-plan.json --approve-local-inference --output artifacts/r9-receipt.json
    python -m phirsi.field_cli verify artifacts/r9-receipt.json
    python -m phirsi.field_cli summary artifacts/r9-receipt.json --output artifacts/r9-summary.json

The React Live Lab Hardware desk accepts the exported summary locally, with no upload and no model API calls. CI uses fake model replies and synthetic GGUF files, not your hardware. All measurements remain descriptive, internally checkable and review-only. [Read the R9 protocol](docs/R9_PROTOCOL.md).
## Rung 10: repeat-run workstation acceptance dossier

R10 packages **3–6 original R9 field receipts** into a single offline review dossier. A predeclared plan binds both model aliases, consecutive seeds, versioned public tasks, R9 source revision, toy-task accuracy floor and repeat-run latency spread limit. Each source receipt is rechecked by its original validator. Negative or unstable results are preserved, not dropped.

    python -m phirsi.workstation_cli plan --model-a YOUR_FIRST_ALIAS --model-b YOUR_SECOND_ALIAS --run-count 3 --quality-floor 0.75 --max-repeat-median-latency-spread 2.0 --output artifacts/r10-plan.json
    # Run the matching R9 plans with seeds 369, 370 and 371 locally and explicitly.
    python -m phirsi.workstation_cli pack --plan artifacts/r10-plan.json --receipt artifacts/r9-run-369.json --receipt artifacts/r9-run-370.json --receipt artifacts/r9-run-371.json --output artifacts/r10-dossier.json
    python -m phirsi.workstation_cli verify artifacts/r10-dossier.json
    python -m phirsi.workstation_cli summary artifacts/r10-dossier.json --output artifacts/r10-summary.json

R10 itself performs **no model inference or GPU access**. Its React Acceptance Desk reads only the reduced JSON summary locally. Meeting these toy-task thresholds does NOT authenticate machine identity, historical timings, model weights, cold/warm behavior or readiness to deploy. CI uses fake PhiServe replies, not real hardware.

See [R10 Protocol](docs/R10_PROTOCOL.md) for the complete R9 operator commands, known confounds and permission boundaries.
## Φ369 ecosystem roadmap

**Agentora** may later propose and orchestrate experiments. **PhiServe** may supply actual model-serving benchmarks. **PhiOS** will handle permission and verification boundaries. **CompAware** can contribute adversarial controls. **PhiMadaPrime** can visualize read-only results. R4 implements an opt-in PhiServe benchmark. R5 adds an offline governance handoff and a GET-only local Agentora health/version preflight; active Agentora orchestration and direct PhiOS, CompAware, and PhiMadaPrime integration remain future work.

Research foundations: [Charter](docs/CHARTER.md), [Receipt contract](docs/RECEIPT_V1.md), [Roadmap](docs/ROADMAP.md).

**Capability is not authority. Observation is not proof. Measurable improvement beats hype.**

MIT licensed, see LICENSE.
