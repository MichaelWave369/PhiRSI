# ΦRSI development roadmap

## R1: Evidence Foundation (merged)

Build a standard-library Python experiment runner with bounded built-in algorithms, deterministic case generation, separate reference, real measurements, JSON receipts, replay checks, unit tests and a CI smoke artifact.

**Exit gate:** Python CI tests pass, real receipts validate, tampered results fail, and automatic promotion remains disabled.

## R2: Precommitted two-split evaluation (merged)

Register bounded hypotheses and acceptance criteria before experiments. Compare development and evaluation splits, reject an identical-algorithm negative control, retain both evidence receipts and replay conclusions. This is a documented split, not a secret or independently isolated holdout. Formal confidence intervals, multiple alternative baselines, authenticated preregistration and independent timing replication remain open research.

## R3: Human-authorized candidate-code probes (merged)

Accept untrusted Python source as inert, fingerprinted proposal packets. Only a separate, explicit operator approval invokes a bounded local Docker container with no network, no secrets, read-only mounts and CPU/memory/process/time caps. Match guest-reported outputs against a host-side reference, but treat guest timings and execution provenance as unverified. R3 does not apply arbitrary Git patches or run Docker in CI. Stronger VM isolation and independent execution provenance remain future work.

## R4: Optional local PhiServe interface (merged)

Explicitly authorized non-streaming inference against an existing loopback PhiServe model; public three-task exact-match suite, end-to-end HTTP latency, optional provider-reported token throughput and receipt consistency checks. Real model weights are not run in CI. VRAM/power telemetry, streaming TTFT, robust quality tasks and independent replication remain future work. Distinguish system optimization from model capability improvement.

## R5: Governed review handoff (merged)

Bind verified R1–R4 evidence to a compact, zero-authority handoff packet; add a real GET-only local Agentora health/version preflight and comprehensive negative tests. PhiOS ledger ingestion, Agentora dispatch, CompAware review and PhiMadaPrime display are **not yet implemented**, and will require separate contracts and operator permission.

## R6: Bounded registered-candidate discovery (merged)

Run one mandatory same-algorithm control, screen a registered candidate on development inputs, optionally evaluate it **once** on separate seeded inputs, and write a versioned chained ledger of all observations and failures. Enforce declared candidate count, evaluation count, input bounds and soft wall-clock budget. This is an algorithm experiment, **not** AI-generated candidate search, secret/immutable holdout, hard OS sandbox or independent timing replication. No self-granting authority, model modification or autonomous deployment.

## R7: Open comparison and research packets (merged)

Create source-bound, reviewable ZIPs from 2–6 R6 ledgers with distinct seeds and identical protocol settings; replay existing validators, reject incompatible runs, retain negative/budget-stopped results, report descriptive statistics, and export local-only summaries to the React comparison desk. **No authenticated independent operators/hosts, statistical significance, model intelligence gain or deployment authority** are implied. True external replication remains future work.

## R8: Controlled local model A/B (merged)

Real, explicitly approved paired inference requests to an already-running loopback PhiServe server, comparing two registered aliases on the same three fixed public tasks. Alternate request order, preserve hashed-answer receipts, verify self-consistency offline and visualize a reduced summary in React. The CI fixture simulates PhiServe; it does not run actual weights. No independent model identity confirmation, hardware telemetry, general quality inference, automatic model selection or deployment authority is claimed.
## R9: Expanded field evidence (current PR)

Compare two already-registered PhiServe aliases on 12 fixed public tasks with bounded requests, optional SHA-256 hashes of operator-selected GGUF files, and optional imported PhiServe driver process-memory observations from **separate** field-run receipts. Export a review-only browser summary. No live CI inference, authenticated served-weight binding, simultaneous GPU telemetry, scientific confidence interval or automatic promotion is claimed.
**Improve. Verify. Remember. Repeat.**


## Static Live Lab website (separate presentation milestone)

The React/Vite site under web/ displays published rung summaries, runs a limited prime-count comparison entirely within the browser, inspects local R5 advisory handoff JSON, adds R6 local-only discovery ledger visualization, in R7 adds a local-only multi-run comparison desk, and in R8 adds a read-only PhiServe A/B results desk. No imported JSON is uploaded. It **cannot** verify original receipt provenance, authorize actions, or claim model intelligence improvement. Public GitHub Pages deployment is gated on the frontend build and requires Pages settings and independent browser acceptance. This is separate from R6 iterative research.
