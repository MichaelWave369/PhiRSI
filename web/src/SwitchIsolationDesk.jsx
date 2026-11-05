import React, { useState } from "react";
import { inspectSwitchIsolation } from "./switchIsolation.js";
import "./switchIsolation.css";

export default function SwitchIsolationDesk(){
  const [preview,setPreview]=useState(null);
  const [name,setName]=useState("");
  const [error,setError]=useState("");
  async function onFile(event){
    const file=event.target.files?.[0];
    event.target.value="";
    setPreview(null);setName("");setError("");
    if(!file)return;
    if(file.size>64000){
      setError("R11 summary JSON must be smaller than 64 KB.");
      return;
    }
    try{
      setPreview(inspectSwitchIsolation(JSON.parse(await file.text())));
      setName(file.name);
    }catch{
      setError("Invalid JSON summary. The file was not uploaded.");
    }
  }
  const max=preview?.recognized
    ?Math.max(1,...preview.blocks.flatMap(b=>[b.firstMs,b.repeatMs]))
    :1;
  return (
    <section className="section switch-desk" id="switch-isolation">
      <div className="section-heading">
        <div>
          <p className="eyebrow"><span className="square-dot" /> 09 / INFERENCE ISOLATION</p>
          <h2>What happens on the first request?</h2>
          <p className="section-description">
            Compare first-request latency with repeated requests to the same model and prompt.
            Observe potential switching overhead without claiming we measured actual model loading.
          </p>
        </div>
        <span className="mini-flag">R11 / LOCAL REQUEST OBSERVATIONS</span>
      </div>
      <div className="switch-grid">
        <aside className="switch-controls">
          <div className="panel-title"><span className="panel-symbol">⌁</span> REQUEST BLOCK PROTOCOL <span className="panel-aside">NO MODEL API</span></div>
          <div className="switch-steps">
            <div><small>01 / PLAN</small><strong>Two registered model aliases</strong><p>Predeclare one initial request and two or three immediate repeats per block. Choose which alias goes first.</p></div>
            <div><small>02 / RUN</small><strong>Explicit approval on your PC</strong><p>Two fixed public prompts, four model blocks, 12–16 bounded loopback requests in total.</p></div>
            <div><small>03 / REVIEW</small><strong>Verify offline, import summary</strong><p>Only the Python verifier rechecks the original receipt. This page previews a reduced, untrusted summary.</p></div>
          </div>
          <label className="switch-upload" htmlFor="r11-summary-file">
            <span aria-hidden="true">⇧</span> IMPORT LOCAL R11 SUMMARY
          </label>
          <input id="r11-summary-file" className="visually-hidden" type="file"
                 accept=".json,application/json" onChange={onFile} />
          <p className="disclaimer-small">No backend requests, credential storage, model downloads, execution of imported data, or file uploads.</p>
        </aside>
        <div className="switch-results">
          <div className="panel-title"><span className="panel-symbol">▥</span> FIRST VS REPEAT <span className="panel-aside">SHAPE-ONLY PREVIEW</span></div>
          {error&&<p className="error-message" role="alert">{error}</p>}
          {!preview&&!error&&<div className="switch-empty">
            <span aria-hidden="true">Φ</span>
            <strong>No isolation experiment loaded.</strong>
            <p>Use the approved local Python workflow, then import its R11 summary JSON.</p>
          </div>}
          {preview&&!preview.recognized&&<div className="discovery-alert" role="alert">
            <strong>UNRECOGNIZED OR UNSAFE EVIDENCE</strong><p>{preview.reason}</p>
          </div>}
          {preview?.recognized&&<div className="switch-report" aria-live="polite">
            <div className="switch-warningline">DESCRIPTIVE ONLY · NO VERIFIED MODEL LOAD OR COLD START</div>
            <div className="switch-models">
              {preview.models.map(m=><article key={m.role}>
                <small>MODEL {m.role}</small>
                <h3>{m.alias}</h3>
                <div className="switch-feature-number">{m.medianFirstOverRepeat.toFixed(2)}<span>×</span></div>
                <p>MEDIAN BLOCK FIRST / REPEAT LATENCY RATIO</p>
                <dl>
                  <div><dt>First-request median</dt><dd>{m.firstMedianMs.toFixed(2)} ms</dd></div>
                  <div><dt>Repeat-request median</dt><dd>{m.repeatMedianMs.toFixed(2)} ms</dd></div>
                  <div><dt>Exact matches</dt><dd>{m.correct}/{m.requests}</dd></div>
                </dl>
              </article>)}
            </div>
            <div className="switch-chart-heading">
              <span>RECORDED SEQUENCE</span><span>FIRST / REPEAT MEDIAN · HTTP MS</span>
            </div>
            <div className="switch-legend"><span className="first">FIRST REQUEST</span><span className="repeat">REPEAT MEDIAN</span></div>
            <div className="switch-chart" role="list" aria-label="Per-block first and repeated HTTP request latencies">
              {preview.blocks.map(b=><div className="switch-block" role="listitem" key={b.block}>
                <div className="switch-block-label"><strong>BLOCK {b.block} · MODEL {b.role}</strong>
                  <span>{b.caseId.toUpperCase()} · {b.requestedAliasChanged?"ALIAS CHANGED":"INITIAL BLOCK"}</span></div>
                <div className="switch-bars">
                  <div><div className="switch-track"><span className="first" style={{width:(b.firstMs/max*100)+"%"}}/></div><small>{b.firstMs.toFixed(2)} ms</small></div>
                  <div><div className="switch-track"><span className="repeat" style={{width:(b.repeatMs/max*100)+"%"}}/></div><small>{b.repeatMs.toFixed(2)} ms</small></div>
                </div>
                <strong className="switch-ratio">{b.ratio.toFixed(2)}×</strong>
              </div>)}
            </div>
            <div className="switch-caution" role="note">
              <strong>ACTUAL MODEL LOADING TIME: NOT MEASURED</strong>
              <p>{preview.warning}</p>
            </div>
            <p className="disclaimer-small">Local file: {name} · Receipt prefix {preview.receiptPrefix}… · Automatic promotion disabled</p>
          </div>}
        </div>
      </div>
      <div className="discovery-footer">
        <a className="link-text" href="https://github.com/MichaelWave369/PhiRSI/blob/main/docs/R11_PROTOCOL.md"
           target="_blank" rel="noreferrer">READ THE R11 SWITCH-ISOLATION PROTOCOL ↗</a>
        <span>OBSERVATION IS NOT PROOF · HUMAN REVIEW REQUIRED</span>
      </div>
    </section>
  );
}
