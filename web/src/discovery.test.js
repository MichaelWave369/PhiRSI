import test from "node:test";
import assert from "node:assert/strict";
import { inspectDiscovery } from "./discovery.js";

function fixture() {
  return {
    schema: "phirsi.discovery_ledger.v1",
    ledger_sha256: "a".repeat(64),
    elapsed_is_unattested: true,
    plan: {
      schema: "phirsi.discovery_plan.v1",
      plan_sha256: "b".repeat(64),
      candidates: ["trial", "sieve"]
    },
    governance: {
      automatic_promotion: false,
      human_review_required: true,
      candidate_code_execution: "built_in_registered_only",
      external_network_calls: false,
      model_weight_changes: false,
      independent_timing_replication: false,
      model_intelligence_gain_claim: false
    },
    events: [
      {sequence: 0, phase: "development", candidate: "trial", event_sha256: "c".repeat(64),
       receipt: {summary: {geomean_observed_speedup: 1.03, correctness_passed: true}}},
      {sequence: 1, phase: "development", candidate: "sieve", event_sha256: "d".repeat(64),
       receipt: {summary: {geomean_observed_speedup: 2.4, correctness_passed: true}}},
      {sequence: 2, phase: "evaluation", candidate: "sieve", event_sha256: "e".repeat(64),
       receipt: {summary: {geomean_observed_speedup: 2.1, correctness_passed: true}}}
    ],
    decision: {
      status: "OBSERVATIONAL_SUPPORT", selected_candidate: "sieve",
      evaluated_candidate: "sieve", automatic_promotion: false,
      human_review_required: true, independent_replication: false,
      model_intelligence_improvement_claim: false
    }
  };
}

test("R6 file can be visualized only as unverified shape", () => {
  const info = inspectDiscovery(fixture());
  assert.equal(info.recognized, true);
  assert.equal(info.policySafe, true);
  assert.equal(info.entries.length, 3);
  assert.equal(info.selectedCandidate, "sieve");
  assert.equal(info.evalObservedSpeedup, 2.1);
  assert.equal(info.originAuthenticated, false);
  assert.equal(info.replayVerified, false);
  assert.equal(info.automaticPromotion, false);
});

test("forged or permissive governance is rejected", () => {
  for (const mutation of [
    v => {v.governance.merge_authorized = true;},
    v => {v.governance.automatic_promotion = true;},
    v => {v.decision.automatic_promotion = true;},
    v => {v.decision.selected_candidate = "trial";},
    v => {v.decision.status = "AGI_DISCOVERED";},
    v => {v.plan.candidates = ["trial", "arbitrary-code"];},
    v => {v.events.push(v.events[2]);},
    v => {v.events[0].candidate = "sieve";},
    v => {v.events[2].receipt.summary.correctness_passed = false;}
  ]) {
    const bad = fixture();
    mutation(bad);
    assert.equal(inspectDiscovery(bad).recognized, false);
  }
});

test("incomplete but budget-stopped run is displayed without false success claim", () => {
  const value = fixture();
  value.events = value.events.slice(0, 1);
  value.decision.status = "BUDGET_STOPPED";
  value.decision.selected_candidate = null;
  value.decision.evaluated_candidate = null;
  const info = inspectDiscovery(value);
  assert.equal(info.recognized, true);
  assert.equal(info.status, "BUDGET STOPPED");
  assert.equal(info.evalObservedSpeedup, null);
});

test("malformed values are refused", () => {
  for (const item of [null, "", {}, [], {schema:"phirsi.discovery_ledger.v1"}]) {
    assert.equal(inspectDiscovery(item).recognized, false);
  }
});
