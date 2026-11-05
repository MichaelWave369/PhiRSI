import React, { useState } from "react";
import { inspectWorkstation } from "./workstation.js";
import "./workstation.css";

export default function WorkstationDesk() {
  const [result,setResult]=useState(null);
  const [filename,setFilename]=useState("");
  const [error,setError]=useState("");
  const choose=async event=>{
    const file=event.target.files?.[0];
    event.target.value="";
    setResult(null);setFilename("");setError("");
    if(!file)return;
    if(file.size>64000){setError("R10 comparison JSON must be at most 64 KB.");return;}
    try {
      setResult(inspectWorkstation(JSON.parse(await file.text())));
      setFilename(file.name);
    } catch {
      setError("Invalid local JSON. No data was uploaded.");
    }
  };
  return (
    <section className="section workstation-desk" id="workstation">
      <div className="section-heading">
        <div>
          <p className="eyebrow"><span className="square-dot"/> 08 / WORKSTATION ACCEPTANCE</p>
          <h2>One pass is a demo.<br/>Repeatability earns scrutiny.</h2>
          <p className="section-description">
            Review three to six locally collected R9 observations against declared task-quality
            and repeat-run latency thresholds. Every original receipt remains in the private dossier.
          </p>
        </div>
        <span className="mini-flag">R10 / OFFLINE ACCEPTANCE DESK</span>
      </div>
      <div className="workstation-layout">
        <aside className="workstation-instructions">
          <div className="panel-title"><span className="panel-symbol">⌁</span> WORKSTATION EVIDENCE <span className="panel-aside">LOCAL ONLY</span></div>
          <div className="workstation-step"><strong>01 / REGISTER CRITERIA</strong><p>Save the R10 plan with aliases, distinct seeds, accuracy floor and maximum allowed repeat-run latency variation.</p></div>
          <div className="workstation-step"><strong>02 / COLLECT R9 RUNS</strong><p>Run R9 separately for each seed on your own workstation with explicit approval. These are not automatically certified cold or warm starts.</p></div>
          <div className="workstation-step"><strong>03 / VERIFY THE DOSSIER</strong><p>Use the offline R10 CLI to preserve and replay every original R9 receipt. Export the smaller JSON summary for this panel.</p></div>
          <label className="workstation-upload" htmlFor="workstation-file">⇧ <span>INSPECT R10 SUMMARY JSON</span></label>
          <input className="visually-hidden" type="file" id="workstation-file"
                 accept=".json,application/json" onChange={choose}/>
          <p className="disclaimer-small">
            Your file stays on your device. This page never calls PhiServe,
            reads model weights, verifies GPU execution, or performs a GitHub action.
          </p>
        </aside>
        <div className="workstation-report">
          <div className="panel-title"><span className="panel-symbol">▥</span> REPEATABILITY REPORT <span className="panel-aside">UNVERIFIED BROWSER DATA</span></div>
          {error&&<p className="error-message" role="alert">{error}</p>}
          {!error&&!result&&<div className="workstation-empty">
            <span aria-hidden="true">Φ</span>
            <strong>No workstation dossier loaded.</strong>
            <p>Import a review-only summary produced by the R10 Python verifier to inspect reported run-to-run consistency.</p>
          </div>}
          {result&&!result.recognized&&<div className="discovery-alert" role="alert">
            <strong>UNRECOGNIZED OR UNSAFE DATA</strong>
            <p>{result.reason}</p>
          </div>}
          {result?.recognized&&<div className="workstation-results" aria-live="polite">
            <div className="workstation-topline">OPERATOR-DECLARED OBSERVATIONS · NO MACHINE ATTESTATION</div>
            <div className={"workstation-status " + (result.qualityMet&&result.stabilityMet?"met":"unmet")}>
              <small>PREDECLARED CRITERIA</small>
              <strong>{result.status}</strong>
              <span>This is not a hardware certification or permission to deploy.</span>
            </div>
            <div className="workstation-summary-cards">
              <div><small>PUBLIC-TASK QUALITY FLOOR</small><strong>{(result.planQualityFloor*100).toFixed(0)}%</strong>
                <span>{result.qualityMet?"REPORTED THRESHOLD MET":"REPORTED THRESHOLD MISSED"}</span></div>
              <div><small>MAX REPEAT LATENCY SPREAD</small><strong>{result.planMaxRepeatSpread.toFixed(2)}×</strong>
                <span>{result.stabilityMet?"REPORTED THRESHOLD MET":"REPORTED THRESHOLD MISSED"}</span></div>
              <div><small>RUNS PRESERVED IN DOSSIER</small><strong>{result.rows.length}</strong><span>NOT IN THIS BROWSER SUMMARY</span></div>
            </div>
            <div className="workstation-run-heading">
              <span>SEQUENTIAL R9 OBSERVATIONS</span><span>MEDIAN HTTP LATENCY / MS</span>
            </div>
            <div className="workstation-legend"><span><i className="model-a"/> A · {result.modelA}</span><span><i className="model-b"/> B · {result.modelB}</span></div>
            <div className="workstation-chart">
              {result.rows.map(row=><div className="workstation-run" key={row.sequence}>
                <div className="workstation-run-label"><strong>{row.label.toUpperCase()} / {row.sequence}</strong>
                  <span>SEED {row.seed}</span></div>
                <div className="workstation-bars">
                  <div><span className="workstation-bar-track"><span className="workstation-fill a" style={{width:(100*row.aMs/(Math.max(1,...result.rows.map(r=>Math.max(r.aMs,r.bMs)))))+"%"}}/></span>
                    <small>{row.aMs.toFixed(2)} ms · {row.aCorrect} correct</small></div>
                  <div><span className="workstation-bar-track"><span className="workstation-fill b" style={{width:(100*row.bMs/(Math.max(1,...result.rows.map(r=>Math.max(r.aMs,r.bMs)))))+"%"}}/></span>
                    <small>{row.bMs.toFixed(2)} ms · {row.bCorrect} correct</small></div>
                </div>
              </div>)}
            </div>
            <div className="workstation-spread">
              <div><small>A REPEAT SPREAD</small><strong>{result.ratios.A.toFixed(2)}×</strong></div>
              <div><small>B REPEAT SPREAD</small><strong>{result.ratios.B.toFixed(2)}×</strong></div>
            </div>
            <div className="workstation-warning" role="note">
              <strong>IMPORTANT LIMITATION</strong>
              <p>{result.warning}</p>
            </div>
            <p className="disclaimer-small">
              Local file: {filename} · Source hash prefix: {result.sourcePrefix}… · Human review required
            </p>
          </div>}
        </div>
      </div>
      <div className="discovery-footer">
        <a className="link-text" href="https://github.com/MichaelWave369/PhiRSI/blob/main/docs/R10_PROTOCOL.md"
           target="_blank" rel="noreferrer">READ THE R10 ACCEPTANCE PROTOCOL ↗</a>
        <span>REVIEW ONLY · NO AUTONOMOUS MODEL PROMOTION</span>
      </div>
    </section>
  );
}
