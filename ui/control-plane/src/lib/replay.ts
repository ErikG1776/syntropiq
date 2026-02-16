import type {
  AgentHistoryPoint,
  AgentRow,
  CycleSummary,
  EventType,
  GovernanceEvent,
  KpiRow,
  ReplayCycle,
  ReplayResult,
  ThresholdPoint,
} from "../types/controlPlane";

const BASE_TS = Date.parse("2026-02-16T18:00:00Z");

export function parseReplayJson(raw: string): ReplayResult {
  const parsed = JSON.parse(raw) as ReplayResult;

  if (!parsed || !parsed.timeline || !Array.isArray(parsed.timeline)) {
    throw new Error("Invalid replay file: missing timeline array");
  }
  if (!parsed.config || typeof parsed.config.num_cycles !== "number") {
    throw new Error("Invalid replay file: missing config.num_cycles");
  }

  parsed.timeline = [...parsed.timeline].sort((a, b) => a.cycle - b.cycle);

  return parsed;
}

export function buildFallbackReplayResult(): ReplayResult {
  const timeline: ReplayCycle[] = [];
  const totalCycles = 50;
  let trust = 0.86;
  let balanced = 0.88;
  let conservative = 0.9;
  let trustThreshold = 0.78;
  let suppressionThreshold = 0.84;

  for (let cycle = 0; cycle < totalCycles; cycle += 1) {
    const phase = cycle < 10 ? "RAMP-UP (mixed loans)" : cycle < 28 ? "STRESS (drift accelerating)" : cycle < 38 ? "RECOVERY (safe loans)" : "STEADY STATE (mixed)";
    const suppressGrowth = cycle >= 28 && cycle < 38;

    if (cycle >= 12 && cycle < 28) {
      trust = Math.max(0.58, trust - 0.016);
    } else if (cycle >= 38) {
      trust = Math.min(0.78, trust + 0.015);
    } else if (cycle >= 28) {
      trust = Math.min(0.66, trust + 0.004);
    }

    balanced = Math.max(0.8, Math.min(1, balanced + (cycle % 6 === 0 ? -0.01 : 0.005)));
    conservative = Math.max(0.86, Math.min(1, conservative + (cycle % 8 === 0 ? -0.005 : 0.004)));

    if (cycle % 7 === 0) {
      trustThreshold = Math.max(0.55, trustThreshold - 0.012);
      suppressionThreshold = Math.max(0.72, suppressionThreshold - 0.01);
    }
    if (cycle === 18 || cycle === 23 || cycle === 29) {
      trustThreshold = Math.min(0.79, trustThreshold + 0.03);
      suppressionThreshold = Math.min(0.86, suppressionThreshold + 0.025);
    }

    const failures = suppressGrowth ? 0 : cycle >= 12 && cycle < 28 ? 2 : 0;
    const badApprovals = suppressGrowth ? 0 : cycle >= 12 && cycle < 28 ? 1 : 0;
    const driftLoss = suppressGrowth ? 0 : cycle >= 12 && cycle < 28 ? 12000 + (cycle * 220) : 0;

    timeline.push({
      cycle,
      phase,
      status: "executed",
      trust_scores: {
        conservative: Number(conservative.toFixed(3)),
        balanced: Number(balanced.toFixed(3)),
        growth: Number(trust.toFixed(3)),
      },
      trust_threshold: Number(trustThreshold.toFixed(3)),
      suppression_threshold: Number(suppressionThreshold.toFixed(3)),
      drift_tolerance: Number((0.42 + cycle * 0.012).toFixed(3)),
      suppressed_agents: suppressGrowth ? ["growth"] : [],
      probation_agents: suppressGrowth ? ["growth"] : [],
      successes: 15 - failures,
      failures,
      bad_approvals: badApprovals,
      potential_loss: driftLoss,
      drift_agent_loss: driftLoss,
      drift_agent_bad: badApprovals,
    });
  }

  return {
    demo: "syntropiq_lending_governance",
    config: {
      num_cycles: 50,
      batch_size: 15,
      routing_mode: "competitive",
      data_source: "Lending Club (demo fallback)",
      drift_agent: "growth",
    },
    final_state: {
      trust_scores: timeline[timeline.length - 1].trust_scores,
      trust_threshold: timeline[timeline.length - 1].trust_threshold ?? 0.62,
      suppression_threshold: timeline[timeline.length - 1].suppression_threshold ?? 0.75,
      drift_tolerance_final: timeline[timeline.length - 1].drift_tolerance,
    },
    timeline,
  };
}

export function timelineSuppressionCycle(timeline: ReplayCycle[]): number | null {
  const item = timeline.find((entry) => (entry.suppressed_agents ?? []).length > 0);
  return item ? item.cycle : null;
}

export function thresholdSeriesFromTimeline(timeline: ReplayCycle[]): ThresholdPoint[] {
  return timeline.map((entry, index) => ({
    cycle: `CYCLE_${String(index + 1).padStart(3, "0")}`,
    cycleNumber: entry.cycle + 1,
    trust: entry.trust_threshold ?? 0.7,
    suppression: entry.suppression_threshold ?? 0.75,
    drift: entry.drift_tolerance ?? 0.1,
  }));
}

export function cycleSummariesFromTimeline(timeline: ReplayCycle[]): CycleSummary[] {
  return timeline.map((entry) => ({
    cycle: entry.cycle + 1,
    phase: entry.phase,
    status: entry.status,
    successes: entry.successes ?? 0,
    failures: entry.failures ?? 0,
    badApprovals: entry.bad_approvals ?? 0,
    potentialLoss: entry.potential_loss ?? 0,
    suppressedAgents: entry.suppressed_agents ?? [],
  }));
}

export function agentHistoryFromTimeline(timeline: ReplayCycle[]): AgentHistoryPoint[] {
  return timeline.map((entry) => ({
    cycle: entry.cycle + 1,
    ...entry.trust_scores,
  }));
}

function eventTimestamp(cycle: number, offsetMs = 0): string {
  return new Date(BASE_TS + cycle * 60_000 + offsetMs).toISOString();
}

function buildCycleEvents(cycle: ReplayCycle, previous: ReplayCycle | null): GovernanceEvent[] {
  const events: GovernanceEvent[] = [];
  const currentSuppressed = new Set(cycle.suppressed_agents ?? []);
  const previousSuppressed = new Set(previous?.suppressed_agents ?? []);

  for (const agent of currentSuppressed) {
    if (!previousSuppressed.has(agent)) {
      events.push({
        timestamp: eventTimestamp(cycle.cycle, 1000),
        cycle: cycle.cycle + 1,
        type: "SUPPRESSED",
        agent,
        message: `${agent} suppressed. Execution blocked by governance policy.`,
      });
    }
  }

  for (const agent of previousSuppressed) {
    if (!currentSuppressed.has(agent)) {
      events.push({
        timestamp: eventTimestamp(cycle.cycle, 1200),
        cycle: cycle.cycle + 1,
        type: "REDEEMED",
        agent,
        message: `${agent} redeemed and restored to active routing.`,
      });
    }
  }

  if ((cycle.drift_agent_bad ?? 0) > 0 || (cycle.drift_agent_loss ?? 0) > 0) {
    events.push({
      timestamp: eventTimestamp(cycle.cycle, 1400),
      cycle: cycle.cycle + 1,
      type: "DRIFT DETECTED",
      agent: "growth",
      message: `${cycle.drift_agent_bad ?? 0} drift-induced bad approvals detected`,
    });
  }

  if (cycle.status === "circuit_breaker") {
    events.push({
      timestamp: eventTimestamp(cycle.cycle, 1600),
      cycle: cycle.cycle + 1,
      type: "CIRCUIT BREAKER",
      agent: "governance",
      message: "No trusted agents available. Execution halted.",
    });
  }

  if (previous && cycle.trust_threshold !== undefined && previous.trust_threshold !== undefined) {
    const delta = cycle.trust_threshold - previous.trust_threshold;
    if (Math.abs(delta) >= 0.001) {
      const type: EventType = delta > 0 ? "MUTATION TIGHTEN" : "MUTATION LOOSEN";
      events.push({
        timestamp: eventTimestamp(cycle.cycle, 1800),
        cycle: cycle.cycle + 1,
        type,
        agent: "governance",
        message: `Trust threshold ${delta > 0 ? "tightened" : "loosened"} ${previous.trust_threshold.toFixed(3)} -> ${cycle.trust_threshold.toFixed(3)}`,
      });
    }
  }

  return events;
}

export function eventsFromTimeline(timeline: ReplayCycle[], currentCycle: number): GovernanceEvent[] {
  const bounded = timeline.slice(0, Math.max(1, currentCycle + 1));
  const events = bounded.flatMap((cycle, index) => buildCycleEvents(cycle, index > 0 ? bounded[index - 1] : null));
  return events.sort((a, b) => +new Date(b.timestamp) - +new Date(a.timestamp));
}

export function agentsFromCycle(
  cycle: ReplayCycle,
  previousCycle: ReplayCycle | null,
  driftAgent = "growth",
): AgentRow[] {
  const suppressed = new Set(cycle.suppressed_agents ?? []);

  const agents = Object.entries(cycle.trust_scores).map(([name, trust], index) => {
    const previousTrust = previousCycle?.trust_scores[name] ?? trust;
    const drifting = !suppressed.has(name) && (name === driftAgent || trust < previousTrust - 0.02);
    const status = suppressed.has(name) ? "SUPPRESSED" : drifting ? "DRIFTING" : "ACTIVE";

    return {
      name,
      trust,
      status,
      drifting,
      lastSeen: status === "SUPPRESSED" ? "policy lock" : `${index + 1}s ago`,
      tasks: (cycle.decisions ?? []).filter((d) => d.agent === name).length,
      executionBlocked: status === "SUPPRESSED",
      frozen: status === "SUPPRESSED",
    } as AgentRow;
  });

  return agents.sort((a, b) => b.trust - a.trust);
}

export function cumulativeKpis(timeline: ReplayCycle[], currentCycle: number): KpiRow {
  const bounded = timeline.slice(0, Math.max(1, currentCycle + 1));
  const firstSuppression = timelineSuppressionCycle(timeline);

  let successes = 0;
  let failures = 0;
  let driftLossBefore = 0;
  let driftLossAfter = 0;

  bounded.forEach((entry) => {
    successes += entry.successes ?? 0;
    failures += entry.failures ?? 0;
    const loss = entry.drift_agent_loss ?? 0;

    if (firstSuppression !== null && entry.cycle < firstSuppression) {
      driftLossBefore += loss;
    } else if (firstSuppression !== null) {
      driftLossAfter += loss;
    } else {
      driftLossBefore += loss;
    }
  });

  const cyclesExecuted = bounded.length;
  const rate = successes + failures > 0 ? successes / (successes + failures) : 0;
  const projectedWithoutSuppression = firstSuppression !== null && firstSuppression > 0
    ? (driftLossBefore / firstSuppression) * Math.max(0, cyclesExecuted - firstSuppression)
    : 0;
  const preventedDelta = Math.max(0, projectedWithoutSuppression - driftLossAfter);

  return {
    preventedDelta,
    driftLossBeforeSuppression: driftLossBefore,
    driftLossAfterSuppression: driftLossAfter,
    overallSuccessRate: rate,
    cyclesExecuted,
  };
}
