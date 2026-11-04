import React, { useState } from "react";
import DiscoveryDesk from "./DiscoveryDesk.jsx";
import ReplicationDesk from "./ReplicationDesk.jsx";
import ModelPairDesk from "./ModelPairDesk.jsx";
import { RUNGS, runBrowserBenchmark, inspectHandoff } from "./lab.js";

const REPO = "https://github.com/MichaelWave369/PhiRSI";
const LINKS = [
  ["AGENTORA", "https://github.com/MichaelWave369/Agentora"],
  ["PHIOS", "https://github.com/MichaelWave369/PhiOS"],
  ["PHISERVE", "https://github.com/MichaelWave369/PhiServe"],
  ["COMPAWARE", "https://github.com/MichaelWave369/CompAware"],
  ["ΦMADA PRIME", "https://github.com/MichaelWave369/PhiMadaPrime"]
];

function Arrow() {
  return <span aria-hidden="true" className="arrow-icon">↗</span>;
}

function Brand() {
  return (
    <a className="brand" href="#top" aria-label="PhiRSI Live Lab home">
      <span className="brand-mark" aria-hidden="true">Φ</span>
      <span className="brand-title">PHI<span>RSI</span><small>RESEARCH LAB / 369</small></span>
    </a>
  );
}

function RingVisual() {
  return (
    <div className="orbit-wrap" role="img" aria-label="Illustrative three-ring research loop: observe, verify, review. No live model activity displayed.">
      <div className="orbit-halo" />
      <div className="orbit orbit-one" />
      <div className="orbit orbit-two" />
      <div className="orbit orbit-three" />
      <div className="orbit-center">
        <span className="orbit-phi">Φ</span>
        <small>RSI / 369</small>
      </div>
      <span className="orbit-node node-a" />
      <span className="orbit-node node-b" />
      <span className="orbit-node node-c" />
      <span className="orbit-label orbit-label-a">OBSERVE</span>
      <span className="orbit-label orbit-label-b">VERIFY</span>
      <span className="orbit-label orbit-label-c">REVIEW</span>
      <span className="orbit-corner top-left">LAB // R08</span>
      <span className="orbit-corner bottom-right">SIMULATION VISUAL</span>
    </div>
  );
}

function SectionHeader({ eyebrow, title, description, children }) {
  return (
    <div className="section-heading">
      <div>
        <p className="eyebrow"><span className="square-dot" />{eyebrow}</p>
        <h2>{title}</h2>
        <p className="section-description">{description}</p>
      </div>
      {children}
    </div>
  );
}

function Roadmap() {
  const [chosen, setChosen] = useState(5);
  const active = RUNGS.find(item => item.id === chosen) || RUNGS[4];
  return (
    <section className="section" id="roadmap">
      <SectionHeader
        eyebrow="01 / EXPERIMENTAL PROTOCOL"
        title="Seven rungs. One accountable path."
        description="Explore the merged research foundations and the experiments still ahead."
      >
        <a className="link-text" target="_blank" rel="noreferrer" href={REPO + "/blob/main/docs/ROADMAP.md"}>
          FULL ROADMAP <Arrow />
        </a>
      </SectionHeader>
      <div className="roadmap-layout">
        <div className="rungs-list" role="group" aria-label="Research milestones">
          {RUNGS.map(item => (
            <button
              className={"rung-row" + (item.id === chosen ? " is-selected" : "")}
              key={item.id} type="button" onClick={() => setChosen(item.id)}
              aria-pressed={item.id === chosen}
            >
              <span className="rung-index">{String(item.id).padStart(2, "0")}</span>
              <span className="rung-main"><strong>{item.title}</strong><small>{item.subtitle}</small></span>
              <span className={"status-pill " + (item.status === "planned" ? "planned" : "complete")}>
                {item.status === "planned" ? "PLANNED" : item.status === "implemented" ? "AVAILABLE" : "MERGED"}
              </span>
              <span className="rung-chevron" aria-hidden="true">›</span>
            </button>
          ))}
        </div>
        <article className="rung-detail" aria-live="polite">
          <p className="eyebrow">PROJECT MILESTONE / {String(active.id).padStart(2, "0")}</p>
          <div className="detail-num" aria-hidden="true">R{active.id}</div>
          <div className="detail-bottom">
            <span className={"status-pill " + (active.status === "planned" ? "planned" : "complete")}>
              {active.status === "planned" ? "RESEARCH PLANNED" : active.status === "implemented" ? "SOURCE IMPLEMENTATION AVAILABLE" : "IMPLEMENTED ON MAIN"}
            </span>
            <h3>{active.title}</h3>
            <p>{active.detail}</p>
            <div className="notice-line"><span aria-hidden="true">!</span><span>{active.limit}</span></div>
            <a className="link-text" target="_blank" rel="noreferrer"
               href={REPO + "/blob/main/" + active.doc}>VIEW SOURCE CONTRACT <Arrow /></a>
          </div>
        </article>
      </div>
    </section>
  );
}

function FlowDiagram() {
  const steps = [
    ["01", "HYPOTHESIZE", "Declare what could change"],
    ["02", "MEASURE", "Use a bounded comparison"],
    ["03", "VERIFY", "Check against an independent reference"],
    ["04", "REVIEW", "Human decides what happens next"]
  ];
  return (
    <div className="flow-diagram" aria-label="PhiRSI research process">
      {steps.map((step, index) => (
        <React.Fragment key={step[0]}>
          <div className="flow-step">
            <small>{step[0]}</small><strong>{step[1]}</strong><span>{step[2]}</span>
          </div>
          {index < steps.length - 1 && <span className="flow-arrow" aria-hidden="true">→</span>}
        </React.Fragment>
      ))}
    </div>
  );
}

function Experiment() {
  const [maximum, setMaximum] = useState(9000);
  const [rounds, setRounds] = useState(2);
  const [candidate, setCandidate] = useState("sieve");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const run = () => {
    setRunning(true);
    setError("");
    setResult(null);
    // Give React time to render the running state before the bounded synchronous demo.
    setTimeout(() => {
      try {
        setResult(runBrowserBenchmark({ n: maximum, rounds, candidate }));
      } catch (exc) {
        setError(exc.message || "Demo failed");
      } finally {
        setRunning(false);
      }
    }, 30);
  };

  const maxObserved = result ? Math.max(...result.rows.map(row => Math.max(row.baselineMs, row.candidateMs)), 0.001) : 1;
  return (
    <section className="section" id="experiment">
      <SectionHeader
        eyebrow="02 / LIVE BROWSER DEMONSTRATION"
        title="Don't believe the claim. Run the test."
        description="Execute two small, known algorithms in your browser and compare them against a separately written reference."
      >
        <span className="mini-flag">LOCAL BROWSER · NO MODEL WEIGHTS</span>
      </SectionHeader>
      <div className="experiment-layout">
        <div className="experiment-controls">
          <div className="panel-title"><span className="panel-symbol">⌘</span> RUN PARAMETERS <span className="panel-aside">BOUNDED / LOCAL</span></div>
          <label className="form-label" htmlFor="candidate">CANDIDATE ALGORITHM</label>
          <select id="candidate" value={candidate} onChange={event => { setCandidate(event.target.value); setResult(null); }}>
            <option value="sieve">Sieve of Eratosthenes</option>
            <option value="trial">Trial division (negative control)</option>
          </select>
          <div className="input-heading">
            <label className="form-label" htmlFor="limit">MAXIMUM INPUT</label>
            <strong>{maximum.toLocaleString("en-US")}</strong>
          </div>
          <input type="range" id="limit" min="1000" max="15000" step="1000"
                 value={maximum} onChange={event => {setMaximum(Number(event.target.value)); setResult(null);}} />
          <div className="range-ends"><span>1,000</span><span>15,000</span></div>
          <label className="form-label" htmlFor="rounds">MEASUREMENT ROUNDS</label>
          <div className="round-selector" id="rounds" role="group" aria-label="Measurement rounds">
            {[1, 2, 3].map(value => (
              <button key={value} type="button" className={rounds === value ? "active" : ""}
                onClick={() => {setRounds(value); setResult(null);}} aria-pressed={rounds === value}>
                {String(value).padStart(2, "0")}
              </button>
            ))}
          </div>
          <button className="run-button" type="button" onClick={run} disabled={running}>
            <span className="play-symbol">▶</span>{running ? "RUNNING LOCAL TEST" : "RUN BROWSER EXPERIMENT"}<span>↗</span>
          </button>
          <p className="disclaimer-small">Times reflect this browser's current workload. They are not server benchmarks, model evaluations or scientific replication.</p>
        </div>
        <div className="experiment-output" aria-live="polite">
          <div className="panel-title"><span className="panel-symbol">▤</span> OBSERVATION TERMINAL <span className="panel-aside">{result ? "RESULTS / LOCAL" : "AWAITING INPUT"}</span></div>
          {!result && !error && (
            <div className="empty-output">
              <div className="empty-wave" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /></div>
              <strong>{running ? "Executing the bounded algorithm comparison…" : "No measurement recorded yet"}</strong>
              <p>Choose a candidate, set the limits, and run the experiment. No API calls are made.</p>
            </div>
          )}
          {error && <p className="error-message" role="alert">{error}</p>}
          {result && (
            <div className="bench-result">
              <div className="result-metrics">
                <div className="result-metric"><small>OBSERVED SPEEDUP</small>
                  <strong>{result.observedGeomeanSpeedup.toFixed(2)}<em>×</em></strong>
                </div>
                <div className="result-metric"><small>CORRECTNESS</small>
                  <strong className={result.correct ? "good-text" : "warning-text"}>{result.correct ? "PASS" : "FAIL"}</strong>
                </div>
                <div className="result-metric"><small>CONTROL STATUS</small>
                  <strong className="small-metric">{result.negativeControl ? "NEGATIVE" : "CANDIDATE"}</strong>
                </div>
              </div>
              <div className="chart-head"><span>MEDIAN ELAPSED TIME / MS</span><span>LOWER IS FASTER</span></div>
              <div className="legend"><span><i className="legend-baseline" />TRIAL BASELINE</span><span><i className="legend-candidate" />{candidate === "sieve" ? "SIEVE CANDIDATE" : "TRIAL CONTROL"}</span></div>
              <div className="bar-chart">
                {result.rows.map(row => (
                  <div className="bar-case" key={row.limit}>
                    <div className="bar-heading"><span>N = {row.limit.toLocaleString("en-US")}</span><span>REFERENCE COUNT {row.expected}</span></div>
                    <div className="bar-item">
                      <div className="bar-track"><div className="bar-fill baseline" style={{width: (100 * row.baselineMs / maxObserved) + "%"}} /></div>
                      <strong>{row.baselineMs.toFixed(3)} ms</strong>
                    </div>
                    <div className="bar-item">
                      <div className="bar-track"><div className="bar-fill candidate" style={{width: (100 * row.candidateMs / maxObserved) + "%"}} /></div>
                      <strong>{row.candidateMs.toFixed(3)} ms</strong>
                    </div>
                  </div>
                ))}
              </div>
              <p className="result-interpretation">{result.negativeControl
                ? "Negative control: identical algorithms are not improvements, regardless of timing noise."
                : result.correct
                  ? "All sampled outputs match the independent prime-count reference. Relative speed is only a local observation."
                  : "A correctness mismatch occurred. This candidate must not qualify as an improvement."}</p>
              <p className="disclaimer-small">Browser demonstration only · No signed evidence · No auto-promotion · No model intelligence claim</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function EvidenceInspector() {
  const [inspection, setInspection] = useState(null);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");
  const onFile = async event => {
    const file = event.target.files?.[0];
    setInspection(null);
    setError("");
    setFileName("");
    if (!file) return;
    if (file.size > 64_000) {
      setError("The inspector only accepts JSON handoff files smaller than 64 KB.");
      return;
    }
    try {
      const data = JSON.parse(await file.text());
      setInspection(inspectHandoff(data));
      setFileName(file.name);
    } catch {
      setError("Could not read that JSON file. No data was sent anywhere.");
    } finally {
      event.target.value = "";
    }
  };
  return (
    <section className="section" id="evidence">
      <SectionHeader
        eyebrow="03 / READ-ONLY EVIDENCE DESK"
        title="Inspect the claim. Keep the authority."
        description="Open an R5 review handoff on your own device. Nothing is uploaded, executed, saved or dispatched."
      />
      <div className="evidence-layout">
        <div className="inspector-panel">
          <div className="panel-title"><span className="panel-symbol">◇</span> LOCAL HANDOFF INSPECTOR <span className="panel-aside">READ ONLY</span></div>
          <label className="upload-zone" htmlFor="handoff-file">
            <span className="upload-icon" aria-hidden="true">⇧</span>
            <strong>Choose a PhiRSI handoff JSON</strong>
            <span>R5 schema · .json · max 64 KB</span>
            <span className="upload-action">CHOOSE FILE <Arrow /></span>
          </label>
          <input className="visually-hidden" type="file" id="handoff-file"
                 accept=".json,application/json" onChange={onFile} />
          {error && <p className="error-message" role="alert">{error}</p>}
          {inspection && (
            <div className="inspection-output" role="status">
              <p className="inspection-file">LOCAL FILE: {fileName}</p>
              <strong>{inspection.structurallyRecognized
                ? inspection.safePolicy ? "REVIEW-ONLY POLICY SHAPE" : "UNSAFE POLICY FIELDS FOUND"
                : "UNRECOGNIZED HANDOFF"}</strong>
              <p>{inspection.structurallyRecognized
                ? "Schema recognized. This does not verify source evidence, authenticity, timing or checksum."
                : inspection.error}</p>
              {inspection.structurallyRecognized && (
                <dl className="inspection-fields">
                  <div><dt>RUNG</dt><dd>{inspection.sourceKind}</dd></div>
                  <div><dt>SOURCE HASH PREFIX</dt><dd>{inspection.sourceHashPrefix}…</dd></div>
                  <div><dt>CLAIMED STATUS</dt><dd>{inspection.status}</dd></div>
                  <div><dt>POLICY SHAPE</dt><dd>{inspection.safePolicy ? "NO AUTHORITY" : "REJECT"}</dd></div>
                  <div><dt>PROVENANCE</dt><dd>NOT AUTHENTICATED</dd></div>
                </dl>
              )}
            </div>
          )}
          <p className="disclaimer-small">To actually verify the handoff, run the Python R5 verifier with both the original source receipt and this file. The browser cannot authenticate it alone.</p>
        </div>
        <div className="security-panel">
          <p className="eyebrow">TRUST ARCHITECTURE</p>
          <h3>Capability <span>≠</span> authority.</h3>
          <p>A useful experiment doesn't grant itself permission. That distinction is built into the lab's software, not just the branding.</p>
          <ul className="guardrail-list">
            <li><span aria-hidden="true">✓</span><span>Local-only file inspection</span></li>
            <li><span aria-hidden="true">✓</span><span>No model inference from the public site</span></li>
            <li><span aria-hidden="true">✓</span><span>No GitHub tokens, merge buttons or secret storage</span></li>
            <li><span aria-hidden="true">✓</span><span>Human review before consequential actions</span></li>
          </ul>
          <a className="link-text" href={REPO + "/blob/main/docs/R5_PROTOCOL.md"}
             target="_blank" rel="noreferrer">READ THE GOVERNANCE CONTRACT <Arrow /></a>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  return (
    <div id="top" className="app-shell">
      <div className="background-grid" aria-hidden="true" />
      <header className="site-header">
        <div className="page-container header-inner">
          <Brand />
          <nav className="primary-nav" aria-label="Main navigation">
            <a href="#roadmap">ROADMAP</a>
            <a href="#experiment">LIVE EXPERIMENT</a>
            <a href="#evidence">EVIDENCE</a>
            <a href="#discovery">DISCOVERY</a>
            <a href="#replication">REPLICATION</a>
            <a href="#model-pair">MODEL A/B</a>
          </nav>
          <a className="header-github" href={REPO} target="_blank" rel="noreferrer">
            GITHUB <Arrow />
          </a>
        </div>
      </header>
      <main>
        <section className="hero page-container">
          <div className="hero-copy">
            <p className="eyebrow"><span className="signal-dot" /> OPEN RESEARCH / OPERATIONAL FOUNDATION</p>
            <h1>Improvement<br/>is a <span>hypothesis.</span><br/>Evidence is the<br/><i>standard.</i></h1>
            <p className="hero-intro">An open laboratory for measurable systems improvement. Build better experiments, challenge the results, and never confuse capability with authority.</p>
            <div className="hero-actions">
              <a className="button-primary" href="#experiment">ENTER THE LIVE LAB <span>↗</span></a>
              <a className="button-secondary" href="#roadmap">EXPLORE THE RESEARCH <span>→</span></a>
            </div>
            <div className="hero-caption"><span className="caption-rule"/> Φ369 RESEARCH INITIATIVE · PUBLIC / MIT LICENSE</div>
          </div>
          <RingVisual />
        </section>
        <div className="page-container">
          <div className="status-strip" aria-label="Research status summary">
            <div><strong>08<span> / 08</span></strong><small>AVAILABLE RESEARCH RUNGS</small></div>
            <div><strong>03</strong><small>FIXED BROWSER TEST CASES</small></div>
            <div><strong>00</strong><small>AUTOMATIC DEPLOYMENT GRANTS</small></div>
            <div className="strip-status"><span className="signal-dot"/> EXPERIMENTAL SOFTWARE <small>NOT AN AGI CLAIM</small></div>
          </div>
          <div className="section-intro">
            <p className="eyebrow">THE PHIRSI METHOD</p>
            <h2>Not faster by assertion.<br/><span>Better by measurement.</span></h2>
            <FlowDiagram />
          </div>
          <Roadmap />
          <Experiment />
          <EvidenceInspector />
          <DiscoveryDesk />
          <ReplicationDesk />
          <ModelPairDesk />
          <section className="ecosystem section" id="ecosystem">
            <SectionHeader eyebrow="04 / THE CONNECTED ECOSYSTEM"
              title="Built to collaborate. Never to overreach."
              description="These projects inform the roadmap. The public site doesn't connect to their private runtimes." />
            <div className="ecosystem-links">
              {LINKS.map(([name, href], i) => (
                <a href={href} target="_blank" rel="noreferrer" key={name}>
                  <span className="eco-index">0{i + 1}</span>
                  <strong>{name}</strong><Arrow />
                </a>
              ))}
            </div>
          </section>
        </div>
      </main>
      <footer className="site-footer">
        <div className="page-container footer-inner">
          <div><strong>ΦRSI</strong><span>IMPROVE · VERIFY · REMEMBER · REPEAT</span></div>
          <p>OPEN SOURCE / MIT LICENSE / Φ369 LABS</p>
          <a href="#top">BACK TO TOP ↑</a>
        </div>
      </footer>
    </div>
  );
}
