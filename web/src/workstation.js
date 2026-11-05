/** R10 browser-only preview. This is not a receipt verifier or a GPU witness. */
const GUARDS = {
  automatic_promotion:false,
  human_review_required:true,
  real_model_execution_authenticated:false,
  machine_identity_authenticated:false,
  model_weights_bound_to_server:false,
  historical_timings_authenticated:false,
  cold_start_verified:false,
  warm_cache_verified:false,
  gpu_execution_independently_verified:false,
  driver_memory_from_same_r10_run:false,
  statistical_significance_claim:false,
  general_intelligence_improvement_claim:false,
  network_or_model_execution_by_r10:false,
  model_deployment_authorized:false
};
const reject = reason => ({recognized:false,verified:false,automaticPromotion:false,reason});
const obj = x => x!==null && typeof x==="object" && !Array.isArray(x);
const sha = x => typeof x==="string" && /^[a-f0-9]{64}$/.test(x);
const alias = x => typeof x==="string" && /^[A-Za-z0-9][A-Za-z0-9_.:/+\-]{0,127}$/.test(x)
  && !x.includes("//") && !x.includes("..");
const value = x => typeof x==="number" && Number.isFinite(x);
const bounded = (x,min,max) => value(x) && x>=min && x<=max;
const nearly = (a,b) => Math.abs(a-b)<0.000002;
const CONFIGURED = new Set(["MEETS_CONFIGURED_THRESHOLDS","DOES_NOT_MEET_CONFIGURED_THRESHOLDS"]);

export function inspectWorkstation(data) {
  if(!obj(data) || data.schema!=="phirsi.workstation_acceptance_summary.v1" ||
     !sha(data.source_dossier_sha256) || !sha(data.summary_sha256) ||
     data.shape_only_browser_preview!==true ||
     data.original_receipts_not_in_browser_summary!==true ||
     data.independently_authenticated!==false ||
     !obj(data.model_aliases) || !alias(data.model_aliases.A) ||
     !alias(data.model_aliases.B) || data.model_aliases.A===data.model_aliases.B ||
     !obj(data.governance) ||
     Object.keys(data.governance).sort().join("|")!==Object.keys(GUARDS).sort().join("|") ||
     Object.entries(GUARDS).some(([key,expected])=>data.governance[key]!==expected) ||
     !obj(data.thresholds) || !bounded(data.thresholds.quality_floor,.5,1) ||
     !bounded(data.thresholds.max_repeat_median_latency_spread,1,5) ||
     ![12,24].includes(data.cases_per_model_per_run)) {
    return reject("Unknown R10 summary format or unsafe authority/provenance claim.");
  }
  const a=data.assessment;
  if(!obj(a) || !CONFIGURED.has(a.status) ||
     !Array.isArray(a.entries) || a.entries.length<3 || a.entries.length>6 ||
     a.run_count!==a.entries.length ||
     a.run_order_labels_are_operator_declared_not_cold_warm_attestations!==true ||
     a.qualified_as_independently_verified_workstation!==false ||
     a.automatic_model_selection!==false || a.human_review_required!==true ||
     !obj(a.minimum_exact_match_fraction_observed) ||
     !obj(a.repeat_only_median_latency_ms) ||
     !obj(a.repeat_only_max_over_min_latency_ratio) ||
     !obj(a.operator_selected_file_evidence)) {
    return reject("Malformed acceptance assessment or unsupported acceptance status.");
  }
  const rows=[];
  for(let i=0;i<a.entries.length;i++){
    const r=a.entries[i];
    if(!obj(r) || r.sequence!==i+1 || r.operator_run_label!==(i===0?"initial":"repeat") ||
       !Number.isInteger(r.seed) || r.seed<0 || r.seed>0xffffffff ||
       (i>0 && r.seed!==a.entries[0].seed+i) || !sha(r.r9_receipt_sha256) ||
       r.historical_execution_authenticated!==false ||
       typeof r.includes_separate_phi_serve_telemetry!=="boolean"){
      return reject("Run order or unverified source data is inconsistent.");
    }
    for(const role of ["a","b"]){
      const correct=r["model_"+role+"_correct"];
      const accuracy=r["model_"+role+"_accuracy"];
      const ms=r["model_"+role+"_median_http_ms"];
      if(!Number.isInteger(correct)||correct<0||correct>data.cases_per_model_per_run ||
         !bounded(accuracy,0,1) ||
         !nearly(accuracy,correct/data.cases_per_model_per_run) ||
         !bounded(ms,.001,61000)){
        return reject("Invalid task quality or timing observation.");
      }
    }
    rows.push({sequence:r.sequence,label:r.operator_run_label,seed:r.seed,
      aFraction:r.model_a_accuracy,bFraction:r.model_b_accuracy,
      aMs:r.model_a_median_http_ms,bMs:r.model_b_median_http_ms,
      aCorrect:r.model_a_correct,bCorrect:r.model_b_correct,
      externalDriverReport:r.includes_separate_phi_serve_telemetry});
  }
  const repeat=rows.slice(1);
  const ratios={};
  const minima={};
  for(const [role,key] of [["A","aMs"],["B","bMs"]]){
    const vals=repeat.map(r=>r[key]);
    const ratio=Math.round(1e6*Math.max(...vals)/Math.min(...vals))/1e6;
    const declared=a.repeat_only_max_over_min_latency_ratio[role];
    if(!bounded(declared,1,61000) || !nearly(declared,ratio))
      return reject("Repeat stability ratio contradicts the run data.");
    ratios[role]=declared;
    const accuracies=rows.map(r=>r[role==="A"?"aFraction":"bFraction"]);
    const min=Math.min(...accuracies);
    if(!bounded(a.minimum_exact_match_fraction_observed[role],0,1) ||
       !nearly(a.minimum_exact_match_fraction_observed[role],min))
      return reject("Minimum quality claims differ from run data.");
    minima[role]=min;
    if(!bounded(a.repeat_only_median_latency_ms[role],.001,61000))
      return reject("Repeat latency summary is malformed.");
    const sorted=[...vals].sort((x,y)=>x-y);
    const center=sorted.length%2?sorted[Math.floor(sorted.length/2)]:
      (sorted[sorted.length/2-1]+sorted[sorted.length/2])/2;
    if(Math.abs(a.repeat_only_median_latency_ms[role]-center)>.0011)
      return reject("Repeat median disagrees with the run observations.");
  }
  const quality=Object.values(minima).every(x=>x>=data.thresholds.quality_floor);
  const stable=Object.values(ratios).every(x=>x<=data.thresholds.max_repeat_median_latency_spread);
  if(a.quality_threshold_met!==quality ||
     a.repeat_stability_threshold_met!==stable ||
     a.status!==(quality&&stable?"MEETS_CONFIGURED_THRESHOLDS":"DOES_NOT_MEET_CONFIGURED_THRESHOLDS")){
    return reject("Reported acceptance status does not follow the plan thresholds.");
  }
  for(const role of ["A","B"]){
    const meta=a.operator_selected_file_evidence[role];
    if(!obj(meta) || meta.server_weight_binding_verified!==false ||
       typeof meta.operator_selected_fingerprint_present_all_runs!=="boolean" ||
       (meta.operator_selected_fingerprint_present_all_runs?
         !(typeof meta.declared_file_hash_prefix==="string" &&
            /^[a-f0-9]{16}$/.test(meta.declared_file_hash_prefix)):
         meta.declared_file_hash_prefix!==null)){
      return reject("Untrustworthy file-identity claim.");
    }
  }
  return {
    recognized:true,verified:false,automaticPromotion:false,
    status:a.status.replaceAll("_"," "),
    planQualityFloor:data.thresholds.quality_floor,
    planMaxRepeatSpread:data.thresholds.max_repeat_median_latency_spread,
    qualityMet:quality,stabilityMet:stable,
    modelA:data.model_aliases.A,modelB:data.model_aliases.B,
    rows,ratios,minima,fingerprintEvidence:a.operator_selected_file_evidence,
    sourcePrefix:data.source_dossier_sha256.slice(0,14),
    warning:"Only declared receipt structure and arithmetic were checked in-browser. The original R9 runs, model weights, machine identity, cold/warm state and historical timings are NOT independently verified."
  };
}
