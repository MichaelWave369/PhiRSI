import test from "node:test";
import assert from "node:assert/strict";
import {inspectFieldEvidence} from "./fieldEvidence.js";

function sample(){
 const names=["arithmetic","extraction","instruction","ordering","text"];
 const counts=[4,1,1,2,4];
 const cats=Object.fromEntries(names.map((name,i)=>[name,{
   A:{correct:counts[i],attempted:counts[i]},
   B:{correct:counts[i],attempted:counts[i]}
 }]));
 return {
   schema:"phirsi.field_summary.v1",
   source_receipt_sha256:"a".repeat(64),summary_sha256:"b".repeat(64),
   read_only_browser_preview:true,not_authenticating_source:true,
   aliases:{A:"model-a",B:"model-b"},
   governance:{
    automatic_promotion:false,human_review_required:true,
    exact_match_on_public_toy_tasks_only:true,
    independent_execution_attestation:false,model_weight_binding_verified:false,
    gpu_execution_independently_verified:false,
    vram_from_independently_witnessed_measurement:false,
    statistical_significance_claim:false,intelligence_improvement_claim:false,
    external_network_or_model_download:false
   },
   metrics:{decision:"DESCRIPTIVE_ONLY_NO_WINNER",automatic_promotion:false,
     independent_replication:false,statistical_significance_calculated:false,
     model_intelligence_gain_claim:false,cases_per_model:12,total_post_requests:24,
     models:{
       A:{alias:"model-a",request_count:12,correct_count:12,exact_match_fraction:1,
          median_http_ms:30,p95_http_ms:35,provider_tokens_total:24,
          approx_total_http_tokens_per_second:70},
       B:{alias:"model-b",request_count:12,correct_count:12,exact_match_fraction:1,
          median_http_ms:41,p95_http_ms:48,provider_tokens_total:null,
          approx_total_http_tokens_per_second:null}
     },
     categories:cats
   },
   selected_file_fingerprints:{},
   separate_driver_observations:{}
 };
}

test("12-task summary shape is explicitly unverified",()=>{
 const x=inspectFieldEvidence(sample());
 assert.equal(x.recognized,true);
 assert.equal(x.verified,false);
 assert.equal(x.models[0].correct,12);
 assert.equal(x.categories.length,5);
 assert.equal(x.devices.A.driverPeakMiB,null);
});

test("forged GPU attribution or promotion is rejected",()=>{
 for(const change of [
   o=>o.governance.model_weight_binding_verified=true,
   o=>o.governance.automatic_promotion=true,
   o=>o.metrics.decision="CERTIFIED_WINNER",
   o=>o.metrics.models.B.correct_count=15,
   o=>o.metrics.categories.text.A.correct=0,
   o=>o.selected_file_fingerprints.A={sha256:"a".repeat(64),size_bytes:100,
      header:"GGUF",declared_by_operator:true,bound_to_running_phiserve_process:true},
   o=>o.separate_driver_observations.A={alias:"model-a",driver_status:"PROCESS_MEMORY_DRIVER_SELF_REPORT",
      driver_peak_process_memory_mib:4000,independently_attested:true,same_execution_as_r9:false}
 ]){
   const o=sample();change(o);
   assert.equal(inspectFieldEvidence(o).recognized,false);
 }
});

test("unknown input denied",()=>{
 for(const x of [null,[],42,{},{}])assert.equal(inspectFieldEvidence(x).recognized,false);
});

test("separate driver samples may be absent without guessing",()=>{
 const o=sample();o.separate_driver_observations.A={
   alias:"model-a",driver_status:"PROCESS_PRESENT_MEMORY_UNAVAILABLE",
   driver_peak_process_memory_mib:null,independently_attested:false,
   same_execution_as_r9:false
 };
 const x=inspectFieldEvidence(o);
 assert.equal(x.recognized,true);
 assert.equal(x.devices.A.driverPeakMiB,null);
});
