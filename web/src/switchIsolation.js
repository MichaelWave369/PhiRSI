/** R11 local summary preview. Untrusted JSON is never executed or uploaded.
 * This parser verifies a narrow shape and internal aggregates, NOT real
 * model loading, hardware state, source authenticity or historical timings.
 */
const GUARD={
  automatic_promotion:false,human_review_required:true,
  same_prompt_within_block:true,alias_change_is_not_model_reload_proof:true,
  cold_start_verified:false,warm_cache_verified:false,
  true_model_loading_ms_measured:false,decode_only_latency_measured:false,
  time_to_first_token_measured:false,served_weights_authenticated:false,
  gpu_execution_independently_verified:false,statistical_significance_claim:false,
  general_model_intelligence_gain_claim:false,
  external_network_or_weight_changes:false
};
const fail=reason=>({recognized:false,verified:false,reason,automaticPromotion:false});
const obj=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
const sha=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const alias=x=>typeof x==="string"&&/^[A-Za-z0-9][A-Za-z0-9_.:/+\-]{0,127}$/.test(x)&&!x.includes("//")&&!x.includes("..");
const num=x=>typeof x==="number"&&Number.isFinite(x);
const range=(x,lo,hi)=>num(x)&&x>=lo&&x<=hi;
const approx=(x,y,delta=.0011)=>Math.abs(x-y)<delta;
const median=xs=>{const ys=[...xs].sort((a,b)=>a-b);return ys.length%2?ys[Math.floor(ys.length/2)]:(ys[ys.length/2-1]+ys[ys.length/2])/2;};
const rounded=(x,places)=>Math.round(x*(10**places))/(10**places);

export function inspectSwitchIsolation(data){
  if(!obj(data)||data.schema!=="phirsi.switch_isolation_summary.v1"||
     !sha(data.source_receipt_sha256)||!sha(data.summary_sha256)||
     !sha(data.case_set_sha256)||data.read_only_local_preview!==true||
     data.source_authenticated!==false||!["A","B"].includes(data.start_role)||
     ![2,3].includes(data.repeat_requests_per_block)||!obj(data.governance)||
     Object.keys(data.governance).sort().join("|")!==Object.keys(GUARD).sort().join("|")||
     Object.entries(GUARD).some(([key,value])=>data.governance[key]!==value)){
    return fail("Invalid R11 summary or unauthorized model-loading claim.");
  }
  const m=data.assessment,repeats=data.repeat_requests_per_block;
  if(!obj(m)||m.decision!=="DESCRIPTIVE_ONLY_NO_MODEL_LOADING_CLAIM"||
     m.model_loading_time_ms!==null||m.cold_start_time_ms!==null||
     m.decode_only_tokens_per_second!==null||
     m.automatic_promotion!==false||m.human_review_required!==true||
     m.request_count!==4*(repeats+1)||m.block_count!==4||
     m.registered_model_count!==2||
     m.requested_alias_change_count!==3||
     !Array.isArray(m.blocks)||m.blocks.length!==4||!obj(m.models)){
    return fail("Inconsistent blocked inference schedule or impossible metrics.");
  }
  const first=data.start_role,second=first==="A"?"B":"A";
  const roles=[first,second,first,second];
  const caseIds=["upper","upper","add","add"];
  const blocks=[];
  for(let i=0;i<4;i++){
    const b=m.blocks[i];
    if(!obj(b)||b.block!==i+1||b.round!==Math.floor(i/2)+1||
       b.role!==roles[i]||b.case_id!==caseIds[i]||
       b.requested_alias_changed!==(i>0)||
       typeof b.first_exact_match!=="boolean"||
       !Number.isInteger(b.repeats_exact_match_count)||
       b.repeats_exact_match_count<0||b.repeats_exact_match_count>repeats||
       !range(b.first_http_latency_ms,.001,61000)||
       !range(b.repeat_median_http_latency_ms,.001,61000)||
       !range(b.observed_first_over_repeat_ratio,.000001,10000000)||
       !approx(b.observed_first_over_repeat_ratio,
         rounded(b.first_http_latency_ms/b.repeat_median_http_latency_ms,6),.000003)){
      return fail("Block phase, alias-change flag or first/repeat latency is inconsistent.");
    }
    blocks.push({
      block:b.block,round:b.round,role:b.role,caseId:b.case_id,
      firstMs:b.first_http_latency_ms,repeatMs:b.repeat_median_http_latency_ms,
      ratio:b.observed_first_over_repeat_ratio,
      requestedAliasChanged:b.requested_alias_changed,
      correct: Number(b.first_exact_match)+b.repeats_exact_match_count
    });
  }
  const models=[];
  for(const role of ["A","B"]){
    const model=m.models[role];
    const own=blocks.filter(b=>b.role===role);
    if(!obj(model)||!alias(model.alias)||model.request_count!==2*(repeats+1)||
       model.first_request_count!==2||model.repeat_request_count!==2*repeats||
       !Number.isInteger(model.exact_match_count)||model.exact_match_count<0||
       model.exact_match_count>model.request_count||
       model.exact_match_count!==own.reduce((n,b)=>n+b.correct,0)||
       !range(model.first_median_http_ms,.001,61000)||
       !range(model.repeat_median_http_ms,.001,61000)||
       !range(model.median_block_first_over_repeat_ratio,.000001,10000000)||
       !approx(model.first_median_http_ms,
         rounded(median(own.map(b=>b.firstMs)),3))||
       !approx(model.median_block_first_over_repeat_ratio,
         rounded(median(own.map(b=>b.ratio)),6),.000003)){
      return fail("Model score, first-request median or ratios do not match blocks.");
    }
    models.push({
      role,alias:model.alias,requests:model.request_count,
      correct:model.exact_match_count,firstMedianMs:model.first_median_http_ms,
      repeatMedianMs:model.repeat_median_http_ms,
      medianFirstOverRepeat:model.median_block_first_over_repeat_ratio
    });
  }
  if(models[0].alias===models[1].alias)return fail("Aliases must be distinct.");
  return {
    recognized:true,verified:false,automaticPromotion:false,
    receiptPrefix:data.source_receipt_sha256.slice(0,14),
    startRole:first,repeatsPerBlock:repeats,blocks,models,
    requestedAliasChanges:3,
    warning:"This is a local shape-only report. A slower first request is not proof of a model reload, genuine cold start, warm cache, decode latency or GPU residency. The original receipt and historical timings were not independently authenticated."
  };
}
