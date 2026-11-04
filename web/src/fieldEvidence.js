/** R9 summary inspector: local untrusted JSON; never replays inference or verifies signatures. */
const GUARD = {
  automatic_promotion:false, human_review_required:true,
  exact_match_on_public_toy_tasks_only:true,
  independent_execution_attestation:false,
  model_weight_binding_verified:false,
  gpu_execution_independently_verified:false,
  vram_from_independently_witnessed_measurement:false,
  statistical_significance_claim:false,
  intelligence_improvement_claim:false,
  external_network_or_model_download:false
};
const isObject = x => !!x && typeof x === "object" && !Array.isArray(x);
const sha = x => typeof x === "string" && /^[0-9a-f]{64}$/.test(x);
const numeric = x => typeof x === "number" && Number.isFinite(x) && x >= 0 && x < 1e9;
const alias = x => typeof x === "string" && /^[A-Za-z0-9][A-Za-z0-9_.:/+\-]{0,127}$/.test(x) && !x.includes("//") && !x.includes("..");
const reject = reason => ({recognized:false,verified:false,reason,automaticPromotion:false});
export function inspectFieldEvidence(obj) {
  if (!isObject(obj) || obj.schema !== "phirsi.field_summary.v1" ||
      !sha(obj.source_receipt_sha256) || !sha(obj.summary_sha256) ||
      obj.read_only_browser_preview !== true || obj.not_authenticating_source !== true ||
      !isObject(obj.aliases) || !alias(obj.aliases.A) || !alias(obj.aliases.B) ||
      obj.aliases.A === obj.aliases.B || !isObject(obj.governance) ||
      Object.keys(obj.governance).sort().join("|") !== Object.keys(GUARD).sort().join("|") ||
      Object.entries(GUARD).some(([key,value])=>obj.governance[key] !== value)) {
    return reject("Unknown R9 format or unsafe provenance/authorization claim.");
  }
  const metrics=obj.metrics;
  if (!isObject(metrics) || metrics.decision !== "DESCRIPTIVE_ONLY_NO_WINNER" ||
      metrics.automatic_promotion !== false ||
      metrics.independent_replication !== false ||
      metrics.statistical_significance_calculated !== false ||
      metrics.model_intelligence_gain_claim !== false ||
      !isObject(metrics.models) || !isObject(metrics.categories) ||
      !Number.isInteger(metrics.cases_per_model) ||
      ![12,24].includes(metrics.cases_per_model) ||
      metrics.total_post_requests !== metrics.cases_per_model*2) {
    return reject("Inconsistent or unauthorized R9 metrics.");
  }
  const models=[];
  for (const role of ["A","B"]) {
    const data=metrics.models[role];
    if (!isObject(data) || data.alias !== obj.aliases[role] ||
        data.request_count !== metrics.cases_per_model ||
        !Number.isInteger(data.correct_count) || data.correct_count<0 ||
        data.correct_count>data.request_count ||
        !numeric(data.exact_match_fraction) || data.exact_match_fraction>1 ||
        Math.abs(data.exact_match_fraction-data.correct_count/data.request_count)>.000001 ||
        !numeric(data.median_http_ms) || data.median_http_ms===0 ||
        !numeric(data.p95_http_ms) || data.p95_http_ms===0 ||
        (data.provider_tokens_total !== null && (!Number.isInteger(data.provider_tokens_total)||data.provider_tokens_total<0)) ||
        (data.approx_total_http_tokens_per_second !== null && !numeric(data.approx_total_http_tokens_per_second))) {
      return reject("Invalid model metrics.");
    }
    models.push({role,alias:data.alias,correct:data.correct_count,total:data.request_count,
      fraction:data.exact_match_fraction,medianMs:data.median_http_ms,
      reportedRate:data.approx_total_http_tokens_per_second});
  }
  const names=["arithmetic","extraction","instruction","ordering","text"];
  if (Object.keys(metrics.categories).sort().join("|")!==names.join("|")) {
    return reject("Unexpected task categories.");
  }
  const categories=[];
  for(const name of names) {
    const entry=metrics.categories[name];
    if (!isObject(entry))return reject("Invalid category.");
    const pair={name};
    for(const role of ["A","B"]) {
      const v=entry[role];
      if (!isObject(v) || !Number.isInteger(v.correct)||!Number.isInteger(v.attempted)||
          v.correct<0||v.attempted<1||v.correct>v.attempted||v.attempted>16) {
        return reject("Invalid category counts.");
      }
      pair[role]={correct:v.correct,attempted:v.attempted};
    }
    categories.push(pair);
  }
  for(const role of ["A","B"]){
    if(categories.reduce((n,c)=>n+c[role].correct,0)!==models.find(m=>m.role===role).correct ||
       categories.reduce((n,c)=>n+c[role].attempted,0)!==metrics.cases_per_model){
      return reject("Category counts inconsistent.");
    }
  }
  if (!isObject(obj.selected_file_fingerprints) ||
      !isObject(obj.separate_driver_observations) ||
      Object.keys(obj.selected_file_fingerprints).some(k=>!["A","B"].includes(k)) ||
      Object.keys(obj.separate_driver_observations).some(k=>!["A","B"].includes(k))) {
    return reject("Unexpected hardware evidence fields.");
  }
  const devices={};
  for(const role of ["A","B"]){
    const f=obj.selected_file_fingerprints[role];
    if(f!==undefined && (!isObject(f)||!sha(f.sha256)||!Number.isInteger(f.size_bytes)
       || f.size_bytes<32 || f.header!=="GGUF" || f.bound_to_running_phiserve_process!==false
       || f.declared_by_operator!==true)){
      return reject("Untrusted file identity claim.");
    }
    const d=obj.separate_driver_observations[role];
    if(d!==undefined && (!isObject(d)||d.alias!==obj.aliases[role]||
       d.independently_attested!==false||d.same_execution_as_r9!==false||
       typeof d.driver_status!=="string"||!["NOT_SAMPLED","PROCESS_MEMORY_DRIVER_SELF_REPORT",
         "PROCESS_PRESENT_MEMORY_UNAVAILABLE","NVIDIA_SMI_UNAVAILABLE",
         "NVIDIA_SMI_QUERY_FAILED","NO_MATCHING_COMPUTE_PROCESS_OBSERVED",
         "SAMPLER_DID_NOT_STOP"].includes(d.driver_status)||
       (d.driver_status==="PROCESS_MEMORY_DRIVER_SELF_REPORT")!==
       (Number.isInteger(d.driver_peak_process_memory_mib)&&d.driver_peak_process_memory_mib>=0))){
      return reject("Unsafe or malformed driver telemetry claim.");
    }
    devices[role]={
      fingerprint:f?.sha256?.slice(0,14)??null,
      driverStatus:d?.driver_status??"NOT_PROVIDED",
      driverPeakMiB:d?.driver_peak_process_memory_mib??null
    };
  }
  return {
    recognized:true,verified:false,automaticPromotion:false,
    summaryPrefix:obj.source_receipt_sha256.slice(0,14),models,categories,devices,
    message:"Shape only. GPU figures are separate operator/driver self-reports and not measurements made during this R9 benchmark. File fingerprints are not proof the server loaded those weights."
  };
}
