import test from "node:test";
import assert from "node:assert/strict";
import { inspectModelPair } from "./modelPair.js";

function sample() {
  const pairs = ["uppercase","arithmetic","alphabetical"].map((case_id,i)=>({
    round:1,case_id,observed_a_over_b_latency_ratio: i===0?1.5:0.9,
    a_exact_match:true,b_exact_match:i!==1
  }));
  return {
    schema:"phirsi.phiserve_pair_summary.v1",
    source_receipt_sha256:"a".repeat(64),summary_sha256:"b".repeat(64),
    model_a_alias:"model-a",model_b_alias:"model-b",
    fixed_case_count:3,rounds:1,browser_only_shape_inspection:true,report_is_not_authenticated:true,
    governance:{
      automatic_promotion:false,human_review_required:true,
      model_identity_authenticated:false,distinct_weights_verified:false,
      inference_execution_independently_attested:false,
      historical_timings_authenticated:false,gpu_vram_measured:false,
      quality_is_only_fixed_exact_match:true,statistical_significance_claim:false,
      model_intelligence_improvement_claim:false,network_outside_loopback:false,
      model_downloads_or_weight_modifications:false
    },
    metrics:{
      models:{
        A:{registered_alias:"model-a",request_count:3,exact_match_count:3,exact_match_fraction:1,
           median_end_to_end_latency_ms:42,p95_end_to_end_latency_ms:50,
           provider_reported_completion_tokens:6,estimated_end_to_end_tokens_per_sec:50},
        B:{registered_alias:"model-b",request_count:3,exact_match_count:2,exact_match_fraction:.666667,
           median_end_to_end_latency_ms:33,p95_end_to_end_latency_ms:48,
           provider_reported_completion_tokens:6,estimated_end_to_end_tokens_per_sec:64}
      },
      paired_task_count:3,paired_observations:pairs,
      median_observed_a_over_b_latency_ratio:.9,
      a_faster_pair_count:2,b_faster_pair_count:1,tie_pair_count:0,
      decision:"DESCRIPTIVE_ONLY_NO_WINNER",automatic_promotion:false,
      gpu_vram_measured:false,task_quality_generalization_claim:false,
      decode_only_throughput_measured:false,first_token_latency_measured:false
    }
  };
}

test("display only model-alias observations with explicit unverified label",()=>{
  const x=inspectModelPair(sample());
  assert.equal(x.recognized,true);
  assert.equal(x.verified,false);
  assert.equal(x.permittedActions,0);
  assert.equal(x.models[0].fraction,1);
  assert.equal(x.models[1].fraction,.666667);
  assert.equal(x.pairs,3);
  assert.equal(x.winsA,2);
});

test("reject forged authority and invented quality claims",()=>{
  for (const changed of [
    x=>x.governance.automatic_promotion=true,
    x=>x.governance.model_identity_authenticated=true,
    x=>x.governance.independent_model_approval=true,
    x=>x.metrics.decision="B_IS_SUPERINTELLIGENT",
    x=>x.metrics.task_quality_generalization_claim=true,
    x=>x.metrics.models.B.exact_match_count=3,
    x=>x.metrics.models.A.registered_alias="wrong",
    x=>x.metrics.paired_task_count=7,
    x=>x.model_b_alias=x.model_a_alias,
    x=>x.metrics.b_faster_pair_count=3
  ]){
    const x=sample();changed(x);assert.equal(inspectModelPair(x).recognized,false);
  }
});

test("refuse malformed JSON shapes",()=>{
  for(const value of [null,[],{},42,"nothing",{schema:"phirsi.phiserve_pair_summary.v1"}]){
    assert.equal(inspectModelPair(value).recognized,false);
  }
});

test("unknown usage remains unmeasured",()=>{
  const x=sample();
  x.metrics.models.A.provider_reported_completion_tokens=null;
  x.metrics.models.A.estimated_end_to_end_tokens_per_sec=null;
  const result=inspectModelPair(x);
  assert.equal(result.recognized,true);
  assert.equal(result.models[0].reportedRate,null);
});
