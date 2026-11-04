# Rung 4 | Opt-in Local PhiServe Inference Benchmark

**Status:** bounded local measurement harness; AI intelligence improvement **not** demonstrated.

R4 measures one **already registered** PhiServe model served at the loopback gateway only. It never installs PhiServe, downloads weights, manages models, changes PhiServe configuration, opens a listening socket, promotes a candidate, or contacts cloud services.

### Running on an actual workstation

1. Start an independently installed and configured PhiServe daemon, using a GGUF model you already possess. See [PhiServe](https://github.com/MichaelWave369/PhiServe).
2. Confirm PhiServe is healthy, and find the registered alias (e.g. qwen3:4b). Its default address is 127.0.0.1:11435.
3. In a **separate local terminal**, from PhiRSI:

       python -m pip install -e .
       python -m unittest discover -s tests -v
       python -m phirsi.phiserve_cli doctor --model qwen3:4b --port 11435

4. When you deliberately want to run real model inference, create a private output directory (ignored if named artifacts) and run:

       mkdir artifacts
       python -m phirsi.phiserve_cli run --model qwen3:4b --port 11435 --rounds 2 --max-tokens 32 --timeout-seconds 30 --approve-local-inference --output artifacts/phiserve-r4.json
       python -m phirsi.phiserve_cli verify artifacts/phiserve-r4.json

   Use a registered alias actually present in your PhiServe installation; qwen3:4b is illustrative, not a promise that it is registered.

Optional local bearer-token mode: set PHIRSI_PHISERVE_TOKEN in your process environment from a trusted local source **without putting it in shell history, Git, logs or a command-line argument**. R4 reads that environment variable and sends Authorization only to a fixed loopback 127.0.0.1 endpoint. It never saves the token in the receipt.

### Network/authority boundaries

- R4 makes only GET /health, GET /v1/models and POST /v1/chat/completions to 127.0.0.1 on an explicitly specified integer port. Direct HTTPConnection bypasses hostname resolution, proxies, redirects and URL-parameter host selection.
- The POST requires the explicit --approve-local-inference switch. Doctor performs GET only. No scheduled or CI-initiated real inference.
- Calls are bounded: 1–3 rounds of three fixed tasks, max 8–64 output tokens per request, timeout 5–60 seconds per generation, response body at most 96 KB. Failing preflight prevents requests.
- PhiServe may **load** a previously registered model upon the first completion request, using its own process and resource policy. PhiRSI itself never installs/downloads any model.
- The bearer token is local-only, not printed, exported or persisted. Do not run this tool against an untrusted local service.

### Experimental design

Three intentionally small, public deterministic prompts measure exact responses: uppercase conversion, 17+25 arithmetic, and alphabetic ordering. The prompts are known to every participant and are neither held-out evaluation data nor a robust model capability benchmark.

Per request, PhiRSI records end-to-end local HTTP latency, the SHA-256 of whitespace-stripped model output, exact-match result and (only if PhiServe reports it) completion tokens. The receipt stores **no prompt text, response text, or bearer token**. Aggregate measures are median/p95 latency, exact-match fraction, and provider-reported completion tokens divided by accumulated full HTTP request time. This is **not decode-only tokens per second**. Absent usage fields remain null, never guessed. Responses do not prove model identity.

There is **no VRAM or power telemetry** in this rung, and the receipt explicitly records that such measurement was not performed. The protocol cannot establish the model's speed relative to a different model without repeated comparable runs on the same hardware/configuration. No time-to-first-token: the request is non-streaming.

### Verification and limits

The verify command checks local receipt consistency, source fingerprint, fixed-case hash, response hashes against exact known answers, aggregate calculations and non-promotion declarations. It does **not** recontact PhiServe, rerun model weights, authenticate model identity or verify historical timings. An unkeyed JSON checksum is not a signature; an attacker can fabricate measurements and rehash them.

The GitHub CI job runs deterministic **fake PhiServe HTTP server tests on loopback**. It makes no request to a real model or actual PhiServe daemon. CI success is not evidence of GPU execution or inference on your computer.

Do not commit personal prompts, secret tokens, actual model outputs, or unreviewed receipts. The R4 benchmark only uses built-in non-sensitive prompts, and the default artifacts/ directory is gitignored.

### Future work

Authenticated model fingerprints and independent resource measurements, streaming time-to-first-token, a proper inference quality task set, independent replications, baselines, evaluator blindness, power/VRAM tracking, and full PhiOS-governed experiment promotion are separate later milestones.

**Evidence above hype. Capability is not authority.**
