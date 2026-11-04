import test from "node:test";
import assert from "node:assert/strict";
import {
  trialCount, sieveCount, referenceCount, runBrowserBenchmark,
  inspectHandoff, EMPTY_AUTHORITY, RUNGS
} from "./lab.js";

test("both algorithms match separate reference on edge and known inputs", () => {
  for (const [n, expected] of [[0, 0], [1, 0], [2, 1], [10, 4], [100, 25], [1000, 168]]) {
    for (const fn of [trialCount, sieveCount, referenceCount]) {
      assert.equal(fn(n), expected);
    }
  }
});

test("browser demo is bounded and never claims independent science", () => {
  assert.throws(() => runBrowserBenchmark({ n: 15001 }));
  assert.throws(() => runBrowserBenchmark({ candidate: "external" }));
  assert.throws(() => runBrowserBenchmark({ rounds: 0 }));
  const result = runBrowserBenchmark({ n: 1200, rounds: 1 });
  assert.equal(result.correct, true);
  assert.equal(result.rows.length, 3);
  assert.equal(result.automaticPromotion, false);
  assert.equal(result.independentlyReplicated, false);
  assert.equal(result.type, "browser_demonstration_only");
});

test("negative control cannot qualify as model improvement", () => {
  const result = runBrowserBenchmark({ candidate: "trial", n: 1200, rounds: 1 });
  assert.equal(result.negativeControl, true);
  assert.equal(result.automaticPromotion, false);
});

function packet() {
  return {
    schema: "phirsi.ecosystem_handoff.v1",
    source_kind: "r4",
    source_sha256: "a".repeat(64),
    handoff_sha256: "b".repeat(64),
    disposition: "REVIEW_ONLY",
    handoff_is_receipt_of_external_execution: false,
    policy: structuredClone(EMPTY_AUTHORITY),
    summary: { status: "OBSERVATION_CONSISTENT", exact_match_fraction: 0.75 }
  };
}

test("inspector reads an advisory policy without attesting its source", () => {
  const value = inspectHandoff(packet());
  assert.equal(value.structurallyRecognized, true);
  assert.equal(value.safePolicy, true);
  assert.equal(value.requiresSourceVerification, true);
  assert.equal(value.originAuthenticated, false);
  assert.equal(value.exactMatchFraction, 0.75);
});

test("forged authority is conspicuously rejected even when schema matches", () => {
  const invalid = packet();
  invalid.policy.merge_authorized = true;
  assert.equal(inspectHandoff(invalid).safePolicy, false);
  invalid.policy.merge_authorized = false;
  invalid.policy.authorized_actions = ["launch_mission"];
  assert.equal(inspectHandoff(invalid).safePolicy, false);
});

test("unknown shape and rogue status never become verified evidence", () => {
  assert.equal(inspectHandoff({}).structurallyRecognized, false);
  const invalid = packet();
  invalid.disposition = "EXECUTE";
  assert.equal(inspectHandoff(invalid).structurallyRecognized, false);
  const suspicious = packet();
  suspicious.summary.status = "<script>alert(1)</script>";
  assert.equal(inspectHandoff(suspicious).status, "NOT PROVIDED");
});

test("published roadmap distinguishes implemented and planned", () => {
  assert.deepEqual(RUNGS.map(item => item.status), [
    "merged", "merged", "merged", "merged", "merged", "planned", "planned"
  ]);
});
