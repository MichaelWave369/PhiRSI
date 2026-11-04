# ΦRSI Research Charter

## Mission

Help independent researchers distinguish genuine, reproducible AI-systems improvements from measurement noise, benchmark leakage and optimistic claims.

## Research contract

1. State a falsifiable hypothesis, an explicit baseline, evaluation criteria and resource budget *before* the experiment.
2. Preserve failure cases, negative results, code identifiers, input provenance and limitations.
3. Compare correctness, latency, resource use and model quality **separately**. Speeding up code does not necessarily increase AI intelligence.
4. Verify with separate reference implementations and, later, independent evaluators and held-out datasets.
5. Keep experimental capability separate from privileged execution and release authority.
6. Make software, results and reproducibility protocols inspectable with minimal vendor lock-in.

## Rung 1 scope

Rung 1 executes only two built-in prime-count algorithms on seeded, bounded integers; it checks correctness with a third reference implementation and measures elapsed time. No model inference or training, generated-code execution, self-rewrites, remote compute, or autonomous merges take place.

A passing Rung 1 CI suite validates local functionality, **not** recursive AI self-improvement, safety of an intelligent agent or general computational awareness.

## Governance

Only pre-reviewed named workloads can execute inside the R1 process. Experiments cannot grant themselves permissions, update trusted code, or deploy a candidate. Later research with AI-authored code must isolate and meter its execution, prohibit secrets and network use by default, and require human authorization to promote results.

An unkeyed hash is not a signature. A receipt is evidence for review, not a grant of authority. Reproduce important claims on a separate machine with pinned source and protocol.

## Non-goals

No consciousness or sentience claims, AGI milestone declarations, or claims of automatic scientific breakthrough from a single benchmark result. Our purpose is to produce carefully bounded and verifiable research.
