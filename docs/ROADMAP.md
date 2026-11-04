# ΦRSI development roadmap

## R1: Evidence Foundation (merged)

Build a standard-library Python experiment runner with bounded built-in algorithms, deterministic case generation, separate reference, real measurements, JSON receipts, replay checks, unit tests and a CI smoke artifact.

**Exit gate:** Python CI tests pass, real receipts validate, tampered results fail, and automatic promotion remains disabled.

## R2: Precommitted two-split evaluation (current PR)

Register bounded hypotheses and acceptance criteria before experiments. Compare development and evaluation splits, reject an identical-algorithm negative control, retain both evidence receipts and replay conclusions. This is a documented split, not a secret or independently isolated holdout. Formal confidence intervals, multiple alternative baselines, authenticated preregistration and independent timing replication remain open research.

## R3: AI proposals in containment

Allow AI-generated candidate patches only in disposable worktrees under externally enforced resource and permission limits. Separate proposal generation from trusted evaluation. No secrets, shell/network privileges by default; never trust candidate-supplied test results.

## R4: Real local AI workloads

Introduce an optional PhiServe interface. Measure model inference latency, throughput, VRAM/resource use and quality on versioned evaluation tasks. Distinguish system optimization from model capability improvement.

## R5: Governed Φ ecosystem

Use Agentora for research orchestration, PhiOS for policy and receipts, CompAware for adversarial controls and PhiMadaPrime for read-only observability. Each adapter must have its own tests and explicit permissions.

## R6: Bounded iterative discovery

Explore candidate search under human-set budgets, immutable holdouts, independent acceptance criteria, rollback and explicit stop conditions. No self-granting authority or autonomous deployment.

## R7: Open replication

Publish reproducible experiment packets, negative results, public evaluation protocols and a clear dashboard with uncertainty and provenance.

**Improve. Verify. Remember. Repeat.**
