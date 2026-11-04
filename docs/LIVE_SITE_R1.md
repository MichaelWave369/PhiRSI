# PhiRSI Live Lab / static website R1

## Purpose

Translate the merged PhiRSI research foundations into a public, accessible and honest React experience without making the public website an agent runtime or controller.

## Boundaries

- GitHub Pages hosts only a static Vite/React site. There are no public model endpoints, secrets, GitHub write tokens, Agentora dispatch APIs or PhiOS ledger writebacks in JavaScript.
- R1–R5 descriptions summarize merged repository documentation as of site creation. They do not claim each system has passed live independent field validation.
- R6 includes a bounded discovery loop and local-only history viewer in this change; R7 remains planned.
- The in-browser experiment uses fixed JavaScript algorithms and measured performance.now() timings. It is **not** a real PhiRSI R1 Python experiment receipt or model benchmark. A browser performance difference is not evidence of recursive model improvement.
- The R6 discovery inspector reads a local JSON file and plots declared development/control/evaluation observations, but cannot verify event hashes, the Python source, or timing provenance.
- The R5 handoff inspector parses a small local JSON file, checks recognized schema and no-authority shape and displays selected fields. It **cannot** replay source evidence, validate the unkeyed checksum or independently authenticate an experiment. It must always label the file unverified. The original R5 Python verifier remains authoritative for local internal consistency checking.
- Imported JSON is not uploaded or saved in any persistent storage. No fetch requests to model/Agentora/PhiOS servers.
- The page makes no research outcome or status promises beyond source-supported, published project milestones.

## CI and publication

The site workflow runs Node unit tests and a Vite build on PR. Deployment runs only on main after build passes, with GitHub Pages deployment permissions in its own job. The expected URL is https://michaelwave369.github.io/PhiRSI/ after setting Pages Source to GitHub Actions and after a successful deployment.

## Manual field acceptance (after merge/deploy)

1. Visit the actual Pages URL in a desktop browser and on a narrow mobile screen.
2. Verify R1–R5 are marked merged and R6/R7 planned; inspect all seven rung descriptions.
3. Run the trial-vs-sieve browser demo and verify correct counts and a local result, then select the trial-vs-trial negative control.
4. Import a real R5 JSON handoff, confirm its source stays local and the UI labels it unverified.
5. Import a malformed JSON file and a packet with a falsified merge_authorized field. Ensure warnings appear and no privileged actions run.
6. Load an R6 ledger and confirm only the registered candidates and read-only results display; tampered authorization fields must show a warning.
7. Check keyboard navigation, focus rings, screen reader labels and reduced-motion behavior.

**CI green does not mean those post-deploy manual checks have occurred.**
