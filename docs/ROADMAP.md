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

## R6: Bounded iterative discovery

Explore candidate search under human-set budgets, immutable holdouts, independent acceptance criteria, rollback and explicit stop conditions. No self-granting authority or autonomous deployment.

## R7: Open replication

Publish reproducible experiment packets, negative results, public evaluation protocols and a clear dashboard with uncertainty and provenance.

**Improve. Verify. Remember. Repeat.**


## Static Live Lab website (separate presentation milestone)

The React/Vite site under web/ displays published rung summaries, runs a limited prime-count comparison entirely within the browser, and inspects the structure of local R5 advisory handoff JSON without uploading it. It **cannot** verify original receipt provenance, authorize actions, or claim model intelligence improvement. Public GitHub Pages deployment is gated on the frontend build and requires Pages settings and independent browser acceptance. This is separate from R6 iterative research.
