import React, { useState } from "react";
import { inspectDiscovery } from "./discovery.js";
import "./discovery.css";

export default function DiscoveryDesk() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  async function onFile(event) {
    const file = event.target.files?.[0];
    setResult(null);
    setError("");
    setFileName("");
    event.target.value = "";
    if (!file) return;
    if (file.size > 1_000_000) {
      setError("Discovery ledger exceeds the 1 MB browser inspection limit.");
      return;
    }
    try {
      const value = JSON.parse(await file.text());
      const inspected = inspectDiscovery(value);
      setResult(inspected);
      setFileName(file.name);
    } catch {
      setError("Invalid JSON file. No bytes were uploaded or saved.");
    }
  }

  const entries = result?.recognized ? result.entries : [];
  const max = entries.length ? Math.max(...entries.map(e => e.ratio), 1) : 1;
  return (
    <section className="section discovery-desk" id="discovery">
      <div className="section-heading">
        <div>
          <p className="eyebrow"><span className="square-dot" /> 04 / RUNG SIX RESEARCH</p>
          <h2>The discovery ledger.</h2>
          <p className="section-description">
            Inspect a locally generated R6 candidate-search ledger. See every registered
            candidate, the negative control, evaluation stage, and stop decision.
          </p>
        </div>
        <span className="mini-flag">LOCAL FILE · NO UPLOAD</span>
      </div>
      <div className="discovery-grid">
        <div className="discovery-upload">
          <div className="panel-title"><span className="panel-symbol">⌁</span> SEARCH HISTORY <span className="panel-aside">UNVERIFIED INPUT</span></div>
          <div className="discovery-example">
            <span className="discovery-rail-dot" />
            <div><small>01 / CONTROL</small><strong>Trial vs trial</strong><p>Negative control never qualifies as an improvement.</p></div>
          </div>
          <div className="discovery-example">
            <span className="discovery-rail-dot" />
            <div><small>02 / DEVELOPMENT</small><strong>Trial vs sieve</strong><p>A candidate must beat the predeclared development threshold.</p></div>
          </div>
          <div className="discovery-example">
            <span className="discovery-rail-dot" />
            <div><small>03 / EVALUATION</small><strong>One-shot evaluation</strong><p>Only the selected candidate is measured on the second input split.</p></div>
          </div>
          <label htmlFor="r6-ledger-file" className="discovery-file-label">
            <span aria-hidden="true">⇧</span> INSPECT LOCAL R6 JSON
          </label>
          <input className="visually-hidden" id="r6-ledger-file" type="file"
                 accept="application/json,.json" onChange={onFile} />
          <p className="disclaimer-small">
            No source code execution, API access, uploads or model calls.
            The browser displays receipt claims but never verifies their timing or hash chain.
          </p>
        </div>
        <div className="discovery-view">
          <div className="panel-title"><span className="panel-symbol">▥</span> OBSERVATION LEDGER <span className="panel-aside">{result?.recognized ? "LOCAL PREVIEW" : "NO VERIFIED DATA"}</span></div>
          {error && <p className="error-message" role="alert">{error}</p>}
          {!result && !error && (
            <div className="discovery-placeholder">
              <span className="discovery-placeholder-icon" aria-hidden="true">Φ</span>
              <strong>Your experiment history appears here.</strong>
              <p>Run the R6 Python research protocol locally and select its JSON ledger. This website cannot launch experiments.</p>
            </div>
          )}
          {result && !result.recognized && (
            <div className="discovery-alert" role="alert">
              <strong>NOT ACCEPTED</strong>
              <p>{result.reason}</p>
            </div>
          )}
          {result?.recognized && (
            <div className="discovery-results" aria-live="polite">
              <div className="discovery-summary-row">
                <div><small>REPORTED DISPOSITION</small><strong>{result.status}</strong></div>
                <div><small>SELECTED</small><strong>{result.selectedCandidate.toUpperCase()}</strong></div>
              </div>
              <div className="discovery-hash">
                <span>PLAN SHA-256 PREFIX</span> <code>{result.planHashPrefix}…</code>
              </div>
              <div className="discovery-chart-heading">
                <span>REPORTED OBSERVED SPEEDUP</span><span>NOT REPLICATED</span>
              </div>
              <div className="discovery-chart" role="list" aria-label="Claimed speedup by experiment stage">
                {entries.map((entry, index) => (
                  <div className="discovery-chart-row" role="listitem" key={index}>
                    <div className="discovery-chart-label"><strong>{entry.label}</strong><span>{entry.candidate}</span></div>
                    <div className="discovery-chart-bar"><div style={{width:(Math.min(entry.ratio/max,1)*100)+"%"}} /></div>
                    <strong className="discovery-chart-value">{entry.ratio.toFixed(2)}×</strong>
                  </div>
                ))}
                {!entries.length && <p>No measurement events recorded before the budget stop.</p>}
              </div>
              <p className="discovery-alert">
                <strong>SHAPE ONLY · NOT VERIFIED</strong>
                <span>Browser display does not authenticate the study, reproduce past timings, validate hash links or grant approval. Use the Python R6 verifier for local consistency checks.</span>
              </p>
              <p className="disclaimer-small">File: {fileName} · Automatic promotion: disabled · AI intelligence gain: not established</p>
            </div>
          )}
        </div>
      </div>
      <div className="discovery-footer">
        <a className="link-text" href="https://github.com/MichaelWave369/PhiRSI/blob/main/docs/R6_PROTOCOL.md"
           target="_blank" rel="noreferrer">
          EXPLORE THE R6 RESEARCH PROTOCOL ↗
        </a>
        <span>HUMAN REVIEW REQUIRED · NO AUTOMATED GIT CHANGES</span>
      </div>
    </section>
  );
}
