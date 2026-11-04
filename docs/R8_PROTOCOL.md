# Rung 8 | Controlled, Opt-in Local PhiServe Model A/B

**Purpose:** compare two already-registered PhiServe model aliases on identical public toy tasks, with an explicitly authorized local operator and recorded evidence. R8 is not a generalized model-quality leaderboard or recursive self-improvement.

## Requirements and authority

- Python 3.11+ and this exact PhiRSI revision.
- An operator-controlled, already-running PhiServe instance on 127.0.0.1 (default port 11435) with TWO registered aliases.
- Existing PhiServe model weights; no model download, installation or automatic model changes by PhiRSI.
- Explicit --approve-local-inference to send any completion POST. Planning and offline verification do not access the server.
- No secrets in CLI arguments. If PhiServe requires a local bearer token, set PHIRSI_PHISERVE_TOKEN through a secure local environment mechanism. Never commit, publish or log it.

The Python R4 transport is reused: only direct GET /health, GET /v1/models and POST /v1/chat/completions on literal 127.0.0.1. No arbitrary URLs, remote hosts, proxies, redirects or DNS. A preflight checks both registered model aliases before inference.

## End-to-end local commands

Install and run the full tests:

    python -m pip install -e .
    python -m unittest discover -s tests -v
    mkdir -p artifacts

Choose two aliases from your ACTUAL local PhiServe catalog. The names below are placeholders:

    python -m phirsi.phiserve_cli doctor --model YOUR_FIRST_ALIAS

Create the R8 plan:

    python -m phirsi.model_pair_cli plan --model-a YOUR_FIRST_ALIAS --model-b YOUR_SECOND_ALIAS --rounds 1 --max-tokens 32 --timeout-seconds 30 --output artifacts/model-pair-plan.json

Review and commit the plan before viewing results if preregistration matters. A local checksum does not authenticate timestamps or establish trusted preregistration.

Run with explicit approval:

    python -m phirsi.model_pair_cli run --plan artifacts/model-pair-plan.json --approve-local-inference --output artifacts/model-pair-receipt.json

Check it offline:

    python -m phirsi.model_pair_cli verify artifacts/model-pair-receipt.json

Produce a summary suitable for the read-only public site:

    python -m phirsi.model_pair_cli summary artifacts/model-pair-receipt.json --output artifacts/model-pair-summary.json

Open PhiRSI Live Lab, navigate to the Model A/B section, and choose the summary JSON. The React site does not call your PhiServe daemon, send prompts, store credentials or upload the file.

## Fixed experiment design

- Three public R4 tasks: uppercase conversion, simple arithmetic and alphabetical sorting, with exact expected replies.
- One or two rounds; exactly 3 cases x 2 models x rounds, so 6–12 completion requests.
- Same prompt, seed, temperature 0, token cap and timeout for each comparison.
- A/B then B/A order alternates across cases and rounds. This reduces but does not eliminate order, model-loading, thermal or cache bias.
- Responses compared to expected answers. Only response SHA-256, exact-match boolean, provider-reported completion tokens (if present), and measured end-to-end HTTP latency are retained.
- No raw prompts, generated answers or bearer tokens are written to the R8 receipt.
- Unkeyed SHA-256 checksums detect accidental mutation. They are not signatures.

Resource bounds: 1–2 rounds, max 8–64 output tokens per request, 5–60-second timeout per request, 96 KB response limit through R4. This is not a global hard time budget. Model-switch/loading may dominate first-call timing.

## How to read metrics

The report gives per-alias exact-match count/fraction, median/p95 end-to-end request latency and optional provider-reported tokens divided by total HTTP time. That is NOT pure decoding throughput. Time-to-first-token is not measured.

Each A/B prompt/round pair gets an observed A-over-B latency ratio (above 1 means B happened to respond faster). The comparison records counts of faster A, faster B and ties, plus a descriptive median.

The decision is ALWAYS DESCRIPTIVE_ONLY_NO_WINNER, regardless of results. It does not establish a model's intelligence, unseen task quality, preferred deployment setting or autonomous self-improvement.

No GPU utilization, VRAM, energy consumption or model weight fingerprints are measured. Two aliases might even refer to identical weights. Repeated calls on one host do not establish independent replication.

## Trust and evidence

- phirsi.phiserve_pair_plan.v1: recorded plan.
- phirsi.phiserve_pair_receipt.v1: full observed timing records, hashes, derived metrics and governance.
- phirsi.phiserve_pair_summary.v1: small web preview, exported from a locally verified receipt.
- Offline verify detects malformed rows, wrong order, impossible exact-match claims, changed configuration, inconsistent aggregates and permissive governance. It CANNOT reconstruct historical model execution or timestamps.
- The browser inspects selected summary shapes and counts only. It cannot independently verify source receipts or historical performance.
- Anyone can fabricate plausible timing data and recompute unkeyed hashes. A verifier PASS means internal consistency, not authenticated model execution.

## CI versus hardware acceptance

GitHub CI tests a **fake PhiServe HTTP server** on loopback, with canned replies. It does not load actual GGUF weights or run on your PC/GPU. A green workflow proves only the software contract with the fixture.

Real field validation requires manually running these commands on a machine with PhiServe, recording model hashes independently, and reviewing cold/warm-start effects. Keep evidence private and inspect it for identifying metadata before publication.

No automatic promotions, PhiOS permissions, Agentora mission launches, model deployments or arbitrary code execution.
