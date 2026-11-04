# ΦRSI development roadmap

## R1: Evidence Foundation (merged)

Build a standard-library Python experiment runner with bounded built-in algorithms, deterministic case generation, separate reference, real measurements, JSON receipts, replay checks, unit tests and a CI smoke artifact.

**Exit gate:** Python CI tests pass, real receipts validate, tampered results fail, and automatic promotion remains disabled.

## R2: Precommitted two-split evaluation (merged)

Register bounded hypotheses and acceptance criteria before experiments. Compare development and evaluation splits, reject an identical-algorithm negative control, retain both evidence receipts and replay conclusions. This is a documented split, not a secret or independently isolated holdout. Formal confidence intervals, multiple alternative baselines, authenticated preregistration and independent timing replication remain open research.

## R3: Human-authorized candidate-code probes (current PR)

Accept untrusted Python source as inert, fingerprinted proposal packets. Only a separate, explicit operator approval invokes a bounded local Docker container with no network, no secrets, read-only mounts and CPU/memory/process/time caps. Match guest-reported outputs against a host-side reference, but treat guest timings and execution provenance as unverified. R3 does not apply arbitrary Git patches or run Docker in CI. Stronger VM isolation and independent execution provenance remain future work.

## R4: Real local AI workloads

Introduce an optional PhiServe interface. Measure model inference latency, throughput, VRAM/resource use and quality on versioned evaluation tasks. Distinguish system optimization from model capability improvement.

## R5: Governed Φ ecosystem

Use Agentora for research orchestration, PhiOS for policy and receipts, CompAware for adversarial controls and PhiMadaPrime for read-only observability. Each adapter must have its own tests and explicit permissions.

## R6: Bounded iterative discovery

Explore candidate search under human-set budgets, immutable holdouts, independent acceptance criteria, rollback and explicit stop conditions. No self-granting authority or autonomous deployment.

## R7: Open replication

Publish reproducible experiment packets, negative results, public evaluation protocols and a clear dashboard with uncertainty and provenance.

**Improve. Verify. Remember. Repeat.**
