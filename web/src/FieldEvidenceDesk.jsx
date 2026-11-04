import React, { useState } from "react";
import { inspectFieldEvidence } from "./fieldEvidence.js";
import "./fieldEvidence.css";

export default function FieldEvidenceDesk() {
  const [report,setReport]=useState(null);
  const [filename,setFilename]=useState("");
  const [error,setError]=useState("");
  const read=async event=>{
    const file=event.target.files?.[0];
    event.target.value="";
    setReport(null);setFilename("");setError("");
    if(!file)return;
    if(file.size>64000){setError("R9 summary must be 64 KB or smaller.");return;}
    try {
      setReport(inspectFieldEvidence(JSON.parse(await file.text())));
      setFilename(file.name);
    } catch {
      setError("Invalid local JSON. No file was uploaded.");
    }
  };
  return (
    <section className="section" id="field-evidence">
      <div className="section-heading">
        <div>
          <p className="eyebrow"><span className="square-dot" /> 07 / HARDWARE RESEARCH</p>
          <h2>Know what was measured.<br/>Know what wasn't.</h2>
          <p className="section-description">
            Twelve public fixed tasks, local model-file fingerprints, and optional PhiServe GPU
            driver observations. All evidence remains review-only.
          </p>
        </div>
        <span className="mini-flag">R9 / NO PUBLIC MODEL API</span>
      </div>
      <div className="field-layout">
        <div className="field-controls">
          <div className="panel-title"><span className="panel-symbol">▤</span> FIELD EVIDENCE IMPORT <span className="panel-aside">LOCAL JSON ONLY</span></div>
          <div className="field-step"><strong>01 / PREDECLARE</strong><span>Record two local PhiServe aliases and fixed task limits.</span></div>
          <div className="field-step"><strong>02 / RUN LOCALLY</strong><span>Authorize the Python evaluation. Optionally hash GGUF files and attach separate PhiServe field-run receipts.</span></div>
          <div className="field-step"><strong>03 / REVIEW</strong><span>Verify the full receipt offline, then load the reduced summary here.</span></div>
          <label className="field-import" htmlFor="r9-summary-file">⇧ <span>INSPECT LOCAL R9 SUMMARY</span></label>
          <input className="visually-hidden" type="file" accept=".json,application/json"
                 id="r9-summary-file" onChange={read}/>
          <p className="disclaimer-small">
            This static website makes no inference requests, executes no supplied source,
            accesses no GPU, and uploads no files. JSON is treated as untrusted data.
          </p>
        </div>
        <div className="field-view">
          <div className="panel-title"><span className="panel-symbol">⌁</span> FIELD OBSERVATIONS <span className="panel-aside">UNVERIFIED BROWSER VIEW</span></div>
          {error&&<p className="error-message" role="alert">{error}</p>}
          {!error&&!report&&<div className="field-empty">
            <span aria-hidden="true">Φ</span><strong>No R9 evidence loaded yet.</strong>
            <p>Use the Python research CLI to export a private summary JSON, then open it here.</p>
          </div>}
          {report&&!report.recognized&&<div className="discovery-alert" role="alert">
            <strong>INVALID OR UNSAFE SUMMARY</strong><p>{report.reason}</p>
          </div>}
          {report?.recognized&&<div className="field-report" aria-live="polite">
            <div className="field-warning">DESCRIPTIVE DATA · NOT AUTHENTICATED · NO WINNER DECLARED</div>
            <div className="field-models">
              {report.models.map(model=><article className="field-model" key={model.role}>
                <small>MODEL {model.role}</small><h3>{model.alias}</h3>
                <strong>{model.correct}<span> / {model.total}</span></strong>
                <p>EXACT MATCH ON PUBLIC TASKS</p>
                <div className="field-meter"><div style={{width:(model.fraction*100)+"%"}}/></div>
                <dl><div><dt>Median HTTP latency</dt><dd>{model.medianMs.toFixed(3)} ms</dd></div>
                  <div><dt>Provider-based rate*</dt><dd>{model.reportedRate===null?"N/A":model.reportedRate.toFixed(1)+" tokens/s"}</dd></div>
                </dl>
              </article>)}
            </div>
            <div className="field-categories">
              <p>CATEGORY-BY-CATEGORY EXACT MATCH</p>
              {report.categories.map(category=><div key={category.name} className="field-category">
                <strong>{category.name.toUpperCase()}</strong>
                <span>A {category.A.correct}/{category.A.attempted}</span>
                <span>B {category.B.correct}/{category.B.attempted}</span>
              </div>)}
            </div>
            <div className="field-hardware">
              <p>OPTIONAL HARDWARE EVIDENCE</p>
              {["A","B"].map(role=><div key={role}>
                <strong>MODEL {role}</strong>
                <span>GGUF {report.devices[role].fingerprint??"NOT PROVIDED"}</span>
                <span>{report.devices[role].driverStatus}</span>
                <span>Driver process memory: {report.devices[role].driverPeakMiB===null?"N/A":report.devices[role].driverPeakMiB+" MiB"}</span>
              </div>)}
            </div>
            <div className="field-caution">
              <strong>SEPARATE EVIDENCE IS NOT EXECUTION PROOF</strong>
              <p>{report.message} *Token rate uses total HTTP request time, not decode-only time. No scientific significance, independent replication, or intelligence improvement is claimed.</p>
            </div>
            <p className="disclaimer-small">Local file: {filename} · Receipt prefix {report.summaryPrefix}… · Automatic promotion disabled</p>
          </div>}
        </div>
      </div>
      <div className="discovery-footer">
        <a className="link-text" target="_blank" rel="noreferrer"
           href="https://github.com/MichaelWave369/PhiRSI/blob/main/docs/R9_PROTOCOL.md">READ THE R9 FIELD PROTOCOL ↗</a>
        <span>NO SECRET DATA UPLOADED · NO AUTOMATIC MODEL CHANGES</span>
      </div>
    </section>
  );
}
