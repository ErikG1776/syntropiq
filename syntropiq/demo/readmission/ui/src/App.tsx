import { useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

type Status = "ACTIVE" | "PROBATION" | "SUPPRESSED";

const AGENTS = ["rapid_screen", "predictive", "conservative"] as const;

const AGENT_COLORS: Record<string, string> = {
  rapid_screen: "#f97316",
  predictive: "#22c55e",
  conservative: "#38bdf8"
};

type TimelineRow = {
  cycle: number;
  phase: string;
  batchSize: number;
  successes: number;
  failures: number;
  missed: number;
  cyclePenalty: number;
  cumulativePenalty: number;
  trustScores: Record<string, number>;
  statuses: Record<string, Status>;
  suppressed: string[];
  thresholds: {
    trust_threshold: number;
    suppression_threshold: number;
    drift_delta: number;
    drift_agent_threshold: number;
  };
  events: string[];
  authorityProxy: Record<string, number>;
};

type Summary = {
  demo: string;
  dataSource: string;
  cycles: number;
  batchSize: number;
  readmissionPenalty: number;
  totalPenalties: number;
  preventedPenalties: number;
  missedReadmissions: number;
  caughtReadmissions: number;
  driftAgentId: string;
  driftStartsCycle: number;
  suppressionActiveCycles: number[];
  overallSuccessRate: number;
  validReflections: number;
  totalExecutions: number;
};

type Parsed = {
  summary: Summary;
  timeline: TimelineRow[];
  payloadExamples: { task_example?: unknown; result_example?: unknown };
};

const SPEEDS: Record<string, number> = {
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

function str(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}

function arr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}

function rec(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
}

function toStatus(v: unknown): Status {
  const s = str(v, "ACTIVE").toUpperCase();
  if (s === "SUPPRESSED") return "SUPPRESSED";
  if (s === "PROBATION") return "PROBATION";
  return "ACTIVE";
}

function parse(raw: unknown): Parsed {
  const root = rec(raw);
  const s = rec(root.summary);
  const timelineRaw = arr(root.timeline);

  const summary: Summary = {
    demo: str(s.demo, "readmission"),
    dataSource: str(s.data_source, "Unknown"),
    cycles: num(s.cycles, 30),
    batchSize: num(s.batch_size, 8),
    readmissionPenalty: num(s.readmission_penalty_usd, 15200),
    totalPenalties: num(s.total_penalties_usd),
    preventedPenalties: num(s.penalties_prevented_usd),
    missedReadmissions: num(s.missed_readmissions),
    caughtReadmissions: num(s.caught_readmissions),
    driftAgentId: str(s.drift_agent_id, "rapid_screen"),
    driftStartsCycle: num(s.drift_starts_cycle, 3),
    suppressionActiveCycles: arr(s.suppression_active_cycles).map((x) => num(x)).filter((x) => x > 0),
    overallSuccessRate: num(s.overall_success_rate),
    validReflections: num(s.valid_reflections),
    totalExecutions: num(s.total_executions)
  };

  const timeline: TimelineRow[] = timelineRaw.map((r, i) => {
    const row = rec(r);
    const trustScoresRaw = rec(row.trust_scores);
    const statusesRaw = rec(row.statuses);
    const thresholdsRaw = rec(row.thresholds);

    const trustScores: Record<string, number> = {};
    const statuses: Record<string, Status> = {};

    AGENTS.forEach((aid) => {
      trustScores[aid] = num(trustScoresRaw[aid]);
      statuses[aid] = toStatus(statusesRaw[aid]);
    });

    const suppressed = arr(row.suppressed_agents).map((x) => String(x));
    AGENTS.forEach((aid) => {
      if (suppressed.includes(aid)) statuses[aid] = "SUPPRESSED";
    });

    const authorityRaw: Record<string, number> = {};
    AGENTS.forEach((aid) => {
      authorityRaw[aid] = statuses[aid] === "SUPPRESSED" ? 0 : Math.max(0, trustScores[aid]);
    });
    const authorityTotal = AGENTS.reduce((acc, aid) => acc + authorityRaw[aid], 0);
    const authorityProxy: Record<string, number> = {};
    AGENTS.forEach((aid) => {
      authorityProxy[aid] = authorityTotal > 0 ? authorityRaw[aid] / authorityTotal : 0;
    });

    return {
      cycle: Math.max(1, Math.floor(num(row.cycle, i + 1))),
      phase: str(row.phase, "UNKNOWN"),
      batchSize: num(row.batch_size),
      successes: num(row.successes),
      failures: num(row.failures),
      missed: num(row.missed_readmissions),
      cyclePenalty: num(row.cycle_penalty_usd),
      cumulativePenalty: num(row.cumulative_penalty_usd),
      trustScores,
      statuses,
      suppressed,
      thresholds: {
        trust_threshold: num(thresholdsRaw.trust_threshold),
        suppression_threshold: num(thresholdsRaw.suppression_threshold),
        drift_delta: num(thresholdsRaw.drift_delta),
        drift_agent_threshold: num(thresholdsRaw.drift_agent_threshold)
      },
      events: arr(row.events).map((e) => String(e)),
      authorityProxy
    };
  });

  return {
    summary,
    timeline,
    payloadExamples: rec(root.payload_examples) as { task_example?: unknown; result_example?: unknown }
  };
}

function money(v: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);
}

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function App() {
  const [data, setData] = useState<Parsed>({
    summary: {
      demo: "readmission",
      dataSource: "Unknown",
      cycles: 30,
      batchSize: 8,
      readmissionPenalty: 15200,
      totalPenalties: 0,
      preventedPenalties: 0,
      missedReadmissions: 0,
      caughtReadmissions: 0,
      driftAgentId: "rapid_screen",
      driftStartsCycle: 3,
      suppressionActiveCycles: [],
      overallSuccessRate: 0,
      validReflections: 0,
      totalExecutions: 0
    },
    timeline: [],
    payloadExamples: {}
  });

  const [current, setCurrent] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<keyof typeof SPEEDS>("1x");

  const eventRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetch("/readmission_results.json")
      .then((r) => r.json())
      .then((json) => setData(parse(json)))
      .catch(() => setData(parse({ summary: {}, timeline: [] })));
  }, []);

  useEffect(() => {
    if (!playing || data.timeline.length === 0) return;
    const id = window.setInterval(() => {
      setCurrent((c) => {
        if (c >= data.timeline.length - 1) {
          setPlaying(false);
          return c;
        }
        return c + 1;
      });
    }, SPEEDS[speed]);
    return () => clearInterval(id);
  }, [playing, speed, data.timeline.length]);

  const currentRow = data.timeline[current] ?? null;

  const chartRows = useMemo(
    () =>
      data.timeline.map((t) => ({
        cycle: t.cycle,
        penaltyCycle: t.cyclePenalty,
        penaltyCum: t.cumulativePenalty,
        trustRapid: t.trustScores.rapid_screen,
        trustPredictive: t.trustScores.predictive,
        trustConservative: t.trustScores.conservative,
        suppressionThreshold: t.thresholds.suppression_threshold,
        authorityRapid: t.authorityProxy.rapid_screen,
        authorityPredictive: t.authorityProxy.predictive,
        authorityConservative: t.authorityProxy.conservative,
        missed: t.missed,
        statusRapid: t.statuses.rapid_screen,
        statusPredictive: t.statuses.predictive,
        statusConservative: t.statuses.conservative
      })),
    [data.timeline]
  );

  const visibleRows = chartRows.slice(0, current + 1);

  const eventRows = useMemo(() => {
    const rows: Array<{ cycle: number; text: string; severity: string }> = [];
    data.timeline.forEach((t) => {
      t.events.forEach((e) => {
        const lower = e.toLowerCase();
        let severity = "neutral";
        if (lower.includes("suppressed") || lower.includes("missed readmission")) severity = "red";
        else if (lower.includes("drift detected") || lower.includes("probation")) severity = "amber";
        else if (lower.includes("loosened")) severity = "blue";
        else if (lower.includes("tightened") || lower.includes("mutation")) severity = "purple";
        else if (lower.includes("redeemed") || lower.includes("recovered")) severity = "green";
        rows.push({ cycle: t.cycle, text: e, severity });
      });
    });
    return rows;
  }, [data.timeline]);

  const visibleEvents = useMemo(
    () => eventRows.filter((e) => e.cycle <= (currentRow?.cycle ?? 0)).slice(-180),
    [eventRows, currentRow]
  );

  useEffect(() => {
    if (!eventRef.current) return;
    eventRef.current.scrollTop = eventRef.current.scrollHeight;
  }, [visibleEvents.length]);

  const suppressionWindow = useMemo(() => {
    const cycles = data.summary.suppressionActiveCycles;
    if (cycles.length === 0) return null;
    return { start: Math.min(...cycles), end: Math.max(...cycles) };
  }, [data.summary.suppressionActiveCycles]);

  const cycleLabel = `${String(currentRow?.cycle ?? 0).padStart(2, "0")} / ${String(data.timeline.length || data.summary.cycles).padStart(2, "0")}`;
  const driftActive = (currentRow?.cycle ?? 0) >= data.summary.driftStartsCycle;
  const driftSuppressed = currentRow?.statuses?.[data.summary.driftAgentId] === "SUPPRESSED";

  return (
    <div className="shell">
      <header className="header">
        <div className="title">SYNTROPIQ — Hospital Readmission Governance</div>
        <div className="badges">
          <span className="badge">CYCLE {cycleLabel}</span>
          <span className={`badge ${driftActive ? "warn" : "muted"}`}>DRIFT: {driftActive ? "ACTIVE" : "INACTIVE"}</span>
          <span className={`badge ${driftSuppressed ? "danger" : "muted"}`}>
            SUPPRESSION: {driftSuppressed ? "ACTIVE" : "INACTIVE"}
          </span>
        </div>
      </header>

      <main className="grid">
        <section className="panel kpis">
          <div className="kpi">
            <div className="klabel">Total Penalties</div>
            <div className="kvalue">{money(data.summary.totalPenalties)}</div>
          </div>
          <div className="kpi">
            <div className="klabel">Penalties Prevented</div>
            <div className="kvalue emphasis">{money(data.summary.preventedPenalties)}</div>
          </div>
          <div className="kpi">
            <div className="klabel">Missed Readmissions</div>
            <div className="kvalue">{data.summary.missedReadmissions}</div>
          </div>
          <div className="kpi">
            <div className="klabel">Overall Success Rate</div>
            <div className="kvalue">{pct(data.summary.overallSuccessRate)}</div>
          </div>
        </section>

        <section className="panel">
          <h2>Authority Proxy Migration</h2>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={visibleRows}>
              <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
              <XAxis dataKey="cycle" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <Tooltip contentStyle={{ background: "#0b1220", border: "1px solid #334155" }} />
              <Legend />
              <ReferenceLine x={data.summary.driftStartsCycle} stroke="#ef4444" strokeDasharray="4 4" label="Drift starts" />
              {suppressionWindow && (
                <ReferenceArea x1={suppressionWindow.start} x2={suppressionWindow.end} fill="#7f1d1d" fillOpacity={0.2} />
              )}
              <Area type="monotone" dataKey="authorityRapid" stackId="1" stroke={AGENT_COLORS.rapid_screen} fill={AGENT_COLORS.rapid_screen} />
              <Area type="monotone" dataKey="authorityPredictive" stackId="1" stroke={AGENT_COLORS.predictive} fill={AGENT_COLORS.predictive} />
              <Area type="monotone" dataKey="authorityConservative" stackId="1" stroke={AGENT_COLORS.conservative} fill={AGENT_COLORS.conservative} />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        <section className="panel">
          <h2>Trust Trajectories</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={visibleRows}>
              <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
              <XAxis dataKey="cycle" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" domain={[0, 1]} />
              <Tooltip
                contentStyle={{ background: "#0b1220", border: "1px solid #334155" }}
                formatter={(v, n, ctx) => {
                  const key = String(n);
                  if (key.includes("trust")) {
                    const cycle = ctx?.payload?.cycle;
                    const row = data.timeline.find((x) => x.cycle === cycle);
                    if (row) {
                      if (key === "trustRapid") return [`${Number(v).toFixed(3)} (${row.statuses.rapid_screen})`, "rapid_screen"];
                      if (key === "trustPredictive") return [`${Number(v).toFixed(3)} (${row.statuses.predictive})`, "predictive"];
                      if (key === "trustConservative") return [`${Number(v).toFixed(3)} (${row.statuses.conservative})`, "conservative"];
                    }
                  }
                  return [v, n];
                }}
              />
              <Legend />
              <ReferenceLine y={currentRow?.thresholds?.suppression_threshold ?? 0.85} stroke="#ef4444" strokeDasharray="3 3" label="Suppression threshold" />
              <Line type="monotone" dataKey="trustRapid" stroke={AGENT_COLORS.rapid_screen} dot={false} name="rapid_screen" />
              <Line type="monotone" dataKey="trustPredictive" stroke={AGENT_COLORS.predictive} dot={false} name="predictive" />
              <Line type="monotone" dataKey="trustConservative" stroke={AGENT_COLORS.conservative} dot={false} name="conservative" />
            </LineChart>
          </ResponsiveContainer>
        </section>

        <section className="panel">
          <h2>Penalty Accumulation</h2>
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={visibleRows}>
              <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
              <XAxis dataKey="cycle" stroke="#94a3b8" />
              <YAxis yAxisId="left" stroke="#94a3b8" />
              <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: "#0b1220", border: "1px solid #334155" }} />
              <Legend />
              <Bar yAxisId="left" dataKey="penaltyCycle" fill="#dc2626" name="Cycle Penalty ($)" />
              <Line yAxisId="right" type="monotone" dataKey="penaltyCum" stroke="#facc15" dot={false} name="Cumulative Penalty ($)" />
            </ComposedChart>
          </ResponsiveContainer>
        </section>

        <section className="panel event-panel">
          <h2>Governance Event Stream</h2>
          <div className="events" ref={eventRef}>
            {visibleEvents.map((e, i) => (
              <button
                className={`event-row ${e.severity}`}
                key={`${e.cycle}-${i}`}
                onClick={() => {
                  const idx = Math.max(0, e.cycle - 1);
                  setCurrent(idx);
                }}
              >
                <span className="ev-cycle">{String(e.cycle).padStart(2, "0")}</span>
                <span className="ev-text">{e.text}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="panel audit">
          <h2>Audit Panel</h2>
          <div className="audit-grid">
            <div>
              <div className="label">trust_scores</div>
              <pre>{JSON.stringify(currentRow?.trustScores ?? {}, null, 2)}</pre>
            </div>
            <div>
              <div className="label">statuses</div>
              <pre>{JSON.stringify(currentRow?.statuses ?? {}, null, 2)}</pre>
            </div>
            <div>
              <div className="label">thresholds</div>
              <pre>{JSON.stringify(currentRow?.thresholds ?? {}, null, 2)}</pre>
            </div>
            <div>
              <div className="label">events</div>
              <pre>{JSON.stringify(currentRow?.events ?? [], null, 2)}</pre>
            </div>
            <div>
              <div className="label">task_example</div>
              <pre>{JSON.stringify(data.payloadExamples.task_example ?? {}, null, 2)}</pre>
            </div>
            <div>
              <div className="label">result_example</div>
              <pre>{JSON.stringify(data.payloadExamples.result_example ?? {}, null, 2)}</pre>
            </div>
          </div>
        </section>
      </main>

      <footer className="playback">
        <button onClick={() => setPlaying((p) => !p)}>{playing ? "Pause" : "Play"}</button>
        <button onClick={() => setCurrent((c) => Math.max(0, c - 1))}>-1</button>
        <button onClick={() => setCurrent((c) => Math.max(0, c - 5))}>-5</button>
        <button onClick={() => setCurrent((c) => Math.min(data.timeline.length - 1, c + 1))}>+1</button>
        <button onClick={() => setCurrent((c) => Math.min(data.timeline.length - 1, c + 5))}>+5</button>
        <button onClick={() => setCurrent(Math.max(0, data.summary.driftStartsCycle - 1))}>JUMP TO DRIFT</button>
        <button
          onClick={() => {
            const s = data.summary.suppressionActiveCycles[0] ?? 13;
            setCurrent(Math.max(0, s - 1));
          }}
        >
          JUMP TO SUPPRESSION
        </button>
        <div className="speed-wrap">
          {(Object.keys(SPEEDS) as Array<keyof typeof SPEEDS>).map((s) => (
            <button key={s} className={speed === s ? "active" : ""} onClick={() => setSpeed(s)}>{s}</button>
          ))}
        </div>
        <input
          type="range"
          className="slider"
          min={0}
          max={Math.max(0, data.timeline.length - 1)}
          value={current}
          onChange={(e) => setCurrent(Number(e.target.value))}
        />
      </footer>
    </div>
  );
}

export default App;
