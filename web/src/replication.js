/** Browser-only R7 manifest shape inspector.
 * No ZIP extraction, no attestation, no cryptographic verification.
 */
const KNOWN = new Set([
  "OBSERVATIONAL_SUPPORT", "NOT_SUPPORTED",
  "NO_ELIGIBLE_CANDIDATE", "BUDGET_STOPPED"
]);
const GUARDS = {
  review_only: true,
  human_review_required: true,
  automatic_promotion: false,
  writes_to_other_repositories: false,
  external_experiments_launched: false,
  model_intelligence_improvement_claim: false,
  statistical_significance_claim: false,
  independent_hosts_authenticated: false,
  historical_timings_authenticated: false,
  cryptographic_signature_present: false
};
const object = x => x !== null && typeof x === "object" && !Array.isArray(x);
const sha = x => typeof x === "string" && /^[a-f0-9]{64}$/.test(x);
const nonnegative = x => typeof x === "number" && Number.isFinite(x) && x >= 0 && x < 1e9;
const rejected = reason => ({
  recognized: false, reportOnly: true, status: "REJECTED",
  error: reason, independentlyVerified: false, promotionAllowed: false, entries: []
});

export function inspectReplication(value) {
  if (!object(value) || value.schema !== "phirsi.replication_packet.v1"
      || !sha(value.manifest_sha256) || !sha(value.r6_runner_code_sha256)
      || !sha(value.comparison_settings_sha256) || !object(value.policy)
      || !object(value.summary) || !Array.isArray(value.entries)
      || value.entries.length < 2 || value.entries.length > 6) {
    return rejected("This is not a recognized R7 summary JSON.");
  }
  const expectedKeys = Object.keys(GUARDS).sort();
  if (JSON.stringify(Object.keys(value.policy).sort()) !== JSON.stringify(expectedKeys)
      || expectedKeys.some(key => value.policy[key] !== GUARDS[key])) {
    return rejected("Authority claims are inconsistent or unsafe.");
  }
  const seenSeeds = new Set(), seenHashes = new Set();
  const entries = [];
  for (const [i, e] of value.entries.entries()) {
    if (!object(e) || e.id !== "run-" + String(i + 1).padStart(2, "0")
        || e.archive_path !== "runs/" + e.id + ".json"
        || !sha(e.canonical_source_sha256) || !sha(e.ledger_sha256)
        || !sha(e.plan_sha256)
        || !Number.isInteger(e.development_seed) || e.development_seed < 0
        || !KNOWN.has(e.reported_status)
        || !Number.isInteger(e.event_count) || e.event_count < 0 || e.event_count > 3
        || (e.evaluation_observed_ratio !== null && !nonnegative(e.evaluation_observed_ratio))
        || (e.control_observed_ratio !== null && !nonnegative(e.control_observed_ratio))
        || seenSeeds.has(e.development_seed) || seenHashes.has(e.ledger_sha256)) {
      return rejected("Malformed, duplicate or unauthorized source entry.");
    }
    seenSeeds.add(e.development_seed);
    seenHashes.add(e.ledger_sha256);
    entries.push({
      id: e.id,
      seed: e.development_seed,
      status: e.reported_status.replaceAll("_", " "),
      observedRatio: e.evaluation_observed_ratio,
      hadEvaluation: e.evaluation_observed_ratio !== null
    });
  }
  const summary = value.summary;
  const statusCounts = [
    "support_count", "not_supported_count",
    "no_eligible_count", "budget_stopped_count"
  ];
  if (summary.run_count !== entries.length
      || summary.independent_replication_established !== false
      || summary.confidence_interval_calculated !== false
      || summary.quality_of_model_measured !== false
      || statusCounts.some(key => !Number.isInteger(summary[key]) || summary[key] < 0)
      || statusCounts.reduce((n, key) => n + summary[key], 0) !== entries.length
      || !Number.isInteger(summary.evaluated_run_count)
      || summary.evaluated_run_count !== entries.filter(e => e.hadEvaluation).length
      || summary.support_count !== entries.filter(e => e.status === "OBSERVATIONAL SUPPORT").length
      || summary.not_supported_count !== entries.filter(e => e.status === "NOT SUPPORTED").length
      || summary.no_eligible_count !== entries.filter(e => e.status === "NO ELIGIBLE CANDIDATE").length
      || summary.budget_stopped_count !== entries.filter(e => e.status === "BUDGET STOPPED").length) {
    return rejected("Comparison summary is inconsistent with its declared entries.");
  }
  return {
    recognized: true,
    reportOnly: true,
    status: "UNVERIFIED COMPARISON",
    entries,
    runCount: entries.length,
    evaluatedCount: summary.evaluated_run_count,
    supportCount: summary.support_count,
    notSupportedCount: summary.not_supported_count,
    noEligibleCount: summary.no_eligible_count,
    budgetStoppedCount: summary.budget_stopped_count,
    medianObservedRatio: nonnegative(summary.evaluation_median_observed_ratio)
      ? summary.evaluation_median_observed_ratio : null,
    manifestHashPrefix: value.manifest_sha256.slice(0, 14),
    independentlyVerified: false,
    promotionAllowed: false,
    explanatoryNote: "Structure only. This website cannot authenticate runs, verify ZIP contents, or reproduce timings."
  };
}
