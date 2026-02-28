import { useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

type Status = "active" | "probation" | "suppressed";

type EventRow = {
  type: string;
  text: string;
};

type StepRecord = {
  step: number;
  ungovernedRisk: number;
  governedRisk: number;
  congestionUng: number;
  congestionGov: number;
  frequencyUng: number;
  frequencyGov: number;
  waterUng: number;
  waterGov: number;
  gpsUng: number;
  gpsGov: number;
  trustScores: Record<string, number>;
  authorityWeights: Record<string, number>;
  statuses: Record<string, Status>;
  suppressed: string[];
  events: EventRow[];
};

type Summary = {
  ungovernedCascade: boolean;
  governedCascade: boolean;
  ungovernedTimeToCascade: number | null;
  governedTimeToCascade: number | null;
  sectorsFailedUng: number;
  sectorsFailedGov: number;
  suppressionEvents: number;
  maxRiskUng: number;
  maxRiskGov: number;
};

type Parsed = {
  summary: Summary;
  steps: StepRecord[];
};

const AGENTS = [
  "telecom_optimizer",
  "power_grid_balancer",
  "water_monitor",
  "aviation_router",
  "emergency_override"
] as const;

const AGENT_COLORS: Record<string, string> = {
  telecom_optimizer: "#f97316",
  power_grid_balancer: "#0ea5e9",
  water_monitor: "#22c55e",
  aviation_router: "#eab308",
  emergency_override: "#ef4444"
};

const STATUS_COLOR: Record<Status, string> = {
  active: "#1f2937",
  probation: "#8b5cf6",
  suppressed: "#dc2626"
};

const speedMap: Record<string, number> = {
  "1x": 1000,
  "2x": 500,
  "4x": 250,
  "8x": 125
};

function num(v: unknown, fallback = 0): number {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string") {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return fallback;
}

function bool(v: unknown, fallback = false): boolean {
  if (typeof v === "boolean") return v;
  return fallback;
}

function arr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}

function rec(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
}

function eventSeverity(type: string, text: string): string {
  const t = `${type} ${text}`.toLowerCase();
  if (t.includes("suppressed") || t.includes("routing_freeze") || t.includes("safe_degradation")) return "red";
  if (t.includes("threshold") || t.includes("injection") || t.includes("risk")) return "amber";
  if (t.includes("increase") || t.includes("loosen")) return "blue";
  if (t.includes("tighten") || t.includes("mutation")) return "purple";
  if (t.includes("redeem") || t.includes("recover")) return "green";
  return "neutral";
}

function parseData(raw: unknown): Parsed {
  const root = rec(raw);
  const rawSummary = rec(root.summary);
  const rawTimeline = arr(root.timeline);

  const steps: StepRecord[] = rawTimeline.map((row, idx) => {
    const r = rec(row);
    const step = Math.max(1, Math.floor(num(r.step, idx + 1)));
    const sectorMetrics = rec(r.sector_metrics);
    const ung = rec(sectorMetrics.ungoverned);
    const gov = rec(sectorMetrics.governed);

    const trustScoresRaw = rec(r.trust_scores);
    const authorityRaw = rec(r.authority_weights);
    const suppressed = arr(r.suppressed_agents).map((x) => String(x));

    const statuses: Record<string, Status> = {};
    const trustScores: Record<string, number> = {};
    const authorityWeights: Record<string, number> = {};

    AGENTS.forEach((aid) => {
      trustScores[aid] = num(trustScoresRaw[aid], 0);
      authorityWeights[aid] = num(authorityRaw[aid], 0);
      statuses[aid] = suppressed.includes(aid) ? "suppressed" : "active";
    });

    const parsedEvents = arr(r.events).map((ev) => {
      const e = rec(ev);
      const text = String(e.text ?? e.message ?? "event");
      const type = String(e.type ?? "event");
      return { type, text };
    });

    return {
      step,
      ungovernedRisk: num(ung.systemic_risk),
      governedRisk: num(gov.systemic_risk),
      congestionUng: num(ung.congestion_level),
      congestionGov: num(gov.congestion_level),
      frequencyUng: Math.abs(num(ung.frequency_delta)),
      frequencyGov: Math.abs(num(gov.frequency_delta)),
      waterUng: num(ung.sensor_integrity, 1),
      waterGov: num(gov.sensor_integrity, 1),
      gpsUng: num(ung.gps_sync_error),
      gpsGov: num(gov.gps_sync_error),
      trustScores,
      authorityWeights,
      statuses,
      suppressed,
      events: parsedEvents
    };
  });

  const summary: Summary = {
    ungovernedCascade: bool(rawSummary.ungoverned_cascade_occurred),
    governedCascade: bool(rawSummary.governed_cascade_occurred),
    ungovernedTimeToCascade: rawSummary.time_to_cascade_ungoverned == null ? null : num(rawSummary.time_to_cascade_ungoverned),
    governedTimeToCascade: rawSummary.time_to_cascade_governed == null ? null : num(rawSummary.time_to_cascade_governed),
    sectorsFailedUng: num(rawSummary.sectors_failed_ungoverned),
    sectorsFailedGov: num(rawSummary.sectors_failed_governed),
    suppressionEvents: num(rawSummary.suppression_events),
    maxRiskUng: num(rawSummary.max_systemic_risk_index_ungoverned),
    maxRiskGov: num(rawSummary.max_systemic_risk_index_governed)
  };

  return { summary, steps };
}

function cardValue(v: number | null): string {
  if (v == null || Number.isNaN(v)) return "Prevented";
  return `Step ${String(Math.floor(v)).padStart(3, "0")}`;
}

function App() {
  const [data, setData] = useState<Parsed>({
    summary: {
      ungovernedCascade: false,
      governedCascade: false,
      ungovernedTimeToCascade: null,
      governedTimeToCascade: null,
      sectorsFailedUng: 0,
      sectorsFailedGov: 0,
      suppressionEvents: 0,
      maxRiskUng: 0,
      maxRiskGov: 0
    },
    steps: []
  });
  const [current, setCurrent] = useState(0);
  const [selectedStep, setSelectedStep] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<keyof typeof speedMap>("1x");
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetch("/infra_chain_results.json")
      .then((r) => r.json())
      .then((json) => setData(parseData(json)))
      .catch(() => setData(parseData({ summary: {}, timeline: [] })));
  }, []);

  useEffect(() => {
    if (!playing || data.steps.length === 0) return;
    const id = window.setInterval(() => {
      setCurrent((prev) => {
        if (prev >= data.steps.length - 1) {
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, speedMap[speed]);
    return () => window.clearInterval(id);
  }, [playing, speed, data.steps.length]);

  const currentStep = data.steps[current] ?? null;

  const allEvents = useMemo(() => {
    const rows: Array<{ step: number; type: string; text: string; severity: string }> = [];
    data.steps.forEach((s) => {
      s.events.forEach((e) => {
        rows.push({
          step: s.step,
          type: e.type,
          text: e.text,
          severity: eventSeverity(e.type, e.text)
        });
      });
    });
    return rows;
  }, [data.steps]);

  const visibleEvents = useMemo(() => {
    if (!currentStep) return [];
    return allEvents.filter((e) => e.step <= currentStep.step).slice(-220);
  }, [allEvents, currentStep]);

  useEffect(() => {
    if (!logRef.current) return;
    logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [visibleEvents.length, current]);

  const chartRows = useMemo(
    () =>
      data.steps.map((s) => ({
        step: s.step,
        ungovernedRisk: s.ungovernedRisk,
        governedRisk: s.governedRisk,
        congestionUng: s.congestionUng,
        congestionGov: s.congestionGov,
        frequencyUng: s.frequencyUng,
        frequencyGov: s.frequencyGov,
        waterUng: s.waterUng,
        waterGov: s.waterGov,
        gpsUng: s.gpsUng,
        gpsGov: s.gpsGov,
        ...s.authorityWeights
      })),
    [data.steps]
  );
  const visibleRows = chartRows.slice(0, current + 1);

  const stepDisplay = currentStep ? String(currentStep.step).padStart(3, "0") : "000";
  const totalDisplay = String(data.steps.length).padStart(3, "0");

  const selected = selectedStep
    ? data.steps.find((s) => s.step === selectedStep) ?? currentStep
    : currentStep;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">SYNTROPIQ — Critical Infrastructure Control Plane</div>
        <div className="status-pills">
          <span className={`pill ${data.summary.ungovernedCascade ? "danger" : "ok"}`}>
            UNGOVERNED: {data.summary.ungovernedCascade ? "CASCADE" : "STABLE"}
          </span>
          <span className={`pill ${data.summary.governedCascade ? "danger" : "ok"}`}>
            GOVERNED: {data.summary.governedCascade ? "CASCADE" : "CONTAINED"}
          </span>
        </div>
        <div className="step-indicator">
          <span>STEP {stepDisplay} / {totalDisplay}</span>
          <span className={`pill ${currentStep && currentStep.step >= 40 ? "danger" : "neutral"}`}>
            PROMPT INJECTION: {currentStep && currentStep.step >= 40 ? "ACTIVE" : "INACTIVE"}
          </span>
        </div>
      </header>

      <main className="main-grid">
        <section className="panel kpis">
          <h2>Incident Summary</h2>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-label">Ungoverned Time to Cascade</div>
              <div className="kpi-value">{cardValue(data.summary.ungovernedTimeToCascade)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Governed Time to Cascade</div>
              <div className="kpi-value">{cardValue(data.summary.governedTimeToCascade)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Suppression Events</div>
              <div className="kpi-value">{Math.floor(data.summary.suppressionEvents)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Peak Systemic Risk (UNG / GOV)</div>
              <div className="kpi-value">
                {data.summary.maxRiskUng.toFixed(2)} / {data.summary.maxRiskGov.toFixed(2)}
              </div>
            </div>
          </div>
        </section>

        <section className="panel chart-xl" onClick={() => setSelectedStep(currentStep?.step ?? null)}>
          <h2>Systemic Risk Over Time</h2>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={visibleRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="step" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" domain={[0, 1.2]} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
              <Legend />
              <ReferenceLine x={40} stroke="#ef4444" strokeDasharray="4 4" label="Injection starts" />
              <Line type="monotone" dataKey="ungovernedRisk" stroke="#f97316" dot={false} name="Ungoverned Risk" strokeWidth={2} />
              <Line type="monotone" dataKey="governedRisk" stroke="#22c55e" dot={false} name="Governed Risk" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </section>

        <section className="panel chart-xl">
          <h2>Authority Weight Migration</h2>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={visibleRows} stackOffset="expand">
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="step" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
              <Legend />
              <ReferenceLine x={40} stroke="#ef4444" strokeDasharray="4 4" />
              {AGENTS.map((agent) => (
                <Area
                  key={agent}
                  type="monotone"
                  dataKey={agent}
                  stackId="1"
                  stroke={AGENT_COLORS[agent]}
                  fill={AGENT_COLORS[agent]}
                  fillOpacity={0.65}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </section>

        <section className="panel chart-grid">
          <h2>Sector Health (UNG vs GOV)</h2>
          <div className="mini-charts">
            {[{
              keyUng: "congestionUng",
              keyGov: "congestionGov",
              title: "Telecom Congestion",
              yDomain: [0, 1]
            }, {
              keyUng: "frequencyUng",
              keyGov: "frequencyGov",
              title: "Power |Frequency Delta|",
              yDomain: [0, 1]
            }, {
              keyUng: "waterUng",
              keyGov: "waterGov",
              title: "Water Sensor Integrity",
              yDomain: [0, 1]
            }, {
              keyUng: "gpsUng",
              keyGov: "gpsGov",
              title: "Aviation GPS Sync Error",
              yDomain: [0, 1]
            }].map((c) => (
              <div key={c.title} className="mini-panel">
                <div className="mini-title">{c.title}</div>
                <ResponsiveContainer width="100%" height={160}>
                  <LineChart data={visibleRows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="step" hide />
                    <YAxis stroke="#94a3b8" domain={c.yDomain as [number, number]} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <ReferenceLine x={40} stroke="#ef4444" strokeDasharray="3 3" />
                    <Line type="monotone" dataKey={c.keyUng} stroke="#f97316" dot={false} name="UNG" />
                    <Line type="monotone" dataKey={c.keyGov} stroke="#22c55e" dot={false} name="GOV" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>
        </section>

        <section className="panel suppression-map">
          <h2>Suppression Timeline</h2>
          <div className="heatmap-wrap">
            {AGENTS.map((agent) => (
              <div key={agent} className="heatmap-row">
                <div className="heatmap-label">{agent}</div>
                <div className="heatmap-cells">
                  {data.steps.map((s) => (
                    <button
                      type="button"
                      key={`${agent}-${s.step}`}
                      className="heat-cell"
                      style={{ background: STATUS_COLOR[s.statuses[agent]] }}
                      title={`Step ${s.step} • ${s.statuses[agent]}`}
                      onClick={() => {
                        const idx = Math.max(0, s.step - 1);
                        setCurrent(idx);
                        setSelectedStep(s.step);
                      }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="legend-line">
            <span><i style={{ background: STATUS_COLOR.active }} />Active</span>
            <span><i style={{ background: STATUS_COLOR.probation }} />Probation</span>
            <span><i style={{ background: STATUS_COLOR.suppressed }} />Suppressed</span>
          </div>
        </section>

        <section className="panel event-stream">
          <h2>Governance Event Stream</h2>
          <div className="event-list" ref={logRef}>
            {visibleEvents.length === 0 && <div className="event muted">No events yet.</div>}
            {visibleEvents.map((e, i) => (
              <div key={`${e.step}-${i}`} className={`event ${e.severity}`}>
                <span className="event-step">{String(e.step).padStart(3, "0")}</span>
                <span className="event-type">{e.type}</span>
                <span className="event-text">{e.text}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel audit-panel">
          <h2>Audit Proof</h2>
          <div className="audit-block">
            <div>Kernel unchanged: GovernanceLoop + TrustEngine + MutationEngine</div>
            <div className="muted">Selected Step: {selected?.step ?? "N/A"}</div>
            <div className="audit-grid">
              <div>
                <strong>Task</strong>
                <pre>{JSON.stringify(selected ? { step: selected.step, systemicRiskGov: selected.governedRisk } : {}, null, 2)}</pre>
              </div>
              <div>
                <strong>Result</strong>
                <pre>{JSON.stringify(selected?.suppressed ?? [], null, 2)}</pre>
              </div>
              <div>
                <strong>Governance Event</strong>
                <pre>{JSON.stringify(selected?.events?.[0] ?? { type: "none", text: "no event" }, null, 2)}</pre>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="playback-bar">
        <button onClick={() => setPlaying((p) => !p)}>{playing ? "Pause" : "Play"}</button>
        <button onClick={() => setCurrent((c) => Math.max(0, c - 1))}>-1</button>
        <button onClick={() => setCurrent((c) => Math.max(0, c - 5))}>-5</button>
        <button onClick={() => setCurrent((c) => Math.min(data.steps.length - 1, c + 1))}>+1</button>
        <button onClick={() => setCurrent((c) => Math.min(data.steps.length - 1, c + 5))}>+5</button>
        <button onClick={() => setCurrent(Math.min(Math.max(39, 0), Math.max(data.steps.length - 1, 0)))}>Jump Injection</button>
        <div className="speed-group">
          {(Object.keys(speedMap) as Array<keyof typeof speedMap>).map((s) => (
            <button key={s} className={speed === s ? "active" : ""} onClick={() => setSpeed(s)}>{s}</button>
          ))}
        </div>
        <input
          className="scrubber"
          type="range"
          min={0}
          max={Math.max(0, data.steps.length - 1)}
          value={current}
          onChange={(e) => setCurrent(Number(e.target.value))}
        />
      </footer>
    </div>
  );
}

export default App;
