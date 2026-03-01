// ─── Types ───────────────────────────────────────────────────────────────────

export type DomainId = "fraud" | "lending" | "readmission";

export interface DomainConfig {
  id: DomainId;
  label: string;
  shortLabel: string;
  description: string;
  lossLabel: string;
  lossUnit: string;
  agentNames: string[];
  driftAgent: string;
  icon: string;
  accentColor: string;
}

export interface CycleData {
  cycle: number;
  phase: string;
  status: string;
  trust_scores: Record<string, number>;
  trust_threshold?: number;
  suppression_threshold?: number;
  drift_threshold?: number;
  drift_tolerance?: number;
  suppressed_agents: string[];
  probation_agents?: string[];
  successes: number;
  failures: number;
  // Domain-specific loss metrics
  potential_loss?: number;
  bad_approvals?: number;
  missed_fraud?: number;
  caught_fraud?: number;
  false_positives?: number;
  drift_agent_loss?: number;
  drift_agent_missed?: number;
  drift_agent_bad?: number;
  missed_readmissions?: number;
  caught_readmissions?: number;
  unnecessary_flags?: number;
  penalty_incurred?: number;
  drift_agent_penalty?: number;
}

export interface DemoDataset {
  config: Record<string, unknown>;
  final_state: Record<string, unknown>;
  timeline: CycleData[];
}

export interface GovernanceEvent {
  cycle: number;
  type: "drift_detected" | "agent_suppressed" | "agent_restored" | "threshold_mutated" | "loss_detected" | "system_healthy" | "probation_started";
  severity: "info" | "warning" | "danger" | "success";
  agent?: string;
  message: string;
}

// ─── Domain Configs ──────────────────────────────────────────────────────────

export const DOMAINS: Record<DomainId, DomainConfig> = {
  fraud: {
    id: "fraud",
    label: "Payment Fraud Detection",
    shortLabel: "Fraud",
    description: "Real-time transaction monitoring across 3 AI fraud detection models",
    lossLabel: "Fraud Losses",
    lossUnit: "$",
    agentNames: ["rule_engine", "ml_scorer", "ensemble"],
    driftAgent: "ensemble",
    icon: "ShieldAlert",
    accentColor: "#f43f5e",
  },
  lending: {
    id: "lending",
    label: "Loan Underwriting",
    shortLabel: "Lending",
    description: "Automated loan approval decisions across 3 underwriting AI agents",
    lossLabel: "Default Losses",
    lossUnit: "$",
    agentNames: ["conservative", "balanced", "growth"],
    driftAgent: "growth",
    icon: "Landmark",
    accentColor: "#22d3ee",
  },
  readmission: {
    id: "readmission",
    label: "Hospital Readmission",
    shortLabel: "Healthcare",
    description: "Discharge planning for diabetic patients across 3 clinical AI models",
    lossLabel: "Medicare Penalties",
    lossUnit: "$",
    agentNames: ["conservative", "predictive", "rapid_screen"],
    driftAgent: "rapid_screen",
    icon: "HeartPulse",
    accentColor: "#34d399",
  },
};

// ─── Helper: Extract governance events from cycle transitions ────────────────

export function deriveEvents(timeline: CycleData[], domain: DomainConfig): GovernanceEvent[] {
  const events: GovernanceEvent[] = [];

  for (let i = 0; i < timeline.length; i++) {
    const curr = timeline[i];
    const prev = i > 0 ? timeline[i - 1] : null;

    // Suppression started
    if (prev) {
      const newlySuppressed = curr.suppressed_agents.filter(
        (a) => !prev.suppressed_agents.includes(a)
      );
      for (const agent of newlySuppressed) {
        events.push({
          cycle: curr.cycle,
          type: "agent_suppressed",
          severity: "danger",
          agent,
          message: `${agent} suppressed — trust below threshold`,
        });
      }

      // Agent restored
      const restored = prev.suppressed_agents.filter(
        (a) => !curr.suppressed_agents.includes(a)
      );
      for (const agent of restored) {
        events.push({
          cycle: curr.cycle,
          type: "agent_restored",
          severity: "success",
          agent,
          message: `${agent} restored to active duty`,
        });
      }

      // Drift detected (trust drop > 0.05 for drift agent)
      const driftScore = curr.trust_scores[domain.driftAgent];
      const prevDriftScore = prev.trust_scores[domain.driftAgent];
      if (driftScore && prevDriftScore && prevDriftScore - driftScore > 0.05) {
        events.push({
          cycle: curr.cycle,
          type: "drift_detected",
          severity: "warning",
          agent: domain.driftAgent,
          message: `Drift detected on ${domain.driftAgent} — trust ${prevDriftScore.toFixed(2)} → ${driftScore.toFixed(2)}`,
        });
      }

      // Threshold mutation
      if (
        prev.trust_threshold &&
        curr.trust_threshold &&
        Math.abs(prev.trust_threshold - curr.trust_threshold) > 0.005
      ) {
        const direction = curr.trust_threshold > prev.trust_threshold ? "tightened" : "loosened";
        events.push({
          cycle: curr.cycle,
          type: "threshold_mutated",
          severity: "info",
          message: `Governance ${direction} — τ ${prev.trust_threshold.toFixed(3)} → ${curr.trust_threshold.toFixed(3)}`,
        });
      }
    }

    // Loss detected
    const loss = curr.potential_loss || curr.penalty_incurred || 0;
    if (loss > 0) {
      events.push({
        cycle: curr.cycle,
        type: "loss_detected",
        severity: "danger",
        message: `$${loss.toLocaleString("en-US", { maximumFractionDigits: 0 })} loss in cycle ${curr.cycle}`,
      });
    }
  }

  return events;
}

// ─── Helper: Calculate cumulative stats up to a cycle ────────────────────────

export interface CumulativeStats {
  totalCycles: number;
  totalSuccesses: number;
  totalFailures: number;
  successRate: number;
  totalLoss: number;
  totalLossWithout: number;
  lossePrevented: number;
  suppressionCycles: number;
  activeAgents: number;
  totalAgents: number;
  currentPhase: string;
}

export function getCumulativeStats(
  timeline: CycleData[],
  upToCycle: number,
  domain: DomainConfig
): CumulativeStats {
  const cycles = timeline.filter((c) => c.cycle <= upToCycle && c.status !== "circuit_breaker");
  const current = timeline.find((c) => c.cycle === upToCycle);

  let totalSuccesses = 0;
  let totalFailures = 0;
  let totalLoss = 0;
  let suppressionCycles = 0;

  // Track pre-suppression loss rate for "without governance" projection
  let preSuppLossSum = 0;
  let preSuppCycles = 0;
  let firstSuppressionCycle = -1;

  for (const c of cycles) {
    totalSuccesses += c.successes;
    totalFailures += c.failures;
    totalLoss += c.potential_loss || c.penalty_incurred || 0;

    if (c.suppressed_agents.length > 0) {
      suppressionCycles++;
      if (firstSuppressionCycle === -1) firstSuppressionCycle = c.cycle;
    }

    // Accumulate pre-suppression losses from drift agent
    if (firstSuppressionCycle === -1) {
      const agentLoss = c.drift_agent_loss || c.drift_agent_penalty || 0;
      if (agentLoss > 0) {
        preSuppLossSum += agentLoss;
        preSuppCycles++;
      }
    }
  }

  // Project what losses would have been without governance
  const avgPreSuppLoss = preSuppCycles > 0 ? preSuppLossSum / preSuppCycles : 0;
  const cyclesAfterFirstSupp = firstSuppressionCycle >= 0
    ? cycles.filter((c) => c.cycle >= firstSuppressionCycle).length
    : 0;
  const totalLossWithout = totalLoss + avgPreSuppLoss * cyclesAfterFirstSupp * 1.5;

  const total = totalSuccesses + totalFailures;

  return {
    totalCycles: cycles.length,
    totalSuccesses,
    totalFailures,
    successRate: total > 0 ? totalSuccesses / total : 1,
    totalLoss,
    totalLossWithout,
    lossePrevented: Math.max(0, totalLossWithout - totalLoss),
    suppressionCycles,
    activeAgents: current
      ? domain.agentNames.length - (current.suppressed_agents?.length || 0)
      : domain.agentNames.length,
    totalAgents: domain.agentNames.length,
    currentPhase: current?.phase || "Initializing",
  };
}

// ─── Agent display helpers ───────────────────────────────────────────────────

export function getAgentDisplayName(agent: string): string {
  return agent
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function getAgentStatus(
  agent: string,
  cycle: CycleData
): "active" | "suppressed" | "probation" | "drifting" {
  if (cycle.suppressed_agents?.includes(agent)) return "suppressed";
  if (cycle.probation_agents?.includes(agent)) return "probation";
  return "active";
}
