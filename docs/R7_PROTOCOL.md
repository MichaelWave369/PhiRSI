# Rung 7 | Open Comparison and Research Packets

**Purpose:** make controlled research easy to inspect, challenge, repeat and share without treating software test passes as proof of independent scientific replication.

R7 is a **comparison and packaging layer**, not an independent AI discovery system. It accepts 2–6 original R6 ledgers with different development seeds and otherwise identical preregistered experiment settings. Each input must pass the existing R6 verifier, including all embedded R1 correctness checks. A valid pack preserves original receipts, unsuccessful or budget-stopped runs, and observed speedup measurements.

## Reproducible local operator example

Python 3.11+ and the PhiRSI package installed from this exact checkout are required.

    python -m pip install -e .
    python -m unittest discover -s tests -v
    mkdir -p artifacts

Create matching plans with distinct seeds:

    python -m phirsi.discovery_cli plan --seed 369 --max-n 2000 --cases 3 --rounds 2 --output artifacts/plan-369.json
    python -m phirsi.discovery_cli plan --seed 370 --max-n 2000 --cases 3 --rounds 2 --output artifacts/plan-370.json

Review the plans and, for meaningful preregistration, commit and timestamp them before looking at results. Separate runs must retain identical hypothesis, thresholds, candidates, resource caps and R6 implementation source code.

Explicitly approve and run each bounded experiment:

    python -m phirsi.discovery_cli run --plan artifacts/plan-369.json --approve-bounded-search --output artifacts/ledger-369.json
    python -m phirsi.discovery_cli run --plan artifacts/plan-370.json --approve-bounded-search --output artifacts/ledger-370.json

Package the **unmodified** JSON ledgers:

    python -m phirsi.replication_cli pack --ledger artifacts/ledger-369.json --ledger artifacts/ledger-370.json --output artifacts/r7-packet.zip

Check every source and summary without extracting any archive files:

    python -m phirsi.replication_cli verify artifacts/r7-packet.zip

Export the summary-only browser input:

    python -m phirsi.replication_cli summary artifacts/r7-packet.zip --output artifacts/r7-summary.json

Open the public Live Lab, visit Open Replication and choose r7-summary.json. Everything happens in-browser; the site uploads nothing and **does not itself authenticate or verify the summary**.

## Packet contents

A small uncompressed ZIP, containing only:

- manifest.json, schema phirsi.replication_packet.v1.
- runs/run-01.json through runs/run-06.json, as applicable, preserving the original R6 ledger data in canonical JSON.

The manifest binds each run's ledger SHA-256, source hash, plan SHA-256, seed, declared status, observed evaluation ratio if available, mandatory control ratio if recorded, and **self-reported** Python/platform/CPU metadata. It also records overall counts of observational support, non-support, no eligible candidate and budget stops, plus median/min/max of recorded evaluation ratios when available.

Invalid or duplicate seeds/ledger hashes, mixed code versions, differing experiment settings, malformed evidence, forged authority, extra ZIP entries, unexpected paths, oversized inputs and compressed archive members are rejected. ZIP contents are **never extracted or executed**. The CLI refuses to overwrite files.

A packet is at most 8 MB, has 2–6 runs, and each source ledger is at most 1 MB.

## Very important evidence distinctions

- **Same code and different seeds do not establish independent research.** Two runs on one GitHub runner or the same physical machine are repeated trials, not independent external replication.
- R7 never independently authenticates a different laboratory, actual hardware, experimenter, chronology, raw timing measurements or original source execution. The R6 verifier replays correctness and local consistency, not historical timing.
- Both the manifest SHA-256 and embedded ledger digests are **unkeyed checksums**, not signatures. An attacker could fabricate timing observations, then recompute all digests.
- Descriptive counts and observed medians are not statistical significance or confidence intervals. Selection bias remains, and the public prime-count inputs are not hidden holdouts.
- A ratio is an **observed algorithm-runtime comparison**, not a measure of a model's intelligence or proof that a new AI discovered or adopted a better implementation.
- All results, including null evaluation ratios for stopped or nonselected runs, are preserved. Never silently drop failed experiments when publishing.
- The archive may include self-reported environment metadata and individual timing samples. **Review its contents for sensitive information before sharing**, even when using only built-in non-sensitive algorithms. No public upload is automatic.

## Comparison versus verified independent replication

To attempt genuine independent replication, a separate operator must acquire the published source at the pinned revision, evaluate a preregistered protocol on a machine under their control, publish the original evidence with trustworthy external provenance and review any environment differences. R7 does not attest those conditions. The package enables reproducible review without claiming that it happened.

## Browser verification limits

The React comparison desk reads only summary JSON (not the ZIP), recognizes the declared R7 manifest shape and checks that authority fields are not permissive. It is a **local visual preview**, not a verifier of embedded R6 results, hashes or provenance. The Python verify command is required for source consistency checks, and neither tool is an independent historical timing attestation.

## CI evidence

The R7 workflow runs two small synthetic R6 experiments with different seeds on **the same GitHub Actions runner**, packs them, invokes the offline packet verifier and exports a summary artifact. All existing R1–R6 and React tests continue to run on the PR. A green check verifies the new software behavior, not an independent replication.

**Capability is not authority. Repetition is not the same as replication.**
