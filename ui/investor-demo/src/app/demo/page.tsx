"use client";

import { useState, useEffect, useRef } from "react";
import { useDemoPlayer } from "@/hooks/use-demo-player";
import type { PlaySpeed } from "@/hooks/use-demo-player";
import type { GovernanceEvent, DomainId } from "@/lib/demo-data";
import { DOMAINS, getAgentDisplayName, getAgentStatus } from "@/lib/demo-data";
import { computeEnterpriseProjection } from "@/lib/enterprise-scaling";
import { cn, formatCurrency } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import {
  Play,
  Pause,
  RotateCcw,
  Activity,
  ShieldCheck,
  ShieldOff,
  ShieldAlert,
  AlertTriangle,
  Settings,
  TrendingDown,
  ChevronDown,
  CheckCircle2,
  Link2,
  Lock,
} from "lucide-react";
import Link from "next/link";

// ─── Agent Colors ──────────────────────────────────────────────

const AGENT_COLORS: Record<string, string> = {
  rule_engine: "#3b82f6",
  ml_scorer: "#a78bfa",
  ensemble: "#f43f5e",
  conservative: "#3b82f6",
  balanced: "#a78bfa",
  growth: "#f43f5e",
  predictive: "#a78bfa",
  rapid_screen: "#f43f5e",
};

// ─── Narrative Event: group adjacent same-phase cycles ─────────

interface NarrativeEvent {
  id: string;
  type: GovernanceEvent["type"] | "baseline" | "stabilized" | "phase_change";
  cycleStart: number;
  cycleEnd: number;
  phase: string;
  severity: "info" | "warning" | "danger" | "success";
  title: string;
  description: string;
  agent?: string;
  metrics?: Record<string, string | number>;
}

function buildNarrativeEvents(
  events: GovernanceEvent[],
  timeline: {
    cycle: number;
    phase: string;
    trust_scores: Record<string, number>;
    trust_threshold?: number;
    suppression_threshold?: number;
    suppressed_agents: string[];
  }[],
  driftAgent: string
): NarrativeEvent[] {
  const narrative: NarrativeEvent[] = [];
  if (timeline.length === 0) return narrative;

  // Group cycles by phase runs
  let runStart = 0;
  for (let i = 1; i <= timeline.length; i++) {
    const isEnd = i === timeline.length;
    const phaseChanged =
      !isEnd && timeline[i].phase !== timeline[runStart].phase;
    if (isEnd || phaseChanged) {
      const startCycle = timeline[runStart].cycle;
      const endCycle = timeline[i - 1].cycle;
      const phase = timeline[runStart].phase;

      // Find governance events in this run
      const runEvents = events.filter(
        (e) => e.cycle >= startCycle && e.cycle <= endCycle
      );

      // If no governance events, emit a phase summary
      if (runEvents.length === 0) {
        const isBaseline =
          phase.includes("RAMP") ||
          (startCycle <= 3 && !phase.includes("STRESS"));
        const isStable = phase.includes("STEADY");
        narrative.push({
          id: `phase-${startCycle}`,
          type: isBaseline
            ? "baseline"
            : isStable
              ? "stabilized"
              : "phase_change",
          cycleStart: startCycle,
          cycleEnd: endCycle,
          phase,
          severity: isStable ? "success" : "info",
          title: isBaseline
            ? "Baseline Monitoring"
            : isStable
              ? "System Stabilized"
              : phase.includes("RECOVERY")
                ? "Recovery Phase"
                : "Phase Transition",
          description: isBaseline
            ? `All agents operating normally across cycles ${startCycle}\u2013${endCycle}. Building trust history on mixed workload.`
            : isStable
              ? `Governance engine has stabilized the system. All agents above trust threshold.`
              : phase.includes("RECOVERY")
                ? `Low-risk workload allowing suppressed agents to rehabilitate through probation.`
                : `System entered ${phase.toLowerCase()}.`,
        });
      }

      // Emit individual governance events
      for (const evt of runEvents) {
        if (evt.type === "loss_detected") continue;

        const cycleData = timeline.find((c) => c.cycle === evt.cycle);
        const trustScore =
          cycleData?.trust_scores[evt.agent ?? driftAgent];
        const threshold = cycleData?.trust_threshold;

        let title = "";
        let description = "";
        switch (evt.type) {
          case "drift_detected":
            title = "Drift Detected";
            description = `${getAgentDisplayName(evt.agent ?? driftAgent)} showing anomalous trust decay. Governance engine is monitoring.`;
            break;
          case "agent_suppressed":
            title = "Agent Suppressed";
            description = `${getAgentDisplayName(evt.agent ?? "")} isolated from production routing. Trust ${trustScore?.toFixed(3) ?? "?"} fell below threshold ${threshold?.toFixed(3) ?? "?"}. High-risk decisions rerouted to trusted agents.`;
            break;
          case "agent_restored":
            title = "Agent Restored";
            description = `${getAgentDisplayName(evt.agent ?? "")} completed probation and returned to active duty. Trust recovered above threshold.`;
            break;
          case "threshold_mutated":
            title = "Threshold Adapted";
            description = evt.message;
            break;
          case "probation_started":
            title = "Probation Started";
            description = `${getAgentDisplayName(evt.agent ?? "")} placed on probation \u2014 receiving only low-risk tasks to prove reliability.`;
            break;
          default:
            title = evt.type.replace(/_/g, " ");
            description = evt.message;
        }

        narrative.push({
          id: `${evt.type}-${evt.cycle}-${evt.agent ?? ""}`,
          type: evt.type,
          cycleStart: evt.cycle,
          cycleEnd: evt.cycle,
          phase,
          severity: evt.severity,
          agent: evt.agent,
          title,
          description,
          metrics: trustScore
            ? {
                trust: trustScore.toFixed(3),
                ...(threshold ? { threshold: threshold.toFixed(3) } : {}),
              }
            : undefined,
        });
      }

      runStart = i;
    }
  }

  return narrative;
}

// ─── Event card accent colors ──────────────────────────────────

const eventAccent: Record<string, string> = {
  baseline: "border-l-blue-500/60",
  drift_detected: "border-l-amber-500/80",
  agent_suppressed: "border-l-red-500/80",
  threshold_mutated: "border-l-blue-400/60",
  probation_started: "border-l-amber-400/60",
  agent_restored: "border-l-emerald-500/80",
  stabilized: "border-l-emerald-400/60",
  phase_change: "border-l-slate-500/40",
  loss_detected: "border-l-red-400/60",
  system_healthy: "border-l-emerald-400/60",
};

const eventIcon: Record<string, typeof Activity> = {
  baseline: Activity,
  drift_detected: AlertTriangle,
  agent_suppressed: ShieldOff,
  threshold_mutated: Settings,
  probation_started: ShieldAlert,
  agent_restored: ShieldCheck,
  stabilized: CheckCircle2,
  phase_change: Activity,
  loss_detected: TrendingDown,
  system_healthy: CheckCircle2,
};

const severityBadge: Record<
  string,
  "info" | "warning" | "destructive" | "success"
> = {
  info: "info",
  warning: "warning",
  danger: "destructive",
  success: "success",
};

// ─── Chart tooltip ─────────────────────────────────────────────

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: number;
}) {
  if (!active || !payload) return null;
  return (
    <div className="bg-[#0f172a] border border-[#1e293b] rounded-xl p-3 shadow-2xl">
      <p className="text-[#64748b] text-[10px] font-mono mb-2">
        Cycle {label}
      </p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2 mb-1 last:mb-0">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: p.color }}
          />
          <span className="text-xs text-[#94a3b8]">
            {getAgentDisplayName(p.name)}
          </span>
          <span className="ml-auto text-xs font-mono font-medium tabular-nums pl-4 text-white">
            {p.value?.toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Under the Hood panel ──────────────────────────────────────

function UnderTheHood({
  event,
  timeline,
}: {
  event: NarrativeEvent;
  timeline: {
    cycle: number;
    trust_scores: Record<string, number>;
    trust_threshold?: number;
    suppression_threshold?: number;
    drift_threshold?: number;
  }[];
}) {
  const [open, setOpen] = useState(false);
  const cycle = timeline.find((c) => c.cycle === event.cycleStart);
  if (!cycle) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[11px] text-[#64748b] hover:text-[#94a3b8] transition-colors cursor-pointer"
      >
        <ChevronDown
          className={cn(
            "w-3 h-3 transition-transform",
            open && "rotate-180"
          )}
        />
        Under the Hood
      </button>
      {open && (
        <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-[11px] bg-[#0f172a]/60 rounded-lg p-3 border border-[#1e293b]/60">
          {Object.entries(cycle.trust_scores).map(([agent, score]) => (
            <div key={agent} className="flex justify-between">
              <span className="text-[#64748b]">
                {getAgentDisplayName(agent)}
              </span>
              <span className="font-mono text-[#cbd5e1]">
                {score.toFixed(3)}
              </span>
            </div>
          ))}
          {cycle.trust_threshold !== undefined && (
            <div className="flex justify-between">
              <span className="text-[#64748b]">Trust {"\u03c4"}</span>
              <span className="font-mono text-[#cbd5e1]">
                {cycle.trust_threshold.toFixed(3)}
              </span>
            </div>
          )}
          {cycle.suppression_threshold !== undefined && (
            <div className="flex justify-between">
              <span className="text-[#64748b]">
                Suppress {"\u03c4\u209b"}
              </span>
              <span className="font-mono text-[#cbd5e1]">
                {cycle.suppression_threshold.toFixed(3)}
              </span>
            </div>
          )}
          {cycle.drift_threshold !== undefined && (
            <div className="flex justify-between">
              <span className="text-[#64748b]">Drift {"\u0394"}</span>
              <span className="font-mono text-[#cbd5e1]">
                {cycle.drift_threshold.toFixed(3)}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Animated number ───────────────────────────────────────────

function useAnimatedValue(target: number, duration = 800): number {
  const [value, setValue] = useState(0);
  const prevRef = useRef(0);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const start = prevRef.current;
    const diff = target - start;
    if (Math.abs(diff) < 0.5) {
      setValue(target);
      prevRef.current = target;
      return;
    }
    const startTime = performance.now();
    function animate(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(start + diff * eased);
      if (progress < 1) frameRef.current = requestAnimationFrame(animate);
      else prevRef.current = target;
    }
    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration]);

  return value;
}

// ─── Main Demo Page ────────────────────────────────────────────

export default function DemoPage() {
  const player = useDemoPlayer();
  const projection = computeEnterpriseProjection(
    player.stats,
    player.domainConfig
  );
  const animatedSavings = useAnimatedValue(projection.netAnnualSavings);
  const eventScrollRef = useRef<HTMLDivElement>(null);

  const narrativeEvents = buildNarrativeEvents(
    player.visibleEvents,
    player.timeline.filter(
      (c) => c.cycle <= (player.currentCycle?.cycle ?? -1)
    ),
    player.domainConfig.driftAgent
  );

  // Find drift zone for chart shading
  const driftStart = player.timeline.find((c) =>
    c.phase.includes("STRESS")
  )?.cycle;
  const driftEnd = player.timeline
    .filter((c) => c.phase.includes("STRESS"))
    .pop()?.cycle;

  // Auto-scroll event timeline
  useEffect(() => {
    if (eventScrollRef.current) {
      eventScrollRef.current.scrollTo({
        top: eventScrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [narrativeEvents.length]);

  // Has any suppression happened?
  const hasGovernanceAction = player.visibleEvents.some(
    (e) => e.type === "agent_suppressed" || e.type === "threshold_mutated"
  );

  const progress =
    player.timeline.length > 0
      ? ((player.currentCycleIndex + 1) / player.timeline.length) * 100
      : 0;

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Sticky Header ──────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-background/95 backdrop-blur-md border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-3">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
                  <Activity className="w-3.5 h-3.5 text-white" />
                </div>
                <span className="text-base font-semibold tracking-tight">
                  syntropiq
                </span>
              </Link>
              <div className="h-5 w-px bg-border" />
              <span className="text-sm text-muted-foreground">
                {player.domainConfig.label}
              </span>
            </div>

            <div className="flex items-center gap-3">
              {/* Domain switcher */}
              <div className="flex items-center gap-0.5 bg-card rounded-lg p-0.5 border border-border">
                {(Object.keys(DOMAINS) as DomainId[]).map((id) => (
                  <button
                    key={id}
                    onClick={() => player.setDomain(id)}
                    className={cn(
                      "px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer",
                      player.domain === id
                        ? "bg-muted text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {DOMAINS[id].shortLabel}
                  </button>
                ))}
              </div>

              {/* Playback */}
              <div className="flex items-center gap-1.5">
                {player.playState === "playing" ? (
                  <button
                    onClick={player.pause}
                    className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center hover:bg-muted/80 transition-colors cursor-pointer"
                  >
                    <Pause className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <button
                    onClick={player.play}
                    className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center hover:bg-primary/90 transition-colors cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5 text-white" />
                  </button>
                )}
                <button
                  onClick={player.reset}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
              </div>

              {/* Speed */}
              <div className="flex items-center gap-0.5 bg-card rounded-lg p-0.5 border border-border">
                {([1, 2, 3] as PlaySpeed[]).map((s) => (
                  <button
                    key={s}
                    onClick={() => player.setSpeed(s)}
                    className={cn(
                      "px-2 py-1 rounded-md text-[11px] font-mono transition-all cursor-pointer",
                      player.speed === s
                        ? "bg-muted text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {s}x
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Progress bar */}
          <div className="flex items-center gap-3">
            <div
              className="flex-1 h-1 bg-muted rounded-full cursor-pointer overflow-hidden group"
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const pct = (e.clientX - rect.left) / rect.width;
                player.skipTo(Math.floor(pct * player.timeline.length));
              }}
            >
              <div
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-[11px] font-mono text-muted-foreground tabular-nums shrink-0">
              {Math.max(0, player.currentCycleIndex + 1)} /{" "}
              {player.timeline.length}
            </span>
          </div>
        </div>
      </header>

      {/* ── Main Content ──────────────────────────────────── */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8 space-y-8">
        {/* ── Agent Status Strip ──────────────────────────── */}
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {player.domainConfig.agentNames.map((agent) => {
            const trust =
              player.currentCycle?.trust_scores[agent] ?? 0;
            const status = player.currentCycle
              ? getAgentStatus(agent, player.currentCycle)
              : "active";
            const isDrift =
              agent === player.domainConfig.driftAgent;
            const color = AGENT_COLORS[agent] ?? "#64748b";

            const sparkData = player.trustHistory
              .slice(-12)
              .map((d) => d[agent] ?? 0);

            return (
              <div
                key={agent}
                className={cn(
                  "rounded-xl border p-5 transition-all duration-500",
                  status === "suppressed"
                    ? "border-destructive/30 bg-destructive/[0.04] pulse-danger"
                    : status === "probation"
                      ? "border-warning/20 bg-warning/[0.03]"
                      : "border-border bg-card"
                )}
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-sm font-medium">
                      {getAgentDisplayName(agent)}
                    </span>
                    {isDrift && (
                      <span className="text-[9px] font-mono text-muted-foreground border border-border rounded px-1.5 py-0.5">
                        DRIFT TARGET
                      </span>
                    )}
                  </div>
                  <Badge
                    variant={
                      status === "suppressed"
                        ? "destructive"
                        : status === "probation"
                          ? "warning"
                          : "success"
                    }
                  >
                    {status === "suppressed"
                      ? "Suppressed"
                      : status === "probation"
                        ? "Probation"
                        : "Active"}
                  </Badge>
                </div>

                <div className="flex items-end justify-between">
                  <span className="text-3xl font-bold font-mono tabular-nums tracking-tight">
                    {player.currentCycle
                      ? trust.toFixed(3)
                      : "\u2014"}
                  </span>

                  {sparkData.length > 1 && (
                    <svg
                      viewBox={`0 0 ${sparkData.length - 1} 1`}
                      className="w-16 h-8 opacity-40"
                      preserveAspectRatio="none"
                    >
                      <polyline
                        points={sparkData
                          .map(
                            (v, i) =>
                              `${i},${1 - (v - 0.5) * 2}`
                          )
                          .join(" ")}
                        fill="none"
                        stroke={color}
                        strokeWidth="0.08"
                        vectorEffect="non-scaling-stroke"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </div>
              </div>
            );
          })}
        </section>

        {/* ── Trust Trajectory Chart ──────────────────────── */}
        <section className="rounded-xl border border-border bg-card p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-sm font-semibold">
                Agent Trust Trajectories
              </h2>
              <p className="text-xs text-muted-foreground mt-1">
                Real-time trust scores across governance cycles
              </p>
            </div>
            <div className="flex items-center gap-5">
              {player.domainConfig.agentNames.map((agent) => (
                <div
                  key={agent}
                  className="flex items-center gap-2"
                >
                  <span
                    className="w-3 h-[2px] rounded-full block"
                    style={{
                      backgroundColor:
                        AGENT_COLORS[agent] ?? "#64748b",
                    }}
                  />
                  <span className="text-[11px] text-muted-foreground">
                    {getAgentDisplayName(agent)}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={420}>
            <LineChart
              data={player.trustHistory}
              margin={{ top: 8, right: 20, left: 0, bottom: 4 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(148,163,184,0.06)"
                vertical={false}
              />
              {driftStart !== undefined &&
                driftEnd !== undefined && (
                  <ReferenceArea
                    x1={driftStart}
                    x2={driftEnd}
                    y1={0.5}
                    y2={1.05}
                    fill="rgba(239,68,68,0.04)"
                    strokeOpacity={0}
                  />
                )}
              <XAxis
                dataKey="cycle"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: "#64748b" }}
                label={{
                  value: "Governance Cycle",
                  position: "insideBottom",
                  offset: -2,
                  style: { fontSize: 11, fill: "#64748b" },
                }}
              />
              <YAxis
                domain={[0.5, 1.05]}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: "#64748b" }}
                tickFormatter={(v: number) => v.toFixed(2)}
              />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine
                y={
                  player.currentCycle?.trust_threshold ?? 0.78
                }
                stroke="#eab308"
                strokeDasharray="8 6"
                strokeWidth={1}
                strokeOpacity={0.5}
                label={{
                  value: "\u03c4 trust",
                  position: "right",
                  style: {
                    fontSize: 10,
                    fill: "#eab308",
                    opacity: 0.6,
                  },
                }}
              />
              <ReferenceLine
                y={
                  player.currentCycle?.suppression_threshold ??
                  0.84
                }
                stroke="#ef4444"
                strokeDasharray="8 6"
                strokeWidth={1}
                strokeOpacity={0.35}
                label={{
                  value: "\u03c4 suppress",
                  position: "right",
                  style: {
                    fontSize: 10,
                    fill: "#ef4444",
                    opacity: 0.5,
                  },
                }}
              />
              {player.domainConfig.agentNames.map((agent) => (
                <Line
                  key={agent}
                  type="monotone"
                  dataKey={agent}
                  stroke={AGENT_COLORS[agent] ?? "#64748b"}
                  strokeWidth={
                    agent === player.domainConfig.driftAgent
                      ? 2.5
                      : 1.5
                  }
                  dot={false}
                  activeDot={{
                    r: 4,
                    stroke: AGENT_COLORS[agent] ?? "#64748b",
                    strokeWidth: 2,
                    fill: "#020617",
                  }}
                  animationDuration={400}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </section>

        {/* ── Event Timeline ──────────────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold">
              Governance Timeline
            </h2>
            <span className="text-[11px] font-mono text-muted-foreground">
              {narrativeEvents.length} events
            </span>
          </div>

          <div
            ref={eventScrollRef}
            className="space-y-4 max-h-[520px] overflow-y-auto pr-2"
          >
            {narrativeEvents.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground text-sm">
                Press play to begin the governance simulation
              </div>
            ) : (
              narrativeEvents.map((event) => {
                const Icon =
                  eventIcon[event.type] ?? Activity;
                return (
                  <div
                    key={event.id}
                    className={cn(
                      "rounded-xl border border-border bg-card p-5 border-l-[3px] fade-in",
                      eventAccent[event.type] ??
                        "border-l-muted-foreground/30"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className="shrink-0 mt-0.5">
                        <Icon
                          className={cn(
                            "w-4 h-4",
                            event.severity === "danger"
                              ? "text-destructive"
                              : event.severity === "warning"
                                ? "text-warning"
                                : event.severity === "success"
                                  ? "text-success"
                                  : "text-info"
                          )}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2.5 mb-1.5">
                          <span className="text-sm font-semibold">
                            {event.title}
                          </span>
                          <Badge
                            variant={
                              severityBadge[event.severity]
                            }
                          >
                            {event.type === "baseline"
                              ? "Baseline"
                              : event.type === "stabilized"
                                ? "Stable"
                                : event.type
                                    .replace(/_/g, " ")
                                    .replace(/\b\w/g, (c) =>
                                      c.toUpperCase()
                                    )}
                          </Badge>
                          <span className="ml-auto text-[10px] font-mono text-muted-foreground shrink-0">
                            {event.cycleStart ===
                            event.cycleEnd
                              ? `Cycle ${event.cycleStart}`
                              : `Cycles ${event.cycleStart}\u2013${event.cycleEnd}`}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {event.description}
                        </p>

                        {event.metrics && (
                          <div className="flex gap-4 mt-2">
                            {Object.entries(
                              event.metrics
                            ).map(([key, val]) => (
                              <span
                                key={key}
                                className="text-[10px] font-mono text-muted-foreground"
                              >
                                {key}:{" "}
                                <span className="text-foreground/80">
                                  {val}
                                </span>
                              </span>
                            ))}
                          </div>
                        )}

                        <UnderTheHood
                          event={event}
                          timeline={player.timeline}
                        />
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* ── Business Impact ─────────────────────────────── */}
        {hasGovernanceAction && (
          <section className="rounded-xl border border-border bg-card p-8 fade-in">
            <div className="text-center mb-8">
              <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-3">
                Annualized Enterprise Impact
              </p>
              <div className="text-5xl sm:text-6xl font-bold text-primary tabular-nums tracking-tight mb-2">
                {formatCurrency(animatedSavings)}
              </div>
              <p className="text-base text-muted-foreground">
                in annual losses prevented
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto mb-6">
              <div className="rounded-xl border border-destructive/15 bg-destructive/[0.04] p-4 text-center">
                <div className="flex items-center justify-center gap-1.5 mb-2">
                  <ShieldOff className="w-3.5 h-3.5 text-destructive opacity-60" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                    Without Governance
                  </span>
                </div>
                <span className="text-xl font-bold text-destructive tabular-nums">
                  {formatCurrency(projection.withoutGovernance)}
                </span>
                <span className="text-xs text-muted-foreground block mt-0.5">
                  annual risk exposure
                </span>
              </div>

              <div className="rounded-xl border border-success/15 bg-success/[0.04] p-4 text-center">
                <div className="flex items-center justify-center gap-1.5 mb-2">
                  <ShieldCheck className="w-3.5 h-3.5 text-success opacity-60" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                    With Syntropiq
                  </span>
                </div>
                <span className="text-xl font-bold text-success tabular-nums">
                  {formatCurrency(projection.withSyntropiq)}
                </span>
                <span className="text-xs text-muted-foreground block mt-0.5">
                  contained exposure
                </span>
              </div>
            </div>

            <div className="text-center">
              <p className="text-[10px] text-muted-foreground font-mono">
                Based on {projection.volumeLabel} | 0.3% fraud
                rate | $185 avg loss per event
                {projection.reductionPct > 0 &&
                  ` | ${projection.reductionPct.toFixed(0)}% governance reduction`}
              </p>
            </div>
          </section>
        )}

        {/* ── Certification Footer ────────────────────────── */}
        {player.playState === "finished" && (
          <section className="rounded-xl border border-success/20 bg-success/[0.03] p-6 fade-in">
            <div className="flex items-center justify-center gap-3 mb-4">
              <CheckCircle2 className="w-5 h-5 text-success" />
              <span className="text-base font-semibold text-success">
                Governance Certified
              </span>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3 h-3 text-success" />
                <span>R-Score: 1.000</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Link2 className="w-3 h-3 text-success" />
                <span>Audit Chains Verified</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Lock className="w-3 h-3 text-success" />
                <span>No Suppression Deadlock</span>
              </div>
              <div className="flex items-center gap-1.5">
                <ShieldCheck className="w-3 h-3 text-success" />
                <span>All Agents Restored</span>
              </div>
            </div>
          </section>
        )}
      </main>

      {/* ── Footer ────────────────────────────────────────── */}
      <footer className="border-t border-border mt-auto">
        <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Patent-pending autonomous governance technology
          </span>
          <span className="font-mono">syntropiq.com</span>
        </div>
      </footer>
    </div>
  );
}
