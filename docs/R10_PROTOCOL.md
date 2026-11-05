# Rung 10 | Local workstation repeat-run acceptance dossier

## Purpose

R10 allows an operator to predeclare a tiny, inspectable stability policy and compare **three to six existing R9 inference receipts**. It preserves the original receipts in a local JSON dossier, uses the R9 verifier to check every included source, computes repeat-run latency and fixed-task quality metrics, and exports a small summary for the static React Live Lab.

R10 **does not run inference, query GPUs or networks, load models, modify any weights, or authorize deployment**. That work is performed separately via explicitly approved R9 runs on an operator's workstation.

## Experimental design

An acceptance plan fixes:
- PhiServe model aliases A and B, loopback port, rounds, token and timeout bounds.
- The public 12-task R9 dataset fingerprint and exact R9 source-code fingerprint.
- Consecutive R9 seeds beginning at first_seed. Default: 369, 370, 371.
- Quality floor for **every model in every run**. Default 75% exact match on the 12 known public tasks.
- Maximum spread of repeat-run median HTTP latency, evaluated for A and B separately as highest repeat-run median / lowest repeat-run median. Default 2.0.

The first run is labeled initial; every later run is labeled repeat. These are **operator order labels only**. They do not establish cold-start measurements or a genuinely warmed cache. In particular, the current R9 paired benchmark can cause PhiServe to switch models frequently, and the model startup/switching overhead may dominate timings.

Thresholds yield either MEETS_CONFIGURED_THRESHOLDS or DOES_NOT_MEET_CONFIGURED_THRESHOLDS. Both outcomes require human review. Neither outcome means a machine passed a validated readiness certification.

## Run on a local machine

Prerequisites: Python 3.11+, local PhiServe daemon running with two registered aliases, and PhiRSI installed from this same version. Choose two models suitable for your local hardware.

Install and prepare a private folder:

    python -m pip install -e .
    python -m unittest discover -s tests -v
    mkdir artifacts

Freeze the acceptance criteria **before** R9 measurements:

    python -m phirsi.workstation_cli plan --model-a MODEL_A --model-b MODEL_B --first-seed 369 --run-count 3 --quality-floor 0.75 --max-repeat-median-latency-spread 2.0 --max-tokens 32 --rounds 1 --timeout-seconds 30 --output artifacts/r10-plan.json

Use the exact same model aliases, port, token limit, rounds, and timeout for the R9 plans. Record different seeds, one at a time:

    python -m phirsi.field_cli plan --model-a MODEL_A --model-b MODEL_B --seed 369 --rounds 1 --max-tokens 32 --timeout-seconds 30 --output artifacts/r9-plan-369.json
    python -m phirsi.field_cli run --plan artifacts/r9-plan-369.json --approve-local-inference --output artifacts/r9-run-369.json

    python -m phirsi.field_cli plan --model-a MODEL_A --model-b MODEL_B --seed 370 --rounds 1 --max-tokens 32 --timeout-seconds 30 --output artifacts/r9-plan-370.json
    python -m phirsi.field_cli run --plan artifacts/r9-plan-370.json --approve-local-inference --output artifacts/r9-run-370.json

    python -m phirsi.field_cli plan --model-a MODEL_A --model-b MODEL_B --seed 371 --rounds 1 --max-tokens 32 --timeout-seconds 30 --output artifacts/r9-plan-371.json
    python -m phirsi.field_cli run --plan artifacts/r9-plan-371.json --approve-local-inference --output artifacts/r9-run-371.json

R9's loopback inference requires separate, explicit approval for each run. R10 does not send any POST or GET. The R9 runs contain 24 model requests each, or 72 for this example. Multiple model switches can be expensive; do not assume a stable warm cache.

Pack **all** original R9 receipts in seed order:

    python -m phirsi.workstation_cli pack --plan artifacts/r10-plan.json --receipt artifacts/r9-run-369.json --receipt artifacts/r9-run-370.json --receipt artifacts/r9-run-371.json --output artifacts/r10-dossier.json

Check the complete dossier, including every original R9 receipt, without inference:

    python -m phirsi.workstation_cli verify artifacts/r10-dossier.json

Export the summary-only browser review:

    python -m phirsi.workstation_cli summary artifacts/r10-dossier.json --output artifacts/r10-summary.json

Then open the Workstation Acceptance section of PhiRSI Live Lab and select r10-summary.json. The static site does not access PhiServe or upload the file.

## Binding and failure handling

The offline dossier validator refuses:
- Fewer than 3 or more than 6 receipts; changed or repeated seeds; duplicate source receipts.
- Different model aliases, R9 code version, dataset, port, timeout, token cap or rounds.
- Source records not passing the original R9 verifier.
- Partially supplied GGUF hashes when a model has a hash in any run, or inconsistent hashes across runs. These are operator-selected file hashes, **not served-weight attestation**.
- An assessment inconsistent with original per-run results or the predeclared policy.
- Any alteration granting deployment, automatic model promotion, independently authenticated hardware, or cold/warm attestation.

The dossier preserves failed and low-scoring runs rather than discarding them. It never overwrites previous outputs. The summary omits original per-request response hashes and timing observations.

## Evidence limitations

- Identical aliases and operator-selected GGUF file hashes do not independently prove which weights PhiServe served.
- Individual R9 receipt timestamps, runtime latencies and sample origin are unsigned, operator-provided observations. Unkeyed SHA-256 checksums can be recomputed and do not authenticate chronology.
- This is repeated observation on an unknown host, not necessarily independent scientific replication. The presence of a filename or GPU driver report is not physical hardware proof.
- No direct CUDA or VRAM measurement occurs in R10. Optional R9 PhiServe field-run driver memory evidence is from a **separate experiment**, not correlated to the acceptance dossier request stream.
- The public 12 fixed tasks are simplistic. A 75% threshold is a chosen research policy, **not an industry standard or a measure of general intelligence**.
- No statistical confidence interval or significance claim is derived. OS state, RAM availability, model switches, GPU contention and thermal differences can distort latency.
- Results may say the predefined thresholds were met, but **do not authorize shipping a model or changing production software**.

## CI and test limits

GitHub CI creates three R9 receipts from a **mock local PhiServe reply function**, then exercises R10's complete acceptance packaging, validation, failure, tampering and CLI path. GitHub Actions does not access any user's workstation or actual model weights. Frontend tests verify only the browser summary parser and React production build.

**Improve. Verify. Remember. Repeat.**
