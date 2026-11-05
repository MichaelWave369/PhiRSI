# ΦRSI Live Lab (React + Vite)

A lightweight, read-only public research website for the PhiRSI project.

## Run locally

Requires Node.js 22 or newer.

    cd web
    npm install
    npm test
    npm run dev
    npm run build
    npm run preview

All app code lives under web/src. This version has no cloud inference, analytics, database, user credentials, model downloads or authenticated GitHub API calls. There is no frontend backend; GitHub Pages serves a static bundle.

## What actually works

- Interactive R1–R11 milestone explorer. R1–R10 are merged and R11 source is available in this change.
- Browser-only prime-counting demonstration using a trial-division baseline, a sieve candidate and a separately written reference algorithm. Three inputs, 1–3 rounds, n at most 15,000. Results are local observations only, with no formal inference significance or AI model claims.
- Negative control comparing the trial implementation to itself; a speed difference cannot count as an improvement.
- Local-only R5 JSON handoff inspector. File contents remain in browser memory and are not uploaded or saved. The inspector checks a narrow schema shape and whether no-authority fields retain their intended values. **It does not verify source evidence, attest authorship, or validate cryptographic hashes.** Run PhiRSI's Python ecosystem_cli verifier with the original source for that.
- Local-only R6 discovery ledger import and visualization, showing the reported negative control, candidate measurement and any evaluation as a chart.
- Local-only R7 summary JSON import, visualizing 2–6 runs, reported support counts, unsuccessful/budget-stopped runs and evaluation ratios. This is **shape-only** and does not authenticate original ZIP evidence, timing, source identity or true independent replication.
- Local-only R8 model-pair summary JSON preview, comparing registered aliases, public toy-task exact-match fractions and reported end-to-end latency. **The browser does not contact PhiServe, perform inference or independently authenticate the experiment.**
- Local-only R9 expanded public-task and optional hardware-evidence summary: per-category exact match, GGUF hashes, and separate driver memory observations. This is only a shape preview and cannot authenticate the source or loaded model weights.
- Local-only R10 workstation acceptance summary preview: all repeat-run accuracy and median HTTP observations, whether predeclared limits were reported as met, and explicit no-attestation warnings. The original R9 receipt bundle never enters the browser.
- Local-only R11 first-vs-repeat model-request summary preview: per-block initial and repeated HTTP latencies, requested alias change flags, and explicitly unmeasured model-load time. It cannot verify real cold/warm state or source execution.
- Direct links to the public GitHub documentation and related repos. No calls to local Agentora, PhiOS, or PhiServe are made from the web page.

## Publish on GitHub Pages

The .github/workflows/site.yml workflow runs on PRs and pushes to main. For PRs it installs dependencies, runs Node unit tests, and builds; it never publishes a PR artifact to the public site. After a green merge to main, it uploads the built web/dist and runs actions/deploy-pages.

Under Settings → Pages → Build and deployment, choose **GitHub Actions** as the source. The expected project URL after successful deployment is:

https://michaelwave369.github.io/PhiRSI/

This URL is not evidence of a live website before the deploy job succeeds. The relative Vite base supports hosting under the /PhiRSI/ prefix without changing the application's routes. The site uses hash-less in-page anchors, not SPA history routing.

**Build CI is not a browser screenshot or live production smoke test.** On-device visual and accessibility acceptance checks remain open after initial deployment.

## Truth boundaries

The page is a visualization of published milestones and an educational local experiment. It never auto-runs other code, evaluates arbitrary uploaded Python, writes a PhiOS ledger entry, issues GitHub merge calls or promotes models. Uploaded JSON is untrusted data and is rendered using React's normal text escaping. R1–R11 status labels reflect repository source and are not real-time CI/provider health indicators.

**Capability is not authority.**
