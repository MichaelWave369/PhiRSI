import test from "node:test";
import assert from "node:assert/strict";
import {inspectSwitchIsolation} from "./switchIsolation.js";

function fixture(){
  const firstMs=[100,60,120,50];
  const repeatMs=[50,40,60,25];
  const blocks=firstMs.map((first,i)=>({
    block:i+1,round:Math.floor(i/2)+1,role:i%2?"B":"A",
    case_id:i<2?"upper":"add",
    requested_alias_changed:i>0,
    first_http_latency_ms:first,repeat_median_http_latency_ms:repeatMs[i],
    observed_first_over_repeat_ratio:first/repeatMs[i],
    first_exact_match:true,repeats_exact_match_count:2
  }));
  return {
    schema:"phirsi.switch_isolation_summary.v1",
    source_receipt_sha256:"a".repeat(64),summary_sha256:"b".repeat(64),
    case_set_sha256:"c".repeat(64),
    read_only_local_preview:true,source_authenticated:false,
    start_role:"A",repeat_requests_per_block:2,
    governance:{
      automatic_promotion:false,human_review_required:true,
      same_prompt_within_block:true,alias_change_is_not_model_reload_proof:true,
      cold_start_verified:false,warm_cache_verified:false,
      true_model_loading_ms_measured:false,decode_only_latency_measured:false,
      time_to_first_token_measured:false,served_weights_authenticated:false,
      gpu_execution_independently_verified:false,statistical_significance_claim:false,
      general_model_intelligence_gain_claim:false,external_network_or_weight_changes:false
    },
    assessment:{
      request_count:12,block_count:4,registered_model_count:2,
      requested_alias_change_count:3,blocks,
      models:{
        A:{alias:"model-a",request_count:6,exact_match_count:6,
          first_median_http_ms:110,repeat_median_http_ms:55,
          median_block_first_over_repeat_ratio:2,
          first_request_count:2,repeat_request_count:4},
        B:{alias:"model-b",request_count:6,exact_match_count:6,
          first_median_http_ms:55,repeat_median_http_ms:32.5,
          median_block_first_over_repeat_ratio:1.75,
          first_request_count:2,repeat_request_count:4}
      },
      decision:"DESCRIPTIVE_ONLY_NO_MODEL_LOADING_CLAIM",
      model_loading_time_ms:null,cold_start_time_ms:null,
      decode_only_tokens_per_second:null,
      automatic_promotion:false,human_review_required:true
    }
  };
}
test("valid R11 block summary remains unverified and has no load-time estimate",()=>{
  const v=inspectSwitchIsolation(fixture());
  assert.equal(v.recognized,true);
  assert.equal(v.verified,false);
  assert.equal(v.blocks.length,4);
  assert.equal(v.models[0].medianFirstOverRepeat,2);
  assert.equal(v.requestedAliasChanges,3);
  assert.equal(v.automaticPromotion,false);
});
test("forged load claims, changed blocks, scores or governance fail closed",()=>{
  const changes=[
    x=>x.governance.automatic_promotion=true,
    x=>x.governance.true_model_loading_ms_measured=true,
    x=>x.governance.cold_start_verified=true,
    x=>x.governance.gpu_execution_independently_verified=true,
    x=>x.assessment.model_loading_time_ms=450,
    x=>x.assessment.decision="CONFIRMED_MODEL_LOAD",
    x=>x.assessment.blocks[0].requested_alias_changed=true,
    x=>x.assessment.blocks[1].role="A",
    x=>x.assessment.blocks[0].first_http_latency_ms=-1,
    x=>x.assessment.blocks[2].case_id="unsafe",
    x=>x.assessment.blocks[3].observed_first_over_repeat_ratio=999,
    x=>x.assessment.models.B.exact_match_count=5,
    x=>x.assessment.models.A.first_median_http_ms=200,
    x=>x.assessment.requested_alias_change_count=4,
    x=>x.assessment.models.B.alias=x.assessment.models.A.alias,
  ];
  for(const change of changes){
    const f=fixture();change(f);
    assert.equal(inspectSwitchIsolation(f).recognized,false);
  }
});
test("unknown or malformed records display nothing",()=>{
  for(const input of [null,{},[],42,"string",{schema:"phirsi.switch_isolation_summary.v1"}]){
    assert.equal(inspectSwitchIsolation(input).recognized,false);
  }
});
test("B-first run uses the exact reversed block order",()=>{
  const f=fixture();
  f.start_role="B";
  const reversed=["B","A","B","A"];
  f.assessment.blocks.forEach((block,i)=>block.role=reversed[i]);
  f.assessment.models.A.alias="model-a";
  f.assessment.models.B.alias="model-b";
  f.assessment.models.A.first_median_http_ms=55;
  f.assessment.models.A.repeat_median_http_ms=32.5;
  f.assessment.models.A.median_block_first_over_repeat_ratio=1.75;
  f.assessment.models.B.first_median_http_ms=110;
  f.assessment.models.B.repeat_median_http_ms=55;
  f.assessment.models.B.median_block_first_over_repeat_ratio=2;
  const v=inspectSwitchIsolation(f);
  assert.equal(v.recognized,true);
  assert.deepEqual(v.blocks.map(x=>x.role),reversed);
});
