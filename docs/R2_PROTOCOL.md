# Rung 2: Precommitted Evaluation and Negative Controls

**Status:** Bounded experimental demonstration, not autonomous research or independent scientific replication.

## Purpose

R1 taught PhiRSI to run measured software experiments. R2 adds a published *plan*, two distinct deterministic input splits, specified success thresholds, a same-algorithm negative control, conservative verdicts and replayable receipts.

The supported workload remains registered local prime counting. No generative model, model training, AI-written code, external network access, or deployment logic is introduced.

## Commands

Install from the repository root:

    python -m pip install -e .
    python -m unittest discover -s tests -v

Create a plan:

    mkdir -p artifacts
    python -m phirsi.study_cli plan --candidate sieve --hypothesis "Sieve improves prime counting over trial division" --seed 369 --max-n 20000 --cases 5 --rounds 5 --min-speedup 1.2 --min-case-fraction 0.6 --output artifacts/plan.json

To meaningfully pre-register, **commit and timestamp the plan in a reviewed branch before running or examining the evaluation results**. A local checksum alone is neither an immutable record nor a trusted timestamp.

Run the planned study:

    python -m phirsi.study_cli run --plan artifacts/plan.json --output artifacts/study.json
    python -m phirsi.study_cli verify artifacts/study.json

A negative-control study:

    python -m phirsi.study_cli plan --candidate trial --hypothesis "Trial division compared with itself is a negative control" --output artifacts/control-plan.json
    python -m phirsi.study_cli run --plan artifacts/control-plan.json --output artifacts/control-study.json

## What the outcome means

- `observational_support`: registered candidate and correct outputs in both splits; evaluation-only geometric mean observed speedup meets pre-specified threshold; sufficient individual evaluation cases meet the threshold. **Not an independent replication or promotion permit.**
- `not_supported`: valid evidence that did not meet the precommitted thresholds.
- `negative_control`: identical algorithm on both sides, regardless of timing fluctuation. Cannot qualify as improvement.
- `incorrect`: a correctness failure. Current R1 verifier rejects such a study, rather than certifying it; preserving independently verifiable incorrect-candidate cases is future work.

Development and evaluation inputs use two distinct seeds derived deterministically from the plan. **This is not a secret or truly hidden holdout.** The test set is visible in advance, and a motivated researcher can adapt to it. It is a split intended to discourage accidental post hoc metric selection, not proof against deliberate tuning or benchmark contamination.

The evaluation split alone determines the speedup verdict. Development results are diagnostic. Both are required to pass correctness replay.

## Trust and replication boundaries

- A plan hash records internal consistency, **not** trusted precommitment. Establish chronology externally using a timestamped, reviewed Git commit.
- A study hash is not a digital signature. An attacker can fabricate timing records, recompute reported statistics, and rehash the evidence. Verification does not authenticate origin.
- The verifier replays algorithm correctness and checks statistical calculations but **does not rerun historical timing measurements**.
- The two splits run inside the same process on the same host. They are not independently instrumented, externally sandboxed or cryptographically isolated.
- CPU scheduling, thermal behavior, workloads and order effects can distort timing. No confidence interval or formal statistical significance is claimed.
- The plan cannot overwrite an existing output file via the CLI. This prevents accidents, not a malicious file editor.
- No approval, deployment, write permission or agent authority is derived from `observational_support`.

## Recommended next experiment

Run several independently timed studies on the actual target device with unchanged, committed plan and source code, using a control treatment and a predeclared resource budget. Publish negative results as well as successes. For AI model optimization, next add a truly separate model-quality assessment and resource telemetry.

**Protocol version** `phirsi.plan.v1` and `phirsi.study.v1` are separate from unchanged R1 receipt `phirsi.receipt.v1` for compatibility.
