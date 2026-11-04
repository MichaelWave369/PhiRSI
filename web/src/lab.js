/** Pure browser demonstration and untrusted handoff shape inspector.
 * The browser bench is NOT a PhiRSI Python receipt, model benchmark, or independent science.
 */

export const RUNGS = [
  { id: 1, title: "Evidence foundation", subtitle: "Reproducible baseline", status: "merged", detail: "Bounded prime-count experiments, independent reference implementation, correctness replay and local timing receipts.", limit: "No AI model, no independent timing replication.", doc: "docs/CHARTER.md" },
  { id: 2, title: "Evaluation protocol", subtitle: "Controls before conclusions", status: "merged", detail: "Precommitted experiment plan, separate development/evaluation seeds, explicit thresholds and negative controls.", limit: "Holdouts are not secret; timestamps are not authenticated.", doc: "docs/R2_PROTOCOL.md" },
  { id: 3, title: "Candidate intake", subtitle: "Contained proposals", status: "merged", detail: "Inert candidate packets, human approval gate, resource-bound optional Docker probe.", limit: "Docker is not a security proof; candidate results are advisory.", doc: "docs/R3_PROTOCOL.md" },
  { id: 4, title: "Local model benchmark", subtitle: "PhiServe connection", status: "merged", detail: "Opt-in loopback inference measurement for existing registered models; narrow exact-match and end-to-end latency.", limit: "Real model and GPU field evidence is separate; no intelligence gain claimed.", doc: "docs/R4_PROTOCOL.md" },
  { id: 5, title: "Governed evidence", subtitle: "Review-only handoff", status: "merged", detail: "Evidence-bound advisory handoff packets and GET-only Agentora service preflight.", limit: "No Agentora mission dispatch or PhiOS ledger writeback.", doc: "docs/R5_PROTOCOL.md" },
  { id: 6, title: "Iterative discovery", subtitle: "Bounded search ledger", status: "implemented", detail: "A reviewed-algorithm search demo that executes a mandatory negative control, screens a registered candidate, performs at most one evaluation, and writes a chained record.", limit: "Only two built-in algorithms. No arbitrary AI-generated code, independent timing replication, autonomous model upgrades or deployment authority.", doc: "docs/R6_PROTOCOL.md" },
  { id: 7, title: "Open replication", subtitle: "Research commons", status: "planned", detail: "Versioned public research packets, independent replications and transparent negative results.", limit: "Not implemented; no independently certified findings.", doc: "docs/ROADMAP.md" }
];

export function trialCount(n) {
  if (n < 2) return 0;
  let count = 1;
  for (let number = 3; number <= n; number += 2) {
    let prime = true;
    for (let divisor = 3; divisor * divisor <= number; divisor += 2) {
      if (number % divisor === 0) {
        prime = false;
        break;
      }
    }
    if (prime) count += 1;
  }
  return count;
}

export function sieveCount(n) {
  if (n < 2) return 0;
  const flags = new Uint8Array(n + 1);
  flags.fill(1, 2);
  for (let divisor = 2; divisor * divisor <= n; divisor += 1) {
    if (!flags[divisor]) continue;
    for (let j = divisor * divisor; j <= n; j += divisor) flags[j] = 0;
  }
  let count = 0;
  for (let i = 2; i <= n; i += 1) count += flags[i];
  return count;
}

export function referenceCount(n) {
  const primes = [];
  for (let value = 2; value <= n; value += 1) {
    let prime = true;
    for (const p of primes) {
      if (p * p > value) break;
      if (value % p === 0) {
        prime = false;
        break;
      }
    }
    if (prime) primes.push(value);
  }
  return primes.length;
}

export function runBrowserBenchmark({ n = 9000, rounds = 2, candidate = "sieve" } = {}) {
  if (!Number.isInteger(n) || n < 1000 || n > 15000) throw new Error("Input must be 1,000–15,000.");
  if (!Number.isInteger(rounds) || rounds < 1 || rounds > 3) throw new Error("Rounds must be 1–3.");
  if (!["sieve", "trial"].includes(candidate)) throw new Error("Unknown registered browser candidate.");
  const limits = [Math.round(n * 0.4), Math.round(n * 0.7), n];
  const rows = [];
  const candidateFn = candidate === "sieve" ? sieveCount : trialCount;
  for (const limit of limits) {
    const expected = referenceCount(limit);
    const baselineMs = [];
    const candidateMs = [];
    let baselineCorrect = true;
    let candidateCorrect = true;
    for (let round = 0; round < rounds; round += 1) {
      // Alternate order to reduce, but not remove, ordering effects.
      const measured = [
        ["baseline", trialCount],
        ["candidate", candidateFn]
      ];
      if (round % 2 !== 0) measured.reverse();
      for (const [name, fn] of measured) {
        const start = performance.now();
        const result = fn(limit);
        const elapsed = Math.max(0.001, performance.now() - start);
        if (name === "baseline") {
          baselineMs.push(elapsed);
          baselineCorrect = baselineCorrect && result === expected;
        } else {
          candidateMs.push(elapsed);
          candidateCorrect = candidateCorrect && result === expected;
        }
      }
    }
    const med = values => {
      const sorted = [...values].sort((a, b) => a - b);
      const mid = Math.floor(sorted.length / 2);
      return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    };
    const baseline = med(baselineMs);
    const measuredCandidate = med(candidateMs);
    rows.push({
      limit, expected, baselineMs: baseline, candidateMs: measuredCandidate,
      ratio: baseline / measuredCandidate,
      correct: baselineCorrect && candidateCorrect
    });
  }
  return {
    type: "browser_demonstration_only",
    candidate,
    rounds,
    rows,
    correct: rows.every(row => row.correct),
    negativeControl: candidate === "trial",
    observedGeomeanSpeedup: Math.exp(
      rows.reduce((sum, row) => sum + Math.log(row.ratio), 0) / rows.length
    ),
    independentlyReplicated: false,
    signedEvidence: false,
    automaticPromotion: false
  };
}

export const EMPTY_AUTHORITY = Object.freeze({
  authorized_actions: [],
  execution_authorized: false,
  merge_authorized: false,
  deployment_authorized: false,
  model_weight_change_authorized: false,
  writeback_authorized: false,
  human_review_required: true
});

export function inspectHandoff(value) {
  const denied = { structurallyRecognized: false, safePolicy: false, status: "UNVERIFIED INPUT", error: "Unrecognized or incomplete handoff JSON." };
  if (!value || typeof value !== "object" || Array.isArray(value)) return denied;
  const hex = /^[a-f0-9]{64}$/;
  if (value.schema !== "phirsi.ecosystem_handoff.v1" ||
      !["r1", "r2", "r3", "r4"].includes(value.source_kind) ||
      typeof value.source_sha256 !== "string" || !hex.test(value.source_sha256) ||
      typeof value.handoff_sha256 !== "string" || !hex.test(value.handoff_sha256) ||
      value.disposition !== "REVIEW_ONLY" || value.handoff_is_receipt_of_external_execution !== false) {
    return denied;
  }
  const p = value.policy;
  const policyKeys = Object.keys(EMPTY_AUTHORITY).sort();
  const actualKeys = p && typeof p === "object" && !Array.isArray(p) ? Object.keys(p).sort() : [];
  const safePolicy = JSON.stringify(policyKeys) === JSON.stringify(actualKeys) &&
    policyKeys.every(key => key === "authorized_actions" ?
      Array.isArray(p[key]) && p[key].length === 0 : p[key] === EMPTY_AUTHORITY[key]);
  const target = value.summary;
  const summary = target && typeof target === "object" && !Array.isArray(target) ? target : {};
  // Only known fields are rendered. No arbitrary source text or unknown keys enter the UI.
  const status = typeof summary.status === "string" && /^[A-Za-z_]{1,40}$/.test(summary.status)
    ? summary.status.replaceAll("_", " ") : "NOT PROVIDED";
  const confidence = typeof summary.exact_match_fraction === "number" &&
                     Number.isFinite(summary.exact_match_fraction) &&
                     summary.exact_match_fraction >= 0 && summary.exact_match_fraction <= 1
    ? summary.exact_match_fraction : null;
  return {
    structurallyRecognized: true,
    safePolicy,
    status,
    sourceKind: value.source_kind.toUpperCase(),
    sourceHashPrefix: value.source_sha256.slice(0, 14),
    exactMatchFraction: confidence,
    disposition: "REVIEW_ONLY",
    requiresSourceVerification: true,
    originAuthenticated: false,
    permissionGranted: false
  };
}
