# Evidence contract: phirsi.receipt.v1

## JSON fields

- schema: immutable version identifier.
- experiment: fixed workload, registered baseline/candidate, seed, case inputs and resource bounds.
- provenance: current algorithms.py/lab.py SHA-256 fingerprint, canonical seeded-input digest and UTC timestamp.
- environment: Python version, platform, machine architecture and logical CPU count.
- observations: reference prime count, result counts, monotonic elapsed nanosecond samples, median and nearest-rank 95th percentile by case.
- summary: aggregate correctness, geometric mean of observed median speedup ratios and explicit non-claims.
- governance: automatic_promotion=false, human_approval_required=true.
- receipt_sha256: unkeyed SHA-256 of the canonical sorted/compact JSON payload without this field.

## Verifier behavior

The verifier checks the unkeyed digest, shape/schema, parameter bounds, deterministic regeneration of case inputs, local source fingerprint, input hash, reference counts, registered-algorithm correctness replay, derived timing statistics and governance flags.

The verifier does **not** replay the old timing experiment. It does not certify the hardware, timestamp, author, independence of testing, scientific significance or claimed circumstances of execution. Anyone who can edit a file can rehash it. Authentic signed provenance and independent replicated timing are separate future milestones.

A source-code change invalidates verification of old R1 receipts under the currently installed code unless the original experiment implementation is restored. This deliberately avoids silently mixing code revisions.

No receipt provides merge, deployment, runtime or model-training privileges. A candidate can be measured without being authorized.
