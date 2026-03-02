export type NarrativeEventType =
  | "drift_detected"
  | "suppression"
  | "recovery"
  | "threshold_adaptation"
  | "circuit_breaker";

export interface DemoCycle {
  cycle_index: number;
  window_start: string;
  phase: string;
  circuit_breaker: boolean;
  selected_agents: string[];
  trust: Record<string, number>;
  suppressed_agents: string[];
  thresholds: {
    trust_threshold?: number;
    suppression_threshold?: number;
    drift_delta?: number;
  };
  Fs?: number;
  classification?: string;
  failures?: number;
}

export interface DemoRunResult {
  run_id: string;
  window_minutes: number;
  txn_count_per_cycle: number;
  cycles: DemoCycle[];
  final: {
    r_score: number;
    chains: Record<string, boolean>;
    suppression_deadlock: boolean;
    certified: boolean;
  };
}

export interface NarrativeEvent {
  id: string;
  cycle: number;
  type: NarrativeEventType;
  title: string;
  detail: string;
}

export interface ImpactSummary {
  annualVolume: number;
  estimatedLossWithout: number;
  estimatedLossWith: number;
  savings: number;
  reductionPct: number;
  suppressionWindows: number;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseCycle(value: unknown): DemoCycle | null {
  if (!isObject(value)) return null;
  const cycle_index = typeof value.cycle_index === "number" ? value.cycle_index : null;
  const window_start = typeof value.window_start === "string" ? value.window_start : null;
  const phase = typeof value.phase === "string" ? value.phase : "unknown";
  const circuit_breaker = value.circuit_breaker === true;
  const selected_agents = Array.isArray(value.selected_agents)
    ? value.selected_agents.filter((v): v is string => typeof v === "string")
    : [];
  const suppressed_agents = Array.isArray(value.suppressed_agents)
    ? value.suppressed_agents.filter((v): v is string => typeof v === "string")
    : [];

  const trustRaw = isObject(value.trust) ? value.trust : {};
  const trust: Record<string, number> = {};
  for (const [k, v] of Object.entries(trustRaw)) {
    if (typeof v === "number") trust[k] = v;
  }

  const thresholdsRaw = isObject(value.thresholds) ? value.thresholds : {};
  const thresholds = {
    trust_threshold:
      typeof thresholdsRaw.trust_threshold === "number"
        ? thresholdsRaw.trust_threshold
        : undefined,
    suppression_threshold:
      typeof thresholdsRaw.suppression_threshold === "number"
        ? thresholdsRaw.suppression_threshold
        : undefined,
    drift_delta:
      typeof thresholdsRaw.drift_delta === "number" ? thresholdsRaw.drift_delta : undefined,
  };

  if (cycle_index === null || window_start === null) return null;

  return {
    cycle_index,
    window_start,
    phase,
    circuit_breaker,
    selected_agents,
    trust,
    suppressed_agents,
    thresholds,
    Fs: typeof value.Fs === "number" ? value.Fs : undefined,
    classification: typeof value.classification === "string" ? value.classification : undefined,
    failures: typeof value.failures === "number" ? value.failures : undefined,
  };
}

export function parseDemoRunResult(input: unknown): DemoRunResult {
  if (!isObject(input)) {
    throw new Error("Invalid demo JSON payload");
  }

  const run_id = typeof input.run_id === "string" ? input.run_id : "UNKNOWN_RUN";
  const window_minutes = typeof input.window_minutes === "number" ? input.window_minutes : 5;
  const txn_count_per_cycle =
    typeof input.txn_count_per_cycle === "number" ? input.txn_count_per_cycle : 1000;

  const rawCycles = Array.isArray(input.cycles) ? input.cycles : [];
  const cycles = rawCycles
    .map(parseCycle)
    .filter((v): v is DemoCycle => v !== null)
    .sort((a, b) => a.cycle_index - b.cycle_index);

  const finalRaw = isObject(input.final) ? input.final : {};
  const chainsRaw = isObject(finalRaw.chains) ? finalRaw.chains : {};
  const chains: Record<string, boolean> = {};
  for (const [k, v] of Object.entries(chainsRaw)) {
    chains[k] = Boolean(v);
  }

  return {
    run_id,
    window_minutes,
    txn_count_per_cycle,
    cycles,
    final: {
      r_score: typeof finalRaw.r_score === "number" ? finalRaw.r_score : 0,
      chains,
      suppression_deadlock: finalRaw.suppression_deadlock === true,
      certified: finalRaw.certified === true,
    },
  };
}

export async function loadDemoRunResult(): Promise<DemoRunResult> {
  const res = await fetch(`/demo_results.json?ts=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load demo_results.json (${res.status})`);
  }
  const payload = (await res.json()) as unknown;
  return parseDemoRunResult(payload);
}

export function getAgentIds(cycles: DemoCycle[]): string[] {
  const ids = new Set<string>();
  for (const cycle of cycles) {
    for (const agent of Object.keys(cycle.trust || {})) ids.add(agent);
  }
  return Array.from(ids).sort();
}

export function deriveNarrativeEvents(cycles: DemoCycle[]): NarrativeEvent[] {
  const events: NarrativeEvent[] = [];

  for (let i = 0; i < cycles.length; i++) {
    const current = cycles[i];
    const prev = i > 0 ? cycles[i - 1] : null;

    if (current.phase === "drift" && (!prev || prev.phase !== "drift")) {
      events.push({
        id: `drift-${current.cycle_index}`,
        cycle: current.cycle_index,
        type: "drift_detected",
        title: "Drift detected",
        detail: `Elevated risk regime began in cycle ${current.cycle_index}.`,
      });
    }

    if (current.circuit_breaker) {
      events.push({
        id: `cb-${current.cycle_index}`,
        cycle: current.cycle_index,
        type: "circuit_breaker",
        title: "Circuit breaker",
        detail: `Protection mode activated in cycle ${current.cycle_index}.`,
      });
    }

    const newlySuppressed = prev
      ? current.suppressed_agents.filter((id) => !prev.suppressed_agents.includes(id))
      : current.suppressed_agents;

    if (newlySuppressed.length > 0) {
      events.push({
        id: `sup-${current.cycle_index}`,
        cycle: current.cycle_index,
        type: "suppression",
        title: "Suppression",
        detail: `${newlySuppressed.join(", ")} suppressed to contain risk.`,
      });
    }

    if (prev) {
      const restored = prev.suppressed_agents.filter(
        (id) => !current.suppressed_agents.includes(id)
      );
      if (restored.length > 0) {
        events.push({
          id: `rec-${current.cycle_index}`,
          cycle: current.cycle_index,
          type: "recovery",
          title: "Recovery",
          detail: `${restored.join(", ")} restored after stabilization.`,
        });
      }

      const trustBefore = prev.thresholds.trust_threshold;
      const trustAfter = current.thresholds.trust_threshold;
      const suppBefore = prev.thresholds.suppression_threshold;
      const suppAfter = current.thresholds.suppression_threshold;
      const changed =
        typeof trustBefore === "number" &&
        typeof trustAfter === "number" &&
        typeof suppBefore === "number" &&
        typeof suppAfter === "number" &&
        (Math.abs(trustAfter - trustBefore) > 0.0001 ||
          Math.abs(suppAfter - suppBefore) > 0.0001);

      if (changed) {
        events.push({
          id: `th-${current.cycle_index}`,
          cycle: current.cycle_index,
          type: "threshold_adaptation",
          title: "Threshold adaptation",
          detail: `τ ${trustBefore?.toFixed(2)}→${trustAfter?.toFixed(
            2
          )}, τ_s ${suppBefore?.toFixed(2)}→${suppAfter?.toFixed(2)}.`,
        });
      }
    }
  }

  return events.sort((a, b) => a.cycle - b.cycle);
}

export function findDriftWindow(cycles: DemoCycle[]): { start?: number; end?: number } {
  const driftCycles = cycles.filter((c) => c.phase === "drift").map((c) => c.cycle_index);
  if (driftCycles.length === 0) return {};
  return { start: Math.min(...driftCycles), end: Math.max(...driftCycles) };
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function computeEnterpriseImpact(
  run: DemoRunResult,
  annualVolume: number
): ImpactSummary {
  const cycles = run.cycles;
  const suppressionWindows = cycles.filter((c) => c.suppressed_agents.length > 0).length;
  const breakerWindows = cycles.filter((c) => c.circuit_breaker).length;
  const explicitFailures = cycles.reduce((sum, c) => sum + (c.failures ?? 0), 0);

  const proxyFailures =
    explicitFailures > 0
      ? explicitFailures
      : suppressionWindows + breakerWindows * 2 + Math.round(cycles.length * 0.05);

  const windowIncidentRate = cycles.length > 0 ? proxyFailures / cycles.length : 0;
  const annualWindows = run.window_minutes > 0 ? (365 * 24 * 60) / run.window_minutes : 0;
  const annualIncidents = windowIncidentRate * annualWindows;

  // Incident severity scales with transaction volume, kept deterministic from run telemetry.
  const avgLossPerIncident = annualVolume * 0.0000018;
  const estimatedLossWithout = annualIncidents * avgLossPerIncident;

  const events = deriveNarrativeEvents(cycles);
  const restorations = events.filter((e) => e.type === "recovery").length;
  const mitigation = clamp(
    0.25 + restorations * 0.08 + (run.final.certified ? 0.18 : 0) + suppressionWindows * 0.01,
    0.15,
    0.85
  );

  const estimatedLossWith = estimatedLossWithout * (1 - mitigation);
  const savings = Math.max(0, estimatedLossWithout - estimatedLossWith);
  const reductionPct = estimatedLossWithout > 0 ? (savings / estimatedLossWithout) * 100 : 0;

  return {
    annualVolume,
    estimatedLossWithout,
    estimatedLossWith,
    savings,
    reductionPct,
    suppressionWindows,
  };
}

// Legacy compatibility exports for existing dashboard components.
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
  potential_loss?: number;
  penalty_incurred?: number;
  drift_agent_loss?: number;
  drift_agent_penalty?: number;
  [key: string]: unknown;
}

export interface DemoDataset {
  config: Record<string, unknown>;
  final_state: Record<string, unknown>;
  timeline: CycleData[];
}

export interface GovernanceEvent {
  cycle: number;
  type:
    | "drift_detected"
    | "agent_suppressed"
    | "agent_restored"
    | "threshold_mutated"
    | "loss_detected"
    | "system_healthy"
    | "probation_started";
  severity: "info" | "warning" | "danger" | "success";
  agent?: string;
  message: string;
}

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

export function deriveEvents(timeline: CycleData[], domain: DomainConfig): GovernanceEvent[] {
  const events: GovernanceEvent[] = [];

  for (let i = 0; i < timeline.length; i++) {
    const curr = timeline[i];
    const prev = i > 0 ? timeline[i - 1] : null;

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

      const driftScore = curr.trust_scores[domain.driftAgent];
      const prevDriftScore = prev.trust_scores[domain.driftAgent];
      if (
        typeof driftScore === "number" &&
        typeof prevDriftScore === "number" &&
        prevDriftScore - driftScore > 0.05
      ) {
        events.push({
          cycle: curr.cycle,
          type: "drift_detected",
          severity: "warning",
          agent: domain.driftAgent,
          message: `Drift detected on ${domain.driftAgent}`,
        });
      }

      const trustBefore = prev.trust_threshold;
      const trustAfter = curr.trust_threshold;
      if (
        typeof trustBefore === "number" &&
        typeof trustAfter === "number" &&
        Math.abs(trustBefore - trustAfter) > 0.005
      ) {
        events.push({
          cycle: curr.cycle,
          type: "threshold_mutated",
          severity: "info",
          message: `Governance adapted τ ${trustBefore.toFixed(3)} → ${trustAfter.toFixed(3)}`,
        });
      }
    }

    const loss = curr.potential_loss || curr.penalty_incurred || 0;
    if (loss > 0) {
      events.push({
        cycle: curr.cycle,
        type: "loss_detected",
        severity: "danger",
        message: `$${Math.round(loss).toLocaleString()} loss in cycle ${curr.cycle}`,
      });
    }
  }

  return events;
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

  for (const c of cycles) {
    totalSuccesses += c.successes || 0;
    totalFailures += c.failures || 0;
    totalLoss += c.potential_loss || c.penalty_incurred || 0;
    if ((c.suppressed_agents || []).length > 0) suppressionCycles++;
  }

  const total = totalSuccesses + totalFailures;
  const projectedWithout = totalLoss * (1 + suppressionCycles * 0.12);

  return {
    totalCycles: cycles.length,
    totalSuccesses,
    totalFailures,
    successRate: total > 0 ? totalSuccesses / total : 1,
    totalLoss,
    totalLossWithout: projectedWithout,
    lossePrevented: Math.max(0, projectedWithout - totalLoss),
    suppressionCycles,
    activeAgents: current
      ? domain.agentNames.length - (current.suppressed_agents?.length || 0)
      : domain.agentNames.length,
    totalAgents: domain.agentNames.length,
    currentPhase: current?.phase || "Initializing",
  };
}

export function getAgentDisplayName(agent: string): string {
  return agent.replace(/_/g, " ");
}

export function getAgentStatus(
  agent: string,
  cycle: CycleData
): "active" | "suppressed" | "probation" | "drifting" {
  if (cycle.suppressed_agents?.includes(agent)) return "suppressed";
  if (cycle.probation_agents?.includes(agent)) return "probation";
  return "active";
}
