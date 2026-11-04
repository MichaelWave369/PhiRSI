# Rung 3: Human-Approved Candidate-Code Probes

**Status:** Experimental, opt-in local Docker probe. CI does not execute untrusted candidate code.

## Scope

R3 accepts a human- or AI-authored Python candidate as *inert JSON* for an explicitly registered prime-count task. The intake command verifies source and proposal checksums, returns **HELD**, and does not import or execute candidate source. Neither checksum authenticates the source author.

R3 does **not** apply arbitrary patches to Git repositories, train AI models, update itself, or autonomously open/merge pull requests. It stages candidate files in a temporary directory read-only mounted into a disposable Docker container. Future work may add isolated worktrees and a separate independent evaluator.

## Prepare and inspect without executing

Requires Python 3.11+, from the repo root:

    python -m pip install -e .
    mkdir -p artifacts
    python -m phirsi.proposal_cli draft --source examples/sieve_candidate.py --id candidate-sieve-369 --hypothesis "Investigate candidate prime counting" --output artifacts/r3-proposal.json
    python -m phirsi.proposal_cli review --proposal artifacts/r3-proposal.json

The result explicitly says **HELD** and **execution_performed: false**. Draft and probe commands refuse to overwrite existing files.

## Optional authorized Docker probe

Only run on a machine where you trust and control Docker. Inspect the official Python 3.12 slim image yourself, pull it separately, and record the real, locally available pinned digest. The CLI refuses tags without an explicit digest and does not pull images automatically.

    python -m phirsi.proposal_cli probe --proposal artifacts/r3-proposal.json --image "python:3.12-slim@sha256:<verified-image-digest>" --approve-isolated-run --output artifacts/r3-probe.json

The literal placeholder must be replaced with a real 64-character SHA-256 image digest. The container has no network, read-only root and candidate files mounted read-only; drops all capabilities; sets no-new-privileges and non-root UID; requests default Docker seccomp, 256 MB memory, one CPU, 16 PIDs, limited tmpfs/logs and a 20-second bounded wait. It attempts container kill/remove on timeout. Host-generated challenge inputs are recorded in the receipt.

The untrusted guest runs a count_primes(limit) function, and the host separately checks the guest-reported counts against the known reference. The probe does not infer better speed, actual code execution provenance, independent timing, scientific validity, or model intelligence. The guest can manipulate its own output and claimed timings.

Possible receipts: **advisory_correctness_passed**, **incorrect_candidate**, or **failed_closed**. All are review-only, with automatic_promotion=false. A passing probe is not permission to deploy a candidate.

## Important safety limits

**Docker is not a complete security boundary.** The kernel and Docker daemon remain trusted; hostile candidate code could still exploit a container-runtime or kernel vulnerability. Use a separately isolated VM or dedicated machine for truly adversarial source, and keep Docker daemon sockets and credentials inaccessible. The tool does not certify a host's real security settings.

CI uses a trusted example for inert intake, and mocks Docker for control-plane tests. It does not execute the candidate and cannot verify isolation on your computer. Any field claim must include field-test evidence and the exact image digest. Guest-reported performance measurements are not trusted.

Host correctness checking is limited to matching reported integer outputs. It cannot prove the candidate honestly computed them, nor that R3 performed an independent security or timing test.

**Capability is not authority. Evidence is not endorsement.**
