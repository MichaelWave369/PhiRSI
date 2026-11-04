import React, { useState } from "react";
import { inspectModelPair } from "./modelPair.js";
import "./modelPair.css";

export default function ModelPairDesk() {
  const [result, setResult] = useState(null);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function onFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    setResult(null);
    setError("");
    setName("");
    if (!file) return;
    if (file.size > 64000) {
      setError("R8 browser summary must be smaller than 64 KB.");
      return;
    }
    try {
      setResult(inspectModelPair(JSON.parse(await file.text())));
      setName(file.name);
    } catch {
      setError("Invalid JSON summary. No files or data were uploaded.");
    }
  }

  return (
    <section className="section model-pair-desk" id="model-pair">
      <div className="section-heading">
        <div>
          <p className="eyebrow"><span className="square-dot" /> 06 / LOCAL MODEL RESEARCH</p>
          <h2>Same questions.<br/>Two models. No invented winners.</h2>
          <p className="section-description">
            Inspect an approved, locally measured PhiServe A/B experiment.
            Compare fixed-task correctness and end-to-end HTTP latency without exposing a public model server.
          </p>
        </div>
        <span className="mini-flag">R8 / LOCAL-ONLY EVIDENCE</span>
      </div>

      <div className="modelpair-layout">
        <div className="modelpair-sidebar">
          <div className="panel-title"><span className="panel-symbol">⌁</span> INFERENCE RESEARCH <span className="panel-aside">NO PUBLIC API</span></div>
          <ol className="modelpair-steps">
            <li><strong>Prepare locally</strong><span>Choose two already registered PhiServe aliases and prerecord the bounded task plan.</span></li>
            <li><strong>Approve the model run</strong><span>Only the Python CLI can send inference requests to 127.0.0.1, with explicit operator approval.</span></li>
            <li><strong>Verify and export</strong><span>Check the source receipt using Python and export a summary JSON to view here.</span></li>
          </ol>
          <label className="modelpair-file" htmlFor="modelpair-summary-file">
            <span aria-hidden="true">⇧</span> CHOOSE LOCAL R8 SUMMARY
          </label>
          <input id="modelpair-summary-file" type="file" className="visually-hidden"
                 accept=".json,application/json" onChange={onFile} />
          <p className="disclaimer-small">
            No live backend connections, tokens, prompts, model outputs, remote uploads or inference commands exist on this website.
          </p>
        </div>
        <div className="modelpair-report">
          <div className="panel-title"><span className="panel-symbol">▥</span> A/B OBSERVATION DESK <span className="panel-aside">UNVERIFIED PREVIEW</span></div>
          {error && <p className="error-message" role="alert">{error}</p>}
          {!result && !error && (
            <div className="modelpair-empty">
              <span aria-hidden="true">Φ</span>
              <strong>Model comparison results belong here.</strong>
              <p>Import a local R8 summary JSON after running and verifying the bounded PhiServe experiment on your own computer.</p>
            </div>
          )}
          {result && !result.recognized && (
            <div className="discovery-alert" role="alert">
              <strong>REJECTED JSON SHAPE</strong><p>{result.reason}</p>
            </div>
          )}
          {result?.recognized && (
            <div className="modelpair-results" aria-live="polite">
              <div className="modelpair-evidence-tag">UNVERIFIED DESCRIPTIVE COMPARISON · NO AUTOMATIC PROMOTION</div>
              <div className="modelpair-cards">
                {result.models.map(model => (
                  <article className="modelpair-card" key={model.role}>
                    <p>MODEL {model.role}</p>
                    <h3 title={model.alias}>{model.alias}</h3>
                    <div className="modelpair-large">{(model.fraction * 100).toFixed(1)}<small>%</small></div>
                    <span>EXACT MATCH ON PUBLIC TOY TASKS</span>
                    <div className="modelpair-meter" aria-hidden="true">
                      <div style={{width: String(model.fraction * 100) + "%"}} />
                    </div>
                    <dl>
                      <div><dt>Correct answers</dt><dd>{model.exact}/{model.requests}</dd></div>
                      <div><dt>Median HTTP latency</dt><dd>{model.latency.toFixed(3)} ms</dd></div>
                      <div><dt>Reported token rate*</dt><dd>{model.reportedRate === null ? "N/A" : model.reportedRate.toFixed(1) + " /s"}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
              <div className="modelpair-pair-stats">
                <div><small>PAIRED TASKS</small><strong>{result.pairs}</strong></div>
                <div><small>A FASTER</small><strong>{result.winsA}</strong></div>
                <div><small>B FASTER</small><strong>{result.winsB}</strong></div>
                <div><small>TIES</small><strong>{result.ties}</strong></div>
              </div>
              <div className="modelpair-notice">
                <strong>NO SCIENTIFIC WINNER DECLARED</strong>
                <p>This is a shape-checked local report. The browser cannot attest model weights, timings or inference execution. First-request model loading, cache effects and shared hardware can distort A/B timing. Only three public, easy prompts are scored.</p>
                <p>* Provider-reported completion tokens divided by total request time. Not pure decoding throughput.</p>
              </div>
              <p className="disclaimer-small">Local file: {name} · Receipt prefix: {result.sourcePrefix}… · VRAM not measured · No model intelligence claim</p>
            </div>
          )}
        </div>
      </div>
      <div className="discovery-footer">
        <a className="link-text" href="https://github.com/MichaelWave369/PhiRSI/blob/main/docs/R8_PROTOCOL.md"
           target="_blank" rel="noreferrer">
          READ THE R8 LOCAL EXPERIMENT PROTOCOL ↗
        </a>
        <span>CAPABILITY IS NOT AUTHORITY</span>
      </div>
    </section>
  );
}
