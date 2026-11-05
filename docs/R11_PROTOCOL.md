# Rung 11 | Block-ordered PhiServe first-vs-repeat request isolation

**Status: operator-approved local software measurement, not authenticated model loading or genuine cold/warm isolation.**

R11 tackles an experimental confound from R8/R9: rapidly alternating between aliases can mix first-request overhead, runtime caching, model switching, task differences and ordinary request latency.

R11 compares **the same fixed public prompt** for an initial request and two or three immediate follow-up requests within the same alias block. Four blocks alternate the **requested model alias**, while two separate public tasks are used for different rounds. The results distinguish *observed first-request latency* from *observed repeated-request latency*, **not backend model loading time**.

## Actual bounded protocol

- Two **distinct, already-registered** PhiServe aliases. The operator must have a compatible local PhiServe server running at literal 127.0.0.1, default port 11435.
- A fixed schedule: two rounds, each containing two model blocks. The default is A/B/A/B; --first-role B selects B/A/B/A.
- Each block contains one **first_request** and either two or three **repeat_request** POSTs with the **same prompt** and same inference options. The default is 4 blocks x 3 requests = **12 requests**; maximum **16 requests**.
- Round 1 uses the public R9 uppercase toy task (ORBIT). Round 2 uses public simple arithmetic (37 + 58 = 95). Cases are not secret or comprehensive model-quality tests.
- Default max 32 generated tokens (allowed 8–64), per-request timeout 30 seconds (allowed 5–60), temperature 0, non-streaming, one fixed seed. The existing R4 direct loopback HTTP client enforces a 96 KB JSON response limit and prevents user-supplied remote URLs/proxies.
- Each request record retains the requested alias, block number, phase, per-block sequence, the *previous requested alias*, whether a different alias was requested at the block boundary, exact-match boolean, answer SHA-256, provider token count if supplied, and **full end-to-end HTTP request time**.
- Aggregate reports show first/repeat HTTP medians per model and within-block first-over-repeat ratio. Timing medians include all network, backend startup/load (if any), prompt processing, generation, JSON serialization and loopback overhead.
- No raw model outputs, prompt text, bearer credentials, source file paths, live model configuration or GPU telemetry are stored.

## Operator workflow

From the checked-out PhiRSI repository on a PC already running PhiServe:

    python -m pip install -e .
    python -m unittest discover -s tests -v
    mkdir artifacts

Record a plan before looking at outcomes (replace these placeholders with your actual PhiServe aliases):

    python -m phirsi.switch_cli plan --model-a YOUR_MODEL_A --model-b YOUR_MODEL_B --first-role A --repeat-requests 2 --max-tokens 32 --timeout-seconds 30 --output artifacts/r11-plan.json

If true preregistration matters, commit the plan and retain a trusted external timestamp. A local checksum does not prove creation time.

Explicitly authorize this local run:

    python -m phirsi.switch_cli run --plan artifacts/r11-plan.json --approve-local-inference --output artifacts/r11-receipt.json

Offline consistency verification (no inference/network):

    python -m phirsi.switch_cli verify artifacts/r11-receipt.json

Export a small **read-only, shape-only** React summary:

    python -m phirsi.switch_cli summary artifacts/r11-receipt.json --output artifacts/r11-summary.json

Open the static PhiRSI Live Lab and choose the local summary file in the **Isolation** section. The page does not send requests to local PhiServe or upload the selected JSON.

If your PhiServe daemon is password-protected, store the token in the local PHIRSI_PHISERVE_TOKEN environment variable only. No bearer tokens are accepted as CLI arguments or written to the receipt.

## Two useful controlled runs

The R11 plan has --first-role A or B. Comparing separate A/B/A/B and B/A/B/A plans may help explore global request-order effects, but those runs **are not automatically combined or statistically analyzed**. Each run independently needs operator approval.

Ensure your hardware has enough resources to load the selected models. R11 does not install models, purge caches, unload or restart the backend, clear VRAM, pin clocks, isolate background workloads, or control thermals.

## Critical interpretation rules

- The first **block** may begin while an arbitrary model is already resident. The requested_alias_changed flag is false in that first block because PhiRSI has no trusted record of the daemon's prior state.
- In later blocks a *requested alias change* means only that the client sent a different model identifier from the previous request. The server may reuse the same model weights, retain multiple weights, ignore an alias in its internals or serve from cache. A changed alias is **not an observed unload, reload, allocation or CUDA kernel event**.
- A first-request delay may include real model loading, prompt prefill, HTTP timing, device contention, caching, context initialization and application overhead. No instrumentation here isolates one factor.
- Repeated requests might still initiate lazy or asynchronous loading, or be accelerated by response caches. R11 cannot certify a warm cache or compare true cold-start time.
- Same-prompt repetition reduces prompt variability within blocks but can introduce prompt- or KV-cache biases, so a lower repeat median is **not proof of reduced decoding cost**.
- No time-to-first-token metric (non-streaming), pure decode speed, GPU/VRAM usage, power consumption, model weights attestation, confidence intervals, statistical significance or model intelligence improvement is measured.
- The SHA-256 file and receipt digests are not signatures. Local tampering with recomputed hashes is possible; offline verify checks only internal source/plan/metric consistency.
- Automatic promotion, model changes, Agentora dispatch, PhiOS permission updates and GitHub merges are prohibited by the R11 governance flags.

## CI versus workstation

The R11 test runner uses an **in-memory fake local PhiServe client** returning canned public-task answers. It verifies the block sequence, duplicate/invalid evidence rejection, both starting-order modes, authorization denial, token privacy, offline CLI and React parser/build. CI **does not execute model weights or touch the user's GPU**.

After merge, the R11 local command remains available; the hardware experiment still needs to be explicitly performed on a workstation running PhiServe.

**Improve. Verify. Remember. Repeat.**
