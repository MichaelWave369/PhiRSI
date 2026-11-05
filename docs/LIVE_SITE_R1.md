# PhiRSI Live Lab / static website R1

## Purpose

Translate the merged PhiRSI research foundations into a public, accessible and honest React experience without making the public website an agent runtime or controller.

## Boundaries

- GitHub Pages hosts only a static Vite/React site. There are no public model endpoints, secrets, GitHub write tokens, Agentora dispatch APIs or PhiOS ledger writebacks in JavaScript.
- R1–R5 descriptions summarize merged repository documentation as of site creation. They do not claim each system has passed live independent field validation.
- R6 includes a bounded discovery loop and local-only history viewer; R7 adds offline comparison ZIP/summary export and a local-only React comparison desk. R8 adds a local model A/B result preview with no browser calls to PhiServe. R9 adds a local-only expanded public task and external driver-evidence preview. R10 adds a local-only repeat-run workstation acceptance report, not an authenticated hardware certification. R11 adds a local-only first-vs-repeat model-request latency view with no claimed direct model-load measurement.
- The in-browser experiment uses fixed JavaScript algorithms and measured performance.now() timings. It is **not** a real PhiRSI R1 Python experiment receipt or model benchmark. A browser performance difference is not evidence of recursive model improvement.
- The R6 discovery inspector reads a local JSON file and plots declared development/control/evaluation observations, but cannot verify event hashes, the Python source, or timing provenance.
- The R7 comparison inspector reads a local summary JSON file and plots reported outcomes from 2–6 runs; it cannot authenticate original ZIP contents, run independence or source provenance.
- The R8 model comparison desk reads only a local model-pair summary JSON, shows reported fixed-task accuracy and end-to-end HTTP latency, but never loads weights, authenticates model execution or contacts a local PhiServe process.
- The R10 workstation desk checks a reduced summary locally but cannot verify original R9 receipts, prove cold/warm behavior or authorize model deployment.
- The R5 handoff inspector parses a small local JSON file, checks recognized schema and no-authority shape and displays selected fields. It **cannot** replay source evidence, validate the unkeyed checksum or independently authenticate an experiment. It must always label the file unverified. The original R5 Python verifier remains authoritative for local internal consistency checking.
- Imported JSON is not uploaded or saved in any persistent storage. No fetch requests to model/Agentora/PhiOS servers.
- The page makes no research outcome or status promises beyond source-supported, published project milestones.

## CI and publication

The site workflow runs Node unit tests and a Vite build on PR. Deployment runs only on main after build passes, with GitHub Pages deployment permissions in its own job. The expected URL is https://michaelwave369.github.io/PhiRSI/ after setting Pages Source to GitHub Actions and after a successful deployment.

## Manual field acceptance (after merge/deploy)

1. Visit the actual Pages URL in a desktop browser and on a narrow mobile screen.
2. Verify R1–R10 are marked merged and R11 source available in the proposed change; inspect all eleven rung descriptions.
3. Run the trial-vs-sieve browser demo and verify correct counts and a local result, then select the trial-vs-trial negative control.
4. Import a real R5 JSON handoff, confirm its source stays local and the UI labels it unverified.
5. Import a malformed JSON file and a packet with a falsified merge_authorized field. Ensure warnings appear and no privileged actions run.
6. Load an R6 ledger and confirm only the registered candidates and read-only results display; tampered authorization fields must show a warning.
7. Load a local R7 summary JSON and confirm failures and budget stops remain visible. Try forged authorization claims; they must be rejected.
8. Load a local R8 summary JSON and confirm the two-model comparison is marked unverified. Try forged authority and model-winner flags.
9. Load an R9 field summary and check that source fingerprints and driver telemetry are not described as execution attestation.
10. Import an R10 summary and confirm pass/fail statuses are descriptive only. Forged machine attestation or automatic-promotion claims must be refused.
11. Import R11 block summary JSON and confirm that the first-vs-repeat latency is not labeled as model loading time. Forged cold-start or deployment permissions must be refused.
12. Check keyboard navigation, focus rings, screen reader labels and reduced-motion behavior.

**CI green does not mean those post-deploy manual checks have occurred.**
