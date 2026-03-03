"use client";

import { useMemo } from "react";
import { AlertTriangle, CheckCircle2, ShieldAlert, ShieldCheck, SlidersHorizontal, Waves } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMoney } from "@/lib/governance";
import { useControlPlane } from "@/lib/control-plane-context";

const AGENT_COLORS = ["#2563eb", "#9333ea", "#059669", "#ea580c", "#dc2626"];

function TrustLegend({ agents }: { agents: string[] }) {
  const colors = ["#2563eb", "#9333ea", "#059669", "#ea580c", "#dc2626"];

  return (
    <div className="flex flex-wrap items-center gap-6 text-sm mt-4">
      {agents.map((agent, index) => (
        <div key={agent} className="flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: colors[index % colors.length] }}
          />
          <span className="text-zinc-700 dark:text-zinc-300 font-medium">
            {agent}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function OverviewPage() {
  const {
    narrative,
    currentCycle,
    cycles,
    visibleCycles,
    successRate,
    activeAgents,
    suppressedAgents,
    impact,
    chartData,
    driftRange,
    suppressionMarkers,
    allAgentIds,
    hasTriggeredGovernance,
    currentNewlySuppressed,
    currentNewlyRestored,
  } = useControlPlane();
  const firstDriftCycle = useMemo(
    () => visibleCycleIndex(visibleCycles, (cycle) => cycle.phase === "drift"),
    [visibleCycles]
  );
  const lastDriftCycle = useMemo(
    () => visibleCycleIndex(visibleCycles, (cycle) => cycle.phase === "drift", true),
    [visibleCycles]
  );
  const thresholdShiftReductionPct = useMemo(() => {
    const thresholdMutations = visibleCycles.reduce((count, cycle, index) => {
      if (index === 0) return count;
      const prev = visibleCycles[index - 1];
      const trustMoved =
        Math.abs((cycle.thresholds.trust_threshold ?? 0) - (prev.thresholds.trust_threshold ?? 0)) > 0.0001;
      const suppressionMoved =
        Math.abs((cycle.thresholds.suppression_threshold ?? 0) - (prev.thresholds.suppression_threshold ?? 0)) > 0.0001;
      return count + (trustMoved || suppressionMoved ? 1 : 0);
    }, 0);
    if (thresholdMutations === 0) return 0;
    const relativeToMaxAmplification = ((0.4 - impact.driftAmplification) / 0.4) * 100;
    return Math.max(0, Math.min(100, relativeToMaxAmplification));
  }, [visibleCycles, impact.driftAmplification]);
  const executiveCallout = useMemo(() => {
    if (!currentCycle) {
      return {
        Icon: ShieldCheck,
        title: "Governance Monitor Online",
        line1: "Baseline observation is active across all fraud models.",
        line2: "No intervention required in current playback window.",
        tone: "border-zinc-200 bg-zinc-50 text-zinc-700",
      };
    }

    const cyclePos = Math.max(0, cycles.findIndex((cycle) => cycle.cycle_index === currentCycle.cycle_index));
    const prev = cyclePos > 0 ? cycles[cyclePos - 1] : null;
    const thresholdMutated =
      !!prev &&
      (Math.abs((prev.thresholds.trust_threshold ?? 0) - (currentCycle.thresholds.trust_threshold ?? 0)) > 0.0001 ||
        Math.abs((prev.thresholds.suppression_threshold ?? 0) - (currentCycle.thresholds.suppression_threshold ?? 0)) > 0.0001);

    if (currentCycle.phase === "stabilized") {
      return {
        Icon: CheckCircle2,
        title: "System Stabilized",
        line1: "All agents are operating within certified trust thresholds.",
        line2: "Governance intervention cycle is complete for this incident.",
        tone: "border-emerald-200 bg-emerald-50 text-emerald-700",
      };
    }
    if (currentNewlySuppressed.length > 0) {
      return {
        Icon: ShieldAlert,
        title: "Suppression Triggered",
        line1: `${currentNewlySuppressed.join(", ")} isolated to contain model risk escalation.`,
        line2: "Transaction routing is now operating under containment policy.",
        tone: "border-red-200 bg-red-50 text-red-700",
      };
    }
    if (currentNewlyRestored.length > 0) {
      return {
        Icon: ShieldCheck,
        title: "Recovery In Progress",
        line1: `${currentNewlyRestored.join(", ")} restored under probation controls.`,
        line2: "Governance is validating trust performance before full reinstatement.",
        tone: "border-emerald-200 bg-emerald-50 text-emerald-700",
      };
    }
    if (thresholdMutated) {
      return {
        Icon: SlidersHorizontal,
        title: "Thresholds Mutated",
        line1: "Trust and suppression limits were adapted to current market conditions.",
        line2: "Policy mutation is enforcing tighter fraud containment sensitivity.",
        tone: "border-blue-200 bg-blue-50 text-blue-700",
      };
    }
    if (currentCycle.phase === "drift") {
      return {
        Icon: AlertTriangle,
        title: "Drift Escalation Detected",
        line1: "Trust degradation detected in active fraud scoring behavior.",
        line2: "Governance is preparing intervention paths before suppression.",
        tone: "border-amber-200 bg-amber-50 text-amber-700",
      };
    }

    return {
      Icon: ShieldCheck,
      title: "Baseline Monitoring",
      line1: "Fraud models are operating within expected trust boundaries.",
      line2: "Governance remains in watch mode until drift conditions emerge.",
      tone: "border-zinc-200 bg-zinc-50 text-zinc-700",
    };
  }, [currentCycle, currentNewlyRestored, currentNewlySuppressed, cycles]);

  return (
    <section className="space-y-8">
      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardContent className="flex items-center justify-between py-5">
          <div className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-400">
            <Waves className="size-4 text-amber-500" />
            <span>{narrative}</span>
          </div>
          <div className="text-sm text-zinc-500">
            Cycle {currentCycle?.cycle_index ?? 0} / {cycles.length}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardContent className="py-5">
          <div className={`rounded-lg border p-4 ${executiveCallout.tone}`}>
            <div className="flex items-start gap-3">
              <executiveCallout.Icon className="size-5 mt-0.5" />
              <div>
                <p className="text-sm font-semibold">{executiveCallout.title}</p>
                <p className="text-sm mt-1">{executiveCallout.line1}</p>
                <p className="text-sm">{executiveCallout.line2}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base">Governance Outcome Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
          {hasTriggeredGovernance ? (
            <>
              <p>
                {impact.totalSuppressionEvents} agents suppressed during drift window
                {typeof firstDriftCycle === "number" && typeof lastDriftCycle === "number"
                  ? ` (cycles ${firstDriftCycle}\u2013${lastDriftCycle}).`
                  : "."}
              </p>
              <p>Containment achieved in {impact.avgTimeToContainment.toFixed(1)} cycles.</p>
              <p>
                Threshold mutation reduced projected fraud amplification by{" "}
                {thresholdShiftReductionPct.toFixed(1)}%.
              </p>
              <p>Net annual loss avoided: {formatMoney(impact.netSavings)}.</p>
            </>
          ) : (
            <>
              <p>Monitoring for drift escalation.</p>
              <p>No containment required.</p>
            </>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardDescription>Success Rate</CardDescription>
            <CardTitle className="text-2xl">{successRate.toFixed(1)}%</CardTitle>
          </CardHeader>
        </Card>

        <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardDescription>Active Agents</CardDescription>
            <CardTitle className="text-2xl">{Math.max(0, activeAgents)}</CardTitle>
          </CardHeader>
        </Card>

        <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardDescription>Suppressed Agents</CardDescription>
            <CardTitle className="text-2xl">{suppressedAgents}</CardTitle>
          </CardHeader>
        </Card>

        <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardDescription>{hasTriggeredGovernance ? "Net Annual Savings" : "Projected Risk Exposure"}</CardDescription>
            <CardTitle className="text-2xl">
              {hasTriggeredGovernance ? formatMoney(impact.netSavings) : formatMoney(impact.annualRiskExposure)}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle>Trust Trajectory</CardTitle>
          <CardDescription>Trust by agent with drift window, suppression markers, and adaptive thresholds.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="h-[420px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                <XAxis dataKey="cycle" label={{ value: "Cycle", position: "insideBottom", offset: -5 }} />
                <YAxis domain={[0, 1]} label={{ value: "Trust", angle: -90, position: "insideLeft" }} />
                <Tooltip />

                {driftRange && (
                  <>
                    <ReferenceArea
                      x1={driftRange.start}
                      x2={driftRange.end}
                      fill="rgba(239,68,68,0.064)"
                      strokeOpacity={0}
                    />
                    <ReferenceArea
                      x1={driftRange.start}
                      x2={driftRange.end}
                      fill="rgba(239,68,68,0.032)"
                      strokeOpacity={0}
                    />
                  </>
                )}

                {suppressionMarkers.map((cycle) => (
                  <ReferenceDot
                    key={`suppression-${cycle.cycle_index}`}
                    x={cycle.cycle_index}
                    y={0.98}
                    r={8}
                    fill="#dc2626"
                    stroke="#fca5a5"
                    strokeWidth={1}
                  />
                ))}

                {typeof currentCycle?.thresholds.trust_threshold === "number" && (
                  <ReferenceLine
                    y={currentCycle.thresholds.trust_threshold}
                    stroke="#2563eb"
                    strokeDasharray="6 6"
                    strokeWidth={1}
                  />
                )}

                {typeof currentCycle?.thresholds.suppression_threshold === "number" && (
                  <ReferenceLine
                    y={currentCycle.thresholds.suppression_threshold}
                    stroke="#ea580c"
                    strokeDasharray="6 6"
                    strokeWidth={1}
                  />
                )}

                {allAgentIds.map((agentId, index) => (
                  <Line
                    key={agentId}
                    type="monotone"
                    dataKey={agentId}
                    stroke={AGENT_COLORS[index % AGENT_COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <TrustLegend agents={allAgentIds} />
        </CardContent>
      </Card>
    </section>
  );
}

function visibleCycleIndex(
  cycles: Array<{ cycle_index: number; phase: string }>,
  predicate: (cycle: { cycle_index: number; phase: string }) => boolean,
  reverse = false
): number | null {
  const source = reverse ? [...cycles].reverse() : cycles;
  const found = source.find((cycle) => predicate(cycle));
  return found?.cycle_index ?? null;
}
