import test from "node:test";
import assert from "node:assert/strict";
import {inspectWorkstation} from "./workstation.js";

function sample(){
  const rows=[369,370,371].map((seed,i)=>({
    sequence:i+1,operator_run_label:i===0?"initial":"repeat",seed,
    r9_receipt_sha256:(""+(i+1)).repeat(64),
    model_a_correct:12,model_b_correct:11,
    model_a_accuracy:1,model_b_accuracy:.916667,
    model_a_median_http_ms:[30,40,44][i],
    model_b_median_http_ms:[50,60,66][i],
    includes_separate_phi_serve_telemetry:false,
    historical_execution_authenticated:false
  }));
  return {
    schema:"phirsi.workstation_acceptance_summary.v1",
    source_dossier_sha256:"a".repeat(64),summary_sha256:"b".repeat(64),
    shape_only_browser_preview:true,original_receipts_not_in_browser_summary:true,
    independently_authenticated:false,
    model_aliases:{A:"model-a",B:"model-b"},
    cases_per_model_per_run:12,
    thresholds:{quality_floor:.75,max_repeat_median_latency_spread:2},
    governance:{
      automatic_promotion:false,human_review_required:true,
      real_model_execution_authenticated:false,machine_identity_authenticated:false,
      model_weights_bound_to_server:false,historical_timings_authenticated:false,
      cold_start_verified:false,warm_cache_verified:false,
      gpu_execution_independently_verified:false,
      driver_memory_from_same_r10_run:false,statistical_significance_claim:false,
      general_intelligence_improvement_claim:false,
      network_or_model_execution_by_r10:false,model_deployment_authorized:false
    },
    assessment:{
      run_count:3,entries:rows,
      run_order_labels_are_operator_declared_not_cold_warm_attestations:true,
      operator_selected_file_evidence:{
        A:{declared_file_hash_prefix:null,operator_selected_fingerprint_present_all_runs:false,
          server_weight_binding_verified:false},
        B:{declared_file_hash_prefix:null,operator_selected_fingerprint_present_all_runs:false,
          server_weight_binding_verified:false}
      },
      minimum_exact_match_fraction_observed:{A:1,B:.916667},
      repeat_only_median_latency_ms:{A:42,B:63},
      repeat_only_max_over_min_latency_ratio:{A:1.1,B:1.1},
      quality_threshold_met:true,repeat_stability_threshold_met:true,
      status:"MEETS_CONFIGURED_THRESHOLDS",
      qualified_as_independently_verified_workstation:false,
      automatic_model_selection:false,human_review_required:true
    }
  };
}
test("valid review summary never becomes hardware validation",()=>{
  const x=inspectWorkstation(sample());
  assert.equal(x.recognized,true);
  assert.equal(x.verified,false);
  assert.equal(x.rows.length,3);
  assert.equal(x.ratios.A,1.1);
  assert.equal(x.automaticPromotion,false);
});
test("tampered authority, forged gate and changed scores fail closed",()=>{
  const changes=[
    x=>x.governance.automatic_promotion=true,
    x=>x.governance.cold_start_verified=true,
    x=>x.governance.model_deployment_authorized=true,
    x=>x.assessment.qualified_as_independently_verified_workstation=true,
    x=>x.assessment.status="DEPLOYMENT_APPROVED",
    x=>x.assessment.status="DOES_NOT_MEET_CONFIGURED_THRESHOLDS",
    x=>x.assessment.entries[1].model_a_correct=0,
    x=>x.assessment.entries[2].model_b_median_http_ms=1000,
    x=>x.assessment.repeat_only_max_over_min_latency_ratio.A=.1,
    x=>x.assessment.entries[1].operator_run_label="cold_verified",
    x=>x.assessment.operator_selected_file_evidence.A.server_weight_binding_verified=true,
    x=>x.model_aliases.A=x.model_aliases.B
  ];
  for(const change of changes){
    const value=sample();change(value);
    assert.equal(inspectWorkstation(value).recognized,false);
  }
});
test("failure is displayed as a failure not an approved deployment",()=>{
  const x=sample();
  x.thresholds.quality_floor=1;
  x.assessment.quality_threshold_met=false;
  x.assessment.status="DOES_NOT_MEET_CONFIGURED_THRESHOLDS";
  const value=inspectWorkstation(x);
  assert.equal(value.recognized,true);
  assert.equal(value.qualityMet,false);
  assert.equal(value.verified,false);
});
test("unrecognized inputs never execute actions",()=>{
  for(const x of [null,[],{},42,"no",{"schema":"phirsi.workstation_acceptance_summary.v1"}])
    assert.equal(inspectWorkstation(x).recognized,false);
});
