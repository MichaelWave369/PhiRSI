# Rung 9 | Expanded local field evaluation and hardware-evidence dossier

**Status:** R9 is an opt-in local research workflow, not an intelligence benchmark, model attestation, or certified hardware test. CI uses fake PhiServe replies, not real model weights.

## Included

- 12 public fixed tasks spanning text transforms, arithmetic, ordering, extraction, and literal instruction-following. This is a deterministic smoke test, not a robust general-quality evaluation or secret holdout.
- Two distinct registered PhiServe aliases on 127.0.0.1. One or two rounds of 12 tasks per model (24-48 POSTs total), with alternating A/B order and existing R4 bounds: 5-60-second request timeout, 8-64 output tokens, 96KB maximum reply.
- Per-request answer hash, exact-match, full HTTP latency and optional provider-reported completion tokens. No raw generated responses, input prompts or bearer tokens in evidence.
- Optional operator-selected GGUF fingerprint, streamed SHA-256 up to 64 GiB, with GGUF header and change-during-read check. This does not prove the server loaded that GGUF file.
- Optional separate PhiServe acceptance field-run receipt, projecting driver-reported memory for its own child process if available. It is **not from the same inference** as the R9 comparison and is never described as independent GPU execution proof.
- Review-only browser JSON summary. The React frontend verifies shape only, not source evidence.

## Run locally (Windows 11 example)

First, run an existing local PhiServe daemon with two registered model aliases, then install PhiRSI at this checkout:

    python -m pip install -e .
    python -m unittest discover -s tests -v
    mkdir artifacts

Choose actual registered PhiServe aliases and record a plan:

    python -m phirsi.field_cli plan --model-a YOUR_FIRST_ALIAS --model-b YOUR_SECOND_ALIAS --rounds 1 --max-tokens 32 --timeout-seconds 30 --output artifacts/r9-plan.json

Review the plan and preserve an externally trusted timestamp if preregistration matters. Then explicitly approve local inference:

    python -m phirsi.field_cli run --plan artifacts/r9-plan.json --approve-local-inference --output artifacts/r9-receipt.json

Optional: add --model-a-gguf and --model-b-gguf with full local GGUF file paths to the run command. Model files are read and hashed, never edited, but the resulting fingerprints cannot bind the files to PhiServe's loaded weights.

Optional: in PhiServe, run its separate acceptance field-run command per model alias with the --sample-nvidia and --gpu-layers options, saving private receipts. Pass those files to the R9 run command as --field-a-receipt and --field-b-receipt. Those PhiServe samples come from a **separate operator-run child process**, not the R9 request stream. Windows WDDM may report memory N/A.

Check the R9 receipt offline and export a local-only web summary:

    python -m phirsi.field_cli verify artifacts/r9-receipt.json
    python -m phirsi.field_cli summary artifacts/r9-receipt.json --output artifacts/r9-summary.json

Import that JSON in the Hardware section of PhiRSI Live Lab. No browser uploads or model API requests occur.

If PhiServe requires a bearer token, use PHIRSI_PHISERVE_TOKEN in a trusted local environment, never GitHub, screenshots, CLI arguments or logs.

## Boundaries

- No independent model execution or weight identity attestation, no authenticated historical timings, no CUDA proof, no direct GPU telemetry during the R9 benchmark, and no formal significance or confidence intervals.
- Two aliases may point to the same weights. Selection bias, model switches, caching, thermal throttling and concurrent workloads may affect timings.
- Driver process memory is a self-report from a separate experiment. GPU memory can be unavailable, especially under Windows WDDM.
- GGUF SHA-256 identifies an operator-selected local file; it does not prove that the server loaded the file.
- No hard overall wall-clock budget. Only individual request timeouts.
- Fixed public questions cannot establish general model intelligence or safety.
- Receipt checksums are unkeyed and forgeable. Verification replays arithmetic and shape constraints, not historical model execution.
- Always review-only: no model changes, promotion, deployment, Github merges, Agentora mission launch or PhiOS permission changes.

## CI

R9 CI executes full Python regression tests against fake local PhiServe replies, synthetic GGUF files, tampered evidence and no-authority guards. Static React logic tests and build are run separately by the website workflow. **No real GGUF model** or physical GPU runs in CI.

**Improve. Verify. Remember. Repeat.**
