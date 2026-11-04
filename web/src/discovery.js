/** Strictly presentational local R6 JSON inspector.
 * This CANNOT authenticate a ledger, verify event hashes, rerun R1 experiments,
 * attest latency, or authorize candidate promotion.
 */
const CANDIDATES = ["trial", "sieve"];
const STATUS = new Set([
  "OBSERVATIONAL_SUPPORT", "NOT_SUPPORTED", "NO_ELIGIBLE_CANDIDATE", "BUDGET_STOPPED"
]);
const DENIED = Object.freeze({
  recognized: false, policySafe: false, status: "UNVERIFIED",
  reason: "Unrecognized or unauthorized R6 discovery ledger.",
  originAuthenticated: false, replayVerified: false, automaticPromotion: false,
  entries: []
});
const REQUIRED_GOVERNANCE = {
  automatic_promotion: false,
  human_review_required: true,
  candidate_code_execution: "built_in_registered_only",
  external_network_calls: false,
  model_weight_changes: false,
  independent_timing_replication: false,
  model_intelligence_gain_claim: false
};
const isObject = v => v !== null && typeof v === "object" && !Array.isArray(v);
const hex64 = s => typeof s === "string" && /^[a-f0-9]{64}$/.test(s);
const numeric = n => typeof n === "number" && Number.isFinite(n) && n >= 0 && n < 1e9;
const matchingPolicy = value => isObject(value) &&
  Object.keys(value).sort().join("|") === Object.keys(REQUIRED_GOVERNANCE).sort().join("|") &&
  Object.keys(REQUIRED_GOVERNANCE).every(k => value[k] === REQUIRED_GOVERNANCE[k]);

export function inspectDiscovery(value) {
  if (!isObject(value) || value.schema !== "phirsi.discovery_ledger.v1"
    || !hex64(value.ledger_sha256) || !isObject(value.plan)
    || value.plan.schema !== "phirsi.discovery_plan.v1"
    || !hex64(value.plan.plan_sha256)
    || !Array.isArray(value.plan.candidates)
    || JSON.stringify(value.plan.candidates) !== JSON.stringify(CANDIDATES)
    || !Array.isArray(value.events) || value.events.length > 3
    || !isObject(value.decision) || !STATUS.has(value.decision.status)
    || typeof value.decision.automatic_promotion !== "boolean"
    || !isObject(value.governance)
    || value.elapsed_is_unattested !== true) {
    return DENIED;
  }
  const policySafe = matchingPolicy(value.governance)
    && value.decision.automatic_promotion === false
    && value.decision.human_review_required === true
    && value.decision.model_intelligence_improvement_claim === false
    && value.decision.independent_replication === false;
  if (!policySafe) {
    return { ...DENIED, reason: "Unsafe or inconsistent authority fields; do not trust this file." };
  }
  const entries = [];
  for (let i = 0; i < value.events.length; i++) {
    const entry = value.events[i];
    if (!isObject(entry) || entry.sequence !== i
        || !["development", "evaluation"].includes(entry.phase)
        || !CANDIDATES.includes(entry.candidate)
        || !hex64(entry.event_sha256)
        || !isObject(entry.receipt) || !isObject(entry.receipt.summary)
        || !numeric(entry.receipt.summary.geomean_observed_speedup)
        || entry.receipt.summary.correctness_passed !== true) {
      return DENIED;
    }
    const requiredPhase = i < 2 ? "development" : "evaluation";
    if (entry.phase !== requiredPhase
        || (i < 2 && entry.candidate !== CANDIDATES[i])
        || (i === 2 && entry.candidate !== "sieve")) {
      return DENIED;
    }
    entries.push({
      label: i === 0 ? "NEGATIVE CONTROL" : i === 1 ? "CANDIDATE SCREEN" : "SINGLE EVALUATION",
      candidate: entry.candidate,
      phase: entry.phase,
      ratio: entry.receipt.summary.geomean_observed_speedup,
      referenceCorrect: true
    });
  }
  if (value.decision.selected_candidate !== null
      && value.decision.selected_candidate !== "sieve") return DENIED;
  if (value.decision.evaluated_candidate !== null
      && value.decision.evaluated_candidate !== "sieve") return DENIED;
  if (entries.length === 3 && value.decision.evaluated_candidate !== "sieve") return DENIED;
  if (entries.length < 3 && value.decision.evaluated_candidate !== null) return DENIED;
  return {
    recognized: true,
    policySafe: true,
    status: value.decision.status.replaceAll("_", " "),
    planHashPrefix: value.plan.plan_sha256.slice(0, 12),
    sourceHashPrefix: value.ledger_sha256.slice(0, 12),
    selectedCandidate: value.decision.selected_candidate || "NONE",
    evalObservedSpeedup: entries.length === 3 ? entries[2].ratio : null,
    entries,
    originAuthenticated: false,
    replayVerified: false,
    automaticPromotion: false,
    reason: "Shape only. Source, checksums, sample timings and provenance are NOT verified here."
  };
}
