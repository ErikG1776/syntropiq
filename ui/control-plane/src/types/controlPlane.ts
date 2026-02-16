export type Environment = "DEMO" | "STAGING" | "PROD";
export type Mode = "LIVE" | "REPLAY";

export type AgentStatus = "ACTIVE" | "DRIFTING" | "SUPPRESSED";

export type EventType =
  | "DRIFT DETECTED"
  | "SUPPRESSED"
  | "REDEEMED"
  | "MUTATION TIGHTEN"
  | "MUTATION LOOSEN"
  | "CIRCUIT BREAKER";

export interface StatisticsResponse {
  total_executions: number;
  success_rate: number;
  suppressed_agents: number;
  valid_reflections: number;
  total_agents: number;
  active_agents: number;
  avg_trust_score: number;
  mutation_performance: {
    avg_success_rate: number;
    trend: string;
    cycles_tracked: number;
  };
}

export interface AgentApi {
  agent_id: string;
  trust_score: number;
  capabilities: string[];
  status: string;
}

export interface MutationHistoryItem {
  cycle_id: string;
  success_rate: number;
  action: string;
  trust_threshold: { old: number; new: number };
  suppression_threshold: { old: number; new: number };
  drift_delta: { old: number; new: number };
  timestamp: string;
}

export interface ReflectionItem {
  reflection_text: string;
  constraint_score: number;
  timestamp: string;
}

export interface ReplayDecision {
  loan_id: string;
  agent: string;
  decision: string;
  outcome: string;
  amount: number;
  grade: string;
  success: boolean;
}

export interface ReplayCycle {
  cycle: number;
  phase: string;
  status: "executed" | "circuit_breaker";
  trust_scores: Record<string, number>;
  trust_threshold?: number;
  suppression_threshold?: number;
  drift_tolerance?: number;
  suppressed_agents?: string[];
  probation_agents?: string[];
  successes?: number;
  failures?: number;
  bad_approvals?: number;
  potential_loss?: number;
  drift_agent_loss?: number;
  drift_agent_bad?: number;
  decisions?: ReplayDecision[];
}

export interface ReplayResult {
  demo: string;
  config: {
    num_cycles: number;
    batch_size: number;
    routing_mode: "competitive" | "deterministic";
    data_source: string;
    drift_agent?: string;
  };
  final_state: {
    trust_scores: Record<string, number>;
    trust_threshold: number;
    suppression_threshold: number;
    drift_tolerance_final?: number;
  };
  timeline: ReplayCycle[];
}

export interface AgentRow {
  name: string;
  trust: number;
  status: AgentStatus;
  drifting: boolean;
  lastSeen: string;
  tasks: number;
  executionBlocked: boolean;
  frozen: boolean;
}

export interface GovernanceEvent {
  timestamp: string;
  cycle: number;
  type: EventType;
  agent: string;
  message: string;
}

export interface KpiRow {
  preventedDelta: number;
  driftLossBeforeSuppression: number;
  driftLossAfterSuppression: number;
  overallSuccessRate: number;
  cyclesExecuted: number;
}

export interface ThresholdPoint {
  cycle: string;
  cycleNumber: number;
  trust: number;
  suppression: number;
  drift: number;
}

export interface AgentHistoryPoint {
  cycle: number;
  [agentId: string]: number;
}

export interface CycleSummary {
  cycle: number;
  phase: string;
  status: string;
  successes: number;
  failures: number;
  badApprovals: number;
  potentialLoss: number;
  suppressedAgents: string[];
}

export interface ReplayTimelineMeta {
  currentCycle: number;
  totalCycles: number;
  suppressionCycle: number | null;
  progress: number;
}

export interface ControlPlaneState {
  source: "live" | "mock" | "replay";
  mode: Mode;
  thresholds: {
    trustThreshold: number;
    suppressionThreshold: number;
    driftDelta: number;
  };
  routingMode: "competitive" | "deterministic";
  systemHealth: "HEALTHY" | "SUPPRESSION ACTIVE";
  agents: AgentRow[];
  events: GovernanceEvent[];
  thresholdSeries: ThresholdPoint[];
  kpis: KpiRow;
  agentHistory: AgentHistoryPoint[];
  cycleSummaries: CycleSummary[];
  reflections: ReflectionItem[];
  replayTimeline: ReplayTimelineMeta;
  suppressionPulse: boolean;
  replayFileName: string;
}
