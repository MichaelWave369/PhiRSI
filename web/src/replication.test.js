import test from "node:test";
import assert from "node:assert/strict";
import { inspectReplication } from "./replication.js";

function fixture() {
  return {
    schema: "phirsi.replication_packet.v1",
    manifest_sha256: "a".repeat(64),
    r6_runner_code_sha256: "b".repeat(64),
    comparison_settings_sha256: "c".repeat(64),
    policy: {
      review_only: true, human_review_required: true,
      automatic_promotion: false, writes_to_other_repositories: false,
      external_experiments_launched: false,
      model_intelligence_improvement_claim: false,
      statistical_significance_claim: false,
      independent_hosts_authenticated: false,
      historical_timings_authenticated: false,
      cryptographic_signature_present: false
    },
    entries: [
      {id:"run-01",archive_path:"runs/run-01.json",canonical_source_sha256:"d".repeat(64),
       ledger_sha256:"f".repeat(64),plan_sha256:"1".repeat(64),development_seed:369,
       reported_status:"OBSERVATIONAL_SUPPORT",event_count:3,
       control_observed_ratio:1.02,evaluation_observed_ratio:2.2},
      {id:"run-02",archive_path:"runs/run-02.json",canonical_source_sha256:"e".repeat(64),
       ledger_sha256:"3".repeat(64),plan_sha256:"2".repeat(64),development_seed:370,
       reported_status:"NOT_SUPPORTED",event_count:3,
       control_observed_ratio:1.01,evaluation_observed_ratio:1.1}
    ],
    summary: {
      run_count:2,evaluated_run_count:2,
      support_count:1,not_supported_count:1,
      no_eligible_count:0,budget_stopped_count:0,
      evaluation_median_observed_ratio:1.65,
      independent_replication_established:false,
      confidence_interval_calculated:false,
      quality_of_model_measured:false
    }
  };
}

test("R7 manifest shows only unverified descriptive comparisons", () => {
  const data = inspectReplication(fixture());
  assert.equal(data.recognized,true);
  assert.equal(data.runCount,2);
  assert.equal(data.supportCount,1);
  assert.equal(data.entries[0].observedRatio,2.2);
  assert.equal(data.independentlyVerified,false);
  assert.equal(data.promotionAllowed,false);
});

test("forged authority or significance rejected", () => {
  for (const modify of [
    x=>{x.policy.automatic_promotion=true;},
    x=>{x.policy.independent_hosts_authenticated=true;},
    x=>{x.policy.statistical_significance_claim=true;},
    x=>{x.policy.merge_authorized=true;},
    x=>{x.summary.independent_replication_established=true;},
    x=>{x.summary.support_count=2;},
    x=>{x.entries[1].development_seed=369;},
    x=>{x.entries[1].ledger_sha256="f".repeat(64);},
    x=>{x.entries[1].reported_status="SUPERINTELLIGENCE";},
    x=>{x.entries.push(x.entries[0]);},
  ]) {
    const item = fixture(); modify(item);
    assert.equal(inspectReplication(item).recognized,false);
  }
});

test("negative and budget stopped statuses preserved", () => {
  const data=fixture();
  data.entries[0].reported_status="NO_ELIGIBLE_CANDIDATE";
  data.entries[0].evaluation_observed_ratio=null;
  data.entries[0].event_count=2;
  data.entries[1].reported_status="BUDGET_STOPPED";
  data.entries[1].evaluation_observed_ratio=null;
  data.entries[1].event_count=1;
  Object.assign(data.summary, {
    support_count:0,not_supported_count:0,no_eligible_count:1,
    budget_stopped_count:1,evaluated_run_count:0,
    evaluation_median_observed_ratio:null
  });
  const review=inspectReplication(data);
  assert.equal(review.recognized,true);
  assert.equal(review.evaluatedCount,0);
  assert.equal(review.medianObservedRatio,null);
});

test("malformed and unsupported formats refused", () => {
  for (const value of [null, {}, [], "ZIP", {schema:"phirsi.replication_packet.v1"}])
    assert.equal(inspectReplication(value).recognized,false);
});
