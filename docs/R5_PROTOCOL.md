# Rung 5: Governed Evidence Handoff

## Objective and current truth

PhiRSI R5 integrates existing **R1–R4 verification functions** with a common *offline, zero-authority* handoff schema. It also provides one **real, read-only local Agentora preflight**, using Agentora's existing GET /api/health and GET /api/system/version routes.

**This rung does not install, launch, or integrate a mission into Agentora.** It does not write to PhiOS's Reality Ledger, invoke its permission checks, import into PhiMadaPrime, or exchange data with CompAware. Those require separately reviewed adapters in their owning repositories. Instead the handoff describes those future *review targets*, with no dispatch or writeback authority.

## Local commands

Requires Python 3.11+ and existing R1, R2, R3 or R4 JSON evidence:

    python -m pip install -e .
    python -m unittest discover -s tests -v
    mkdir -p artifacts
    python -m phirsi.ecosystem_cli prepare --kind r2 --source artifacts/study.json --output artifacts/handoff.json
    python -m phirsi.ecosystem_cli verify --kind r2 --source artifacts/study.json --handoff artifacts/handoff.json

Use --kind r1 for a PhiRSI R1 experiment receipt, r2 for the two-split R2 study, r3 for an **inert candidate proposal** (not an execution probe), or r4 for the PhiServe benchmarking receipt.

The output file cannot overwrite an existing file. The original source is not embedded in the handoff. Keep local raw evidence available to replay its validator when evaluating the handoff.

When you are already running Agentora on its documented local port 8088:

    python -m phirsi.ecosystem_cli agentora-doctor --port 8088

This performs exactly **GET /api/health** and **GET /api/system/version** at 127.0.0.1:8088, with small response caps. It does not send a mission, an authorization token, a candidate, a prompt, a receipt, or any write request. If Agentora is offline, it fails closed.

## Handoff evidence

Schema: phirsi.ecosystem_handoff.v1. Each packet includes:
- Source kind, SHA-256 hash of the entire underlying JSON and a *reduced*, validator-derived summary.
- A recorded timestamp, packet consistency checksum and explicit unverified provenance flags.
- Policy: execution, merge, deployment, model-weight changes and writeback all **false**; authorized_actions is **empty**; human_review_required is **true**.
- Target hints for Agentora (offline review), PhiOS (offline governance proposal), PhiMadaPrime (local import candidate), CompAware (adversarial review candidate).
- Disposition REVIEW_ONLY and no claimed external side effects.

The verifier requires the **original source evidence file**, reruns the existing rung verifier, and checks the full source hash, reduced summary and exact no-authority policy. A handoff hash alone cannot verify correctness or timestamp chronology. All hashes are unkeyed and do not authenticate authorship.

### Per-rung limitations

- R1: correctness replayed locally, timings not independently replicated.
- R2: two-split evidence checked; a non-secret evaluation split is not scientific independence.
- R3: **inert proposal only**. Source bytes are not copied into handoffs; no candidate execution is performed or certified. Probe receipts are not supported in R5.
- R4: checks hashes/summary on three public toy prompts, but cannot attest model identity, original inference execution, GPU hardware, or historical latency.

The handoff has **no executable instructions or external URLs**. Importers must treat all text as data, revalidate locally, and request explicit review. An external system receiving this JSON must never grant authority based on its fields alone.

## Research orchestration integration boundaries

Agentora exposes an operator-controlled mission system, but its launch routes are POST endpoints and can trigger real work. R5 **does not use them**. Future Agentora integration should obtain human approval and preserve source hashes, resource budgets, and exact mission targets.

PhiOS's principle "capability is not authority" remains the rule here: evidence is not permission. Future PhiOS ingestion needs a dedicated versioned review adapter that reads the original source evidence and applies its own rules. No bridge may silently write to canonical memory or the Reality Ledger.

PhiMadaPrime stays a read-only office; this handoff is not an already supported import format. A future UI should plainly mark it unverified until independently checked.

## What CI proves

The R5 GitHub Actions workflow runs all R1–R5 tests; it exercises the evidence adapters against real locally generated R1/R2 data, an inert R3 proposal and an R4 fake-inference receipt. It uses an in-process fake Agentora HTTP service on loopback and never launches a real Agentora, PhiOS, PhiServe model, or candidate sandbox.

Green CI proves **software contract compatibility with those test fixtures**, not live end-to-end installation, independent scientific replication or permission to promote results.

**Capability is not authority. Observations are not receipts of execution. Review before promotion.**
