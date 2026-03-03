export type RunCycle = {
  cycle_index: number;
  window_start: string;
  phase: string;
  circuit_breaker: boolean;
  selected_agents: string[];
  trust: Record<string, number>;
  suppressed_agents: string[];
  suppressed_before?: string[];
  suppressed_after?: string[];
  newly_suppressed?: string[];
  newly_restored?: string[];
  thresholds: {
    trust_threshold?: number;
    suppression_threshold?: number;
    drift_delta?: number;
  };
};

export type DemoRun = {
  run_id: string;
  window_minutes: number;
  txn_count_per_cycle: number;
  cycles: RunCycle[];
  final: {
    certified: boolean;
    r_score?: number;
    suppression_deadlock?: boolean;
    chains?: Record<string, boolean>;
  };
};

export type GovernanceEventType =
  | "drift"
  | "suppression"
  | "recovery"
  | "threshold"
  | "circuit"
  | "stabilized";

export type GovernanceEvent = {
  id: string;
  cycle: number;
  type: GovernanceEventType;
  message: string;
  agent?: string;
};

export type PlaySpeed = 1 | 2 | 3;

export type ImpactModel = {
  annualFraudEvents: number;
  fraudEventsAvoided: number;
  annualRiskExposure: number;
  driftAmplification: number;
  governanceReduction: number;
  withoutGovernance: number;
  withSyntropiq: number;
  netSavings: number;
  reductionPct: number;
  totalSuppressionEvents: number;
  avgTimeToContainment: number;
  avgSuppressionDuration: number;
  driftWindowLength: number;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function safeArray(input?: string[]): string[] {
  return Array.isArray(input) ? input : [];
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function getSuppressedAfter(cycle: RunCycle | null): string[] {
  if (!cycle) return [];
  const after = safeArray(cycle.suppressed_after);
  if (after.length > 0) return after;
  return safeArray(cycle.suppressed_agents);
}

export function getSuppressedBefore(cycle: RunCycle, prev: RunCycle | null): string[] {
  const before = safeArray(cycle.suppressed_before);
  if (before.length > 0) return before;
  return prev ? getSuppressedAfter(prev) : [];
}

export function getNewlySuppressed(cycle: RunCycle, prev: RunCycle | null): string[] {
  const existing = safeArray(cycle.newly_suppressed);
  if (existing.length > 0) return existing;
  const before = new Set(getSuppressedBefore(cycle, prev));
  return getSuppressedAfter(cycle).filter((id) => !before.has(id));
}

export function getNewlyRestored(cycle: RunCycle, prev: RunCycle | null): string[] {
  const existing = safeArray(cycle.newly_restored);
  if (existing.length > 0) return existing;
  const after = new Set(getSuppressedAfter(cycle));
  return getSuppressedBefore(cycle, prev).filter((id) => !after.has(id));
}

export function deriveEvents(cycles: RunCycle[]): GovernanceEvent[] {
  const events: GovernanceEvent[] = [];

  for (let i = 0; i < cycles.length; i++) {
    const cycle = cycles[i];
    const prev = i > 0 ? cycles[i - 1] : null;

    if (cycle.phase === "drift" && (!prev || prev.phase !== "drift")) {
      const droppingAgent = Object.entries(cycle.trust).sort((a, b) => a[1] - b[1])[0]?.[0];
      events.push({
        id: `drift-${cycle.cycle_index}`,
        cycle: cycle.cycle_index,
        type: "drift",
        agent: droppingAgent,
        message: `Drift detected${droppingAgent ? ` on ${droppingAgent}` : ""}.`,
      });
    }

    for (const agent of getNewlySuppressed(cycle, prev)) {
      events.push({
        id: `suppression-${cycle.cycle_index}-${agent}`,
        cycle: cycle.cycle_index,
        type: "suppression",
        agent,
        message: `${agent} suppressed due to trust breach.`,
      });
    }

    for (const agent of getNewlyRestored(cycle, prev)) {
      events.push({
        id: `recovery-${cycle.cycle_index}-${agent}`,
        cycle: cycle.cycle_index,
        type: "recovery",
        agent,
        message: `${agent} moved into probation and recovery.`,
      });
    }

    if (prev) {
      const prevTrust = prev?.thresholds?.trust_threshold;
      const currTrust = cycle?.thresholds?.trust_threshold;
      const prevSupp = prev?.thresholds?.suppression_threshold;
      const currSupp = cycle?.thresholds?.suppression_threshold;

      if (
        typeof prevTrust === "number" &&
        typeof currTrust === "number" &&
        typeof prevSupp === "number" &&
        typeof currSupp === "number"
      ) {
        if (Math.abs(prevTrust - currTrust) > 0.0001 || Math.abs(prevSupp - currSupp) > 0.0001) {
          const verb = currTrust > prevTrust ? "tightened" : "loosened";
          events.push({
            id: `threshold-${cycle.cycle_index}`,
            cycle: cycle.cycle_index,
            type: "threshold",
            message: `Thresholds ${verb}: trust ${prevTrust.toFixed(2)}->${currTrust.toFixed(2)}, suppression ${prevSupp.toFixed(2)}->${currSupp.toFixed(2)}.`,
          });
        }
      }
    }

    if (cycle.circuit_breaker) {
      events.push({
        id: `circuit-${cycle.cycle_index}`,
        cycle: cycle.cycle_index,
        type: "circuit",
        message: "Circuit breaker triggered. Governance fail-safe engaged.",
      });
    }
  }

  const last = cycles[cycles.length - 1];
  if (last && getSuppressedAfter(last).length === 0) {
    events.push({
      id: `stable-${last.cycle_index}`,
      cycle: last.cycle_index,
      type: "stabilized",
      message: "System stabilized and certified.",
    });
  }

  return events.sort((a, b) => a.cycle - b.cycle);
}

export function getNarrative(cycle: RunCycle | undefined, newlySuppressed: string[], newlyRestored: string[]): string {
  if (!cycle) return "System online. Awaiting cycle playback.";
  if (newlySuppressed.length > 0) return `Agent ${newlySuppressed[0]} suppressed to contain risk.`;
  if (newlyRestored.length > 0) return `Agent ${newlyRestored[0]} entering recovery.`;
  if (cycle.phase === "baseline") return "System stable. Monitoring agents.";
  if (cycle.phase === "drift") return "Drift detected. Monitoring degradation.";
  if (cycle.phase === "stabilized") return "System stabilized. Governance certified.";
  return "System stable. Monitoring agents.";
}

export function getEventBadgeClasses(type: GovernanceEventType): string {
  if (type === "suppression" || type === "circuit") {
    return "bg-red-100 text-red-700 border-red-200";
  }
  if (type === "drift") {
    return "bg-amber-100 text-amber-700 border-amber-200";
  }
  if (type === "threshold") {
    return "bg-blue-100 text-blue-700 border-blue-200";
  }
  if (type === "recovery" || type === "stabilized") {
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }
  return "bg-zinc-100 text-zinc-700 border-zinc-200";
}

export function playbackIntervalMs(speed: PlaySpeed): number {
  if (speed === 3) return 450;
  if (speed === 2) return 900;
  return 1400;
}

export function computeImpact(
  cycles: RunCycle[],
  annualTransactions: number,
  fraudRate: number,
  lossPerFraud: number
): ImpactModel {
  const driftCycleIndices = cycles
    .filter((cycle) => cycle.phase === "drift")
    .map((cycle) => cycle.cycle_index);
  const firstDriftCycleIndex =
    driftCycleIndices.length > 0 ? Math.min(...driftCycleIndices) : null;

  const suppressionEventCycles: number[] = [];
  const suppressionEvents = cycles.reduce((count, cycle, index) => {
    const newlySuppressed = getNewlySuppressed(cycle, index > 0 ? cycles[index - 1] : null);
    if (newlySuppressed.length > 0) {
      suppressionEventCycles.push(cycle.cycle_index);
    }
    return count + newlySuppressed.length;
  }, 0);

  const restorationEvents = cycles.reduce((count, cycle, index) => {
    return count + getNewlyRestored(cycle, index > 0 ? cycles[index - 1] : null).length;
  }, 0);

  const driftCycles = driftCycleIndices.length;
  const circuitEvents = cycles.filter((cycle) => cycle.circuit_breaker).length;

  const cycleCount = Math.max(cycles.length, 1);
  const suppressionRate = suppressionEvents / cycleCount;
  const restorationRate = restorationEvents / cycleCount;
  const driftRate = driftCycles / cycleCount;
  const circuitRate = circuitEvents / cycleCount;

  const annualFraudEvents = annualTransactions * fraudRate;
  const annualRiskExposure = annualFraudEvents * lossPerFraud;
  const firstSuppressionCycleIndex =
    suppressionEventCycles.length > 0 ? Math.min(...suppressionEventCycles) : null;

  const avgTimeToContainment =
    typeof firstDriftCycleIndex === "number" && typeof firstSuppressionCycleIndex === "number"
      ? Math.max(0, firstSuppressionCycleIndex - firstDriftCycleIndex)
      : 0;

  const perAgentStart = new Map<string, number>();
  const suppressionDurations: number[] = [];
  for (let i = 0; i < cycles.length; i++) {
    const cycle = cycles[i];
    const prev = i > 0 ? cycles[i - 1] : null;
    for (const agent of getNewlySuppressed(cycle, prev)) {
      perAgentStart.set(agent, cycle.cycle_index);
    }
    for (const agent of getNewlyRestored(cycle, prev)) {
      const start = perAgentStart.get(agent);
      if (typeof start === "number") {
        suppressionDurations.push(Math.max(0, cycle.cycle_index - start));
        perAgentStart.delete(agent);
      }
    }
  }

  const lastCycleIndex = cycles[cycles.length - 1]?.cycle_index ?? 0;
  for (const start of perAgentStart.values()) {
    suppressionDurations.push(Math.max(0, lastCycleIndex - start + 1));
  }

  const avgSuppressionDuration =
    suppressionDurations.length > 0
      ? suppressionDurations.reduce((sum, value) => sum + value, 0) / suppressionDurations.length
      : 0;

  const driftWindowLength =
    driftCycleIndices.length > 0 ? Math.max(...driftCycleIndices) - Math.min(...driftCycleIndices) + 1 : 0;

  const driftAmplification = clamp(
    0.08 + driftRate * 0.18 + suppressionRate * 0.6 + circuitRate * 0.25,
    0.08,
    0.4
  );

  const governanceReduction = clamp(
    0.32 + suppressionRate * 0.6 + restorationRate * 0.25 - circuitRate * 0.25,
    0.2,
    0.65
  );

  const withoutGovernance = annualRiskExposure * (1 + driftAmplification);
  const withSyntropiq = annualRiskExposure * (1 - governanceReduction);
  const fraudEventsAvoided = annualFraudEvents * governanceReduction;
  const netSavings = withoutGovernance - withSyntropiq;
  const reductionPct = withoutGovernance > 0 ? (netSavings / withoutGovernance) * 100 : 0;

  return {
    annualFraudEvents,
    fraudEventsAvoided,
    annualRiskExposure,
    driftAmplification,
    governanceReduction,
    withoutGovernance,
    withSyntropiq,
    netSavings,
    reductionPct,
    totalSuppressionEvents: suppressionEvents,
    avgTimeToContainment,
    avgSuppressionDuration,
    driftWindowLength,
  };
}
