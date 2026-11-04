/** Static browser inspection only. No HTTP inference, credentials, or cryptographic attestation. */
const GUARD = {
  automatic_promotion: false,
  human_review_required: true,
  model_identity_authenticated: false,
  distinct_weights_verified: false,
  inference_execution_independently_attested: false,
  historical_timings_authenticated: false,
  gpu_vram_measured: false,
  quality_is_only_fixed_exact_match: true,
  statistical_significance_claim: false,
  model_intelligence_improvement_claim: false,
  network_outside_loopback: false,
  model_downloads_or_weight_modifications: false
};
const rejected = reason => ({ recognized: false, verified: false, permittedActions: 0, reason });
const isObject = value => value !== null && typeof value === "object" && !Array.isArray(value);
const isSHA = value => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const positive = value => typeof value === "number" && Number.isFinite(value) && value > 0 && value <= 61000;
const nonnegative = value => typeof value === "number" && Number.isFinite(value) && value >= 0 && value < 1e7;
const alias = value => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9_.:/+\-]{0,127}$/.test(value) && !value.includes("//") && !value.includes("..");
const guardMatches = g => isObject(g) && Object.keys(g).sort().join("|") === Object.keys(GUARD).sort().join("|")
  && Object.entries(GUARD).every(([key, value]) => g[key] === value);

export function inspectModelPair(data) {
  if (!isObject(data) || data.schema !== "phirsi.phiserve_pair_summary.v1"
      || !isSHA(data.source_receipt_sha256) || !isSHA(data.summary_sha256)
      || !alias(data.model_a_alias) || !alias(data.model_b_alias)
      || data.model_a_alias === data.model_b_alias
      || data.fixed_case_count !== 3 || ![1, 2].includes(data.rounds)
      || !guardMatches(data.governance)
      || data.report_is_not_authenticated !== true
      || data.browser_only_shape_inspection !== true
      || !isObject(data.metrics)) {
    return rejected("Invalid R8 summary or unsafe authority/provenance fields.");
  }
  const m = data.metrics;
  if (!isObject(m.models) || !isObject(m.models.A) || !isObject(m.models.B)
      || !Array.isArray(m.paired_observations)
      || m.paired_task_count !== data.rounds * 3
      || m.paired_observations.length !== m.paired_task_count
      || m.decision !== "DESCRIPTIVE_ONLY_NO_WINNER"
      || m.automatic_promotion !== false
      || m.gpu_vram_measured !== false
      || m.task_quality_generalization_claim !== false
      || m.decode_only_throughput_measured !== false
      || m.first_token_latency_measured !== false
      || !nonnegative(m.median_observed_a_over_b_latency_ratio)) {
    return rejected("Unexpected comparison metrics or implied model winner.");
  }
  const models = [];
  for (const [role, label] of [["A", data.model_a_alias], ["B", data.model_b_alias]]) {
    const s = m.models[role];
    if (s.registered_alias !== label
        || s.request_count !== m.paired_task_count
        || !Number.isInteger(s.exact_match_count)
        || s.exact_match_count < 0 || s.exact_match_count > s.request_count
        || !nonnegative(s.exact_match_fraction) || s.exact_match_fraction > 1
        || Math.abs(s.exact_match_fraction - s.exact_match_count/s.request_count) > .000001
        || !positive(s.median_end_to_end_latency_ms)
        || !positive(s.p95_end_to_end_latency_ms)
        || (s.provider_reported_completion_tokens !== null &&
            (!Number.isInteger(s.provider_reported_completion_tokens)
            || s.provider_reported_completion_tokens < 0))
        || (s.estimated_end_to_end_tokens_per_sec !== null &&
            !nonnegative(s.estimated_end_to_end_tokens_per_sec))) {
      return rejected("One model's reported metrics are inconsistent.");
    }
    models.push({
      role, alias: label, exact: s.exact_match_count,
      requests: s.request_count, fraction: s.exact_match_fraction,
      latency: s.median_end_to_end_latency_ms,
      reportedRate: s.estimated_end_to_end_tokens_per_sec
    });
  }
  let winsA = 0, winsB = 0, ties = 0;
  for (const [i, pair] of m.paired_observations.entries()) {
    if (!isObject(pair) || pair.round !== Math.floor(i/3) + 1
        || pair.case_id !== ["uppercase","arithmetic","alphabetical"][i%3]
        || typeof pair.a_exact_match !== "boolean"
        || typeof pair.b_exact_match !== "boolean"
        || !positive(pair.observed_a_over_b_latency_ratio)) {
      return rejected("Invalid paired measurement sequence.");
    }
    if (pair.observed_a_over_b_latency_ratio > 1) winsB++;
    else if (pair.observed_a_over_b_latency_ratio < 1) winsA++;
    else ties++;
  }
  if (m.a_faster_pair_count !== winsA || m.b_faster_pair_count !== winsB
      || m.tie_pair_count !== ties
      || models[0].exact !== m.paired_observations.filter(p=>p.a_exact_match).length
      || models[1].exact !== m.paired_observations.filter(p=>p.b_exact_match).length) {
    return rejected("Reported pair statistics do not match the included rows.");
  }
  return {
    recognized: true, verified: false, permittedActions: 0,
    planStatus: "UNVERIFIED DESCRIPTIVE COMPARISON",
    sourcePrefix: data.source_receipt_sha256.slice(0,12),
    models,
    pairs: m.paired_task_count,
    medianObservedAOverB: m.median_observed_a_over_b_latency_ratio,
    winsA, winsB, ties,
    modelWeightsVerified: false,
    hardwareTelemetryMeasured: false,
    automaticPromotion: false,
    explanation: "This page only checks JSON shape and arithmetic. It never replays inference, authenticates a model, or verifies historical timing."
  };
}
