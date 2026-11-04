# Rung 6 | Bounded Candidate Discovery and Evidence Ledger

**Scope: a real, repeatable software experiment-selection workflow, not a self-improving AI model.**

R6 builds a deterministic control plane around the R1 prime-count benchmark and preserves measurements, negative controls, selection decisions and budget stop conditions in a versioned chained JSON ledger.

## Design

1. Create a plan with hypothesis, baseline, **fixed and pre-reviewed** candidates (trial and sieve), two distinct seeds, evaluation criteria and budgets.
2. Run the **trial vs trial** negative control on development inputs. Its apparent speedup can never qualify it for promotion.
3. Run **sieve vs trial** on development inputs and replay correctness against the trusted R1 reference. If it does not meet the declared development threshold, stop without evaluation.
4. If it qualifies and budget permits, evaluate the selected candidate **once** using a distinct seed. Determine the provisional status from evaluation-only thresholds and the number of cases meeting the speedup target.
5. Write the observed R1 receipts as linked events and a **review-only** decision. No code writes, merges, deployments, privileged actions or model-weight changes occur.

The candidate universe is intentionally tiny. R6 uses only already registered algorithms. It **does not** generate new model architectures, ingest arbitrary patches, run untrusted AI-authored code, call an LLM, or improve the intelligence of any model.

## Operator workflow

From the repo root using Python 3.11+:

    python -m pip install -e .
    python -m unittest discover -s tests -v
    mkdir -p artifacts

Prepare and review a plan:

    python -m phirsi.discovery_cli plan --max-n 5000 --cases 3 --rounds 2 --max-wall-seconds 30 --min-dev-speedup 1.05 --min-eval-speedup 1.2 --min-eval-case-fraction 0.6 --output artifacts/discovery-plan.json

Commit a reviewed plan with a trusted external timestamp **before** running the experiment if chronology matters. A local plan checksum alone does not prove preregistration.

Run after explicit operator approval:

    python -m phirsi.discovery_cli run --plan artifacts/discovery-plan.json --approve-bounded-search --output artifacts/discovery-ledger.json

Verify locally:

    python -m phirsi.discovery_cli verify artifacts/discovery-ledger.json

The run saves negative-control and candidate evidence even if selection fails. It cannot overwrite existing plan or ledger files. The CLI does not call GitHub APIs or any LLM service.

## Bounded protocol

| Resource | Bound |
|---|---|
| Registered candidates | Exactly 2: trial, sieve |
| Negative controls | 1, first in order |
| Evaluation budget | At most 1 selected candidate |
| Input upper bound | 1,000–12,000 |
| Case count per experiment | 2–5 |
| Timing rounds per case | 1–3 |
| Warmups | 0–1 |
| Soft wall-clock budget | 5–120 seconds |
| Remote calls, filesystem code execution, model weights | None |

The wall-clock limit is a **soft** stop condition between trusted bounded Python calls. It does not forcibly interrupt a running algorithm and **is not a hard operating-system resource cap**. Actual elapsed time is recorded but not independently authenticated. Exceeding budget records BUDGET_STOPPED even if a candidate appears faster.

## Status meanings

- OBSERVATIONAL_SUPPORT: selected registered non-control algorithm correct and meets evaluation speedup and per-case fraction thresholds.
- NOT_SUPPORTED: selected candidate was evaluated but failed the criteria.
- NO_ELIGIBLE_CANDIDATE: non-control algorithm failed development criteria.
- BUDGET_STOPPED: work was interrupted by the soft budget or exceeded it.

All statuses are review-only. No status changes code, model weights or GitHub.

## Ledger and verification contract

The phirsi.discovery_plan.v1 schema binds candidates, seeds, thresholds and budget. The phirsi.discovery_ledger.v1 schema includes plan, R1 receipt events, event hash chain, final assessment, code fingerprint, elapsed time and no-authority governance.

The verifier checks exact plan fields, allowlist/order, input seed and limit agreement, chained event hashes, R1 correctness replay, no evaluation of the control, at-most-once evaluation, derived final status and no-authority flags.

**Neither plan hash nor ledger hash is a signature.** Anyone with file access can rewrite fields and recompute hashes. The verifier cannot authenticate experimenter, original timing, execution environment or provenance. There is no hidden holdout: seed construction and candidate source are public. Selection and multiple comparisons introduce statistical bias. Observational support is not replicated evidence of general AI capability.

## Live React site

The public Live Lab adds a local-only Discovery Ledger inspector displaying a timeline and declared ratios after parsing local JSON in-browser. It checks only expected shape and no-authority fields; it **does not** check the hash chain, replay Python correctness or authenticate provenance. It always labels claims unverified. The Python verifier is needed for internal consistency checking. Files are not uploaded to the hosting platform.

## CI

The R6 workflow executes registered algorithms, unit tests and ledger verifier on GitHub runners, then uploads a synthetic evidence artifact. It does not run an agent, generate arbitrary code, contact PhiServe, control Agentora, or execute weights. A green check is not independent scientific replication.

**Improve. Verify. Remember. Repeat.**
