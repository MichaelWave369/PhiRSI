import React, { useState } from "react";
import { inspectReplication } from "./replication.js";
import "./replication.css";

export default function ReplicationDesk() {
  const [review, setReview] = useState(null);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");

  async function onFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    setReview(null);
    setError("");
    setFileName("");
    if (!file) return;
    if (file.size > 64000) {
      setError("The JSON comparison summary exceeds the 64 KB preview limit.");
      return;
    }
    try {
      const parsed = JSON.parse(await file.text());
      setReview(inspectReplication(parsed));
      setFileName(file.name);
    } catch {
      setError("The file was not valid JSON. Nothing was uploaded.");
    }
  }

  const max = review?.recognized
    ? Math.max(1, ...review.entries.map(e => e.observedRatio || 0))
    : 1;

  return (
    <section className="section replication-desk" id="replication">
      <div className="section-heading">
        <div>
          <p className="eyebrow"><span className="square-dot" /> 05 / OPEN REPLICATION</p>
          <h2>One experiment is a story.<br/>Several runs are evidence to compare.</h2>
          <p className="section-description">
            Inspect a locally exported R7 comparison manifest to see differing outcomes
            without hiding failed, stopped or inconclusive runs.
          </p>
        </div>
        <span className="mini-flag">R7 / REVIEW ONLY</span>
      </div>
      <div className="replication-layout">
        <div className="replication-sidebar">
          <div className="panel-title"><span className="panel-symbol">◇</span> REPLICATION PACKET <span className="panel-aside">LOCAL VIEWER</span></div>
          <div className="replication-instruction">
            <span>01</span>
            <div><strong>Run R6 with separate seeds</strong><p>Save two to six original ledgers. Keep the same experiment design.</p></div>
          </div>
          <div className="replication-instruction">
            <span>02</span>
            <div><strong>Pack and verify with Python</strong><p>The R7 CLI replays the original correctness checks and preserves raw evidence in a bounded ZIP.</p></div>
          </div>
          <div className="replication-instruction">
            <span>03</span>
            <div><strong>Export a comparison summary</strong><p>Use the R7 summary command to create a review-only JSON file, then open it here.</p></div>
          </div>
          <label htmlFor="r7-summary-file" className="replication-upload">
            <span aria-hidden="true">⇧</span> INSPECT LOCAL R7 SUMMARY
          </label>
          <input id="r7-summary-file" type="file" className="visually-hidden"
                 accept="application/json,.json" onChange={onFile} />
          <p className="disclaimer-small">
            This page cannot open ZIP bundles, replay Python code, authenticate hardware,
            validate checksums or establish that runs came from independent machines.
          </p>
        </div>
        <div className="replication-results">
          <div className="panel-title"><span className="panel-symbol">▥</span> COMPARATIVE RESEARCH <span className="panel-aside">NO REMOTE DATA</span></div>
          {error && <p className="error-message" role="alert">{error}</p>}
          {!review && !error && (
            <div className="replication-placeholder">
              <span className="replication-globe" aria-hidden="true">Φ</span>
              <strong>No comparison file loaded.</strong>
              <p>Import an R7 manifest summary exported from the Python verifier. No files are transmitted.</p>
            </div>
          )}
          {review && !review.recognized && (
            <div role="alert" className="discovery-alert">
              <strong>UNRECOGNIZED / NOT ACCEPTED</strong>
              <p>{review.error}</p>
            </div>
          )}
          {review?.recognized && (
            <div className="replication-report" aria-live="polite">
              <div className="replication-metrics">
                <div><small>RUNS RECORDED</small><strong>{review.runCount}</strong></div>
                <div><small>WITH EVALUATIONS</small><strong>{review.evaluatedCount}</strong></div>
                <div><small>OBSERVATIONAL SUPPORT</small><strong>{review.supportCount}</strong></div>
              </div>
              <div className="replication-subtitle"><span>INDIVIDUAL RUN RESULTS</span><span>RATIO / REPORTED</span></div>
              <div role="list" className="replication-runs">
                {review.entries.map(item => (
                  <div role="listitem" key={item.id} className="replication-run">
                    <div className="replication-run-meta">
                      <strong>{item.id.toUpperCase()}</strong>
                      <span>SEED {item.seed}</span>
                      <small>{item.status}</small>
                    </div>
                    <div className="replication-run-observation">
                      {item.observedRatio === null ? (
                        <div className="replication-missing">NO QUALIFYING EVALUATION DATA</div>
                      ) : (
                        <div className="replication-bar-track">
                          <div style={{width: String(Math.min(100, item.observedRatio / max * 100)) + "%"}} />
                        </div>
                      )}
                    </div>
                    <strong className="replication-run-ratio">{item.observedRatio === null
                      ? "N/A" : item.observedRatio.toFixed(2) + "×"}</strong>
                  </div>
                ))}
              </div>
              <div className="replication-aggregate">
                <span>MEDIAN OF RECORDED EVALUATION RATIOS</span>
                <strong>{review.medianObservedRatio === null ? "N/A" : review.medianObservedRatio.toFixed(2) + "×"}</strong>
              </div>
              <div className="replication-warning" role="note">
                <strong>UNVERIFIED REPORT · NOT INDEPENDENT REPLICATION</strong>
                <p>These values are claims from a local JSON summary. This browser has not
                  checked the original ledgers, their checksum chains, measured timings or research provenance.
                  Independent replication and statistical significance remain unestablished.</p>
              </div>
              <p className="disclaimer-small">File: {fileName} · Manifest prefix: {review.manifestHashPrefix}… · Automatic promotion disabled</p>
            </div>
          )}
        </div>
      </div>
      <div className="discovery-footer">
        <a className="link-text" target="_blank" rel="noreferrer"
           href="https://github.com/MichaelWave369/PhiRSI/blob/main/docs/R7_PROTOCOL.md">
          EXPLORE THE R7 REPLICATION PROTOCOL ↗
        </a>
        <span>NO HIDDEN RESULTS · NO CLAIMS OF MODEL INTELLIGENCE GAIN</span>
      </div>
    </section>
  );
}
