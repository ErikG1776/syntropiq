import type { AgentApi, MutationHistoryItem, ReflectionItem, StatisticsResponse } from "../types/controlPlane";

export const mockStatistics: StatisticsResponse = {
  total_executions: 782,
  success_rate: 0.912,
  suppressed_agents: 1,
  valid_reflections: 96,
  total_agents: 6,
  active_agents: 5,
  avg_trust_score: 0.823,
  mutation_performance: {
    avg_success_rate: 0.901,
    trend: "improving",
    cycles_tracked: 160,
  },
};

export const mockAgents: AgentApi[] = [
  { agent_id: "Agent-Alpha", trust_score: 0.94, capabilities: ["analysis"], status: "active" },
  { agent_id: "Agent-Beta", trust_score: 0.89, capabilities: ["triage"], status: "active" },
  { agent_id: "Agent-Gamma", trust_score: 0.81, capabilities: ["routing"], status: "active" },
  { agent_id: "Agent-Delta", trust_score: 0.76, capabilities: ["validation"], status: "active" },
  { agent_id: "Agent-Epsilon", trust_score: 0.68, capabilities: ["execution"], status: "suppressed" },
  { agent_id: "Agent-Zeta", trust_score: 0.73, capabilities: ["monitoring"], status: "active" },
];

export const mockMutationHistory: MutationHistoryItem[] = [
  {
    cycle_id: "CYCLE_001",
    success_rate: 0.80,
    action: "TIGHTENING (poor performance)",
    trust_threshold: { old: 0.70, new: 0.75 },
    suppression_threshold: { old: 0.75, new: 0.80 },
    drift_delta: { old: 0.10, new: 0.12 },
    timestamp: "2026-02-16T18:12:00Z",
  },
  {
    cycle_id: "CYCLE_002",
    success_rate: 0.92,
    action: "LOOSENING (excellent performance)",
    trust_threshold: { old: 0.75, new: 0.70 },
    suppression_threshold: { old: 0.80, new: 0.75 },
    drift_delta: { old: 0.12, new: 0.10 },
    timestamp: "2026-02-16T18:14:00Z",
  },
  {
    cycle_id: "CYCLE_003",
    success_rate: 0.69,
    action: "TIGHTENING (poor performance)",
    trust_threshold: { old: 0.70, new: 0.75 },
    suppression_threshold: { old: 0.75, new: 0.82 },
    drift_delta: { old: 0.10, new: 0.12 },
    timestamp: "2026-02-16T18:16:00Z",
  },
  {
    cycle_id: "CYCLE_004",
    success_rate: 0.90,
    action: "MINOR LOOSENING",
    trust_threshold: { old: 0.75, new: 0.73 },
    suppression_threshold: { old: 0.82, new: 0.82 },
    drift_delta: { old: 0.12, new: 0.12 },
    timestamp: "2026-02-16T18:18:00Z",
  },
  {
    cycle_id: "CYCLE_005",
    success_rate: 0.93,
    action: "LOOSENING (excellent performance)",
    trust_threshold: { old: 0.73, new: 0.68 },
    suppression_threshold: { old: 0.82, new: 0.77 },
    drift_delta: { old: 0.12, new: 0.10 },
    timestamp: "2026-02-16T18:20:00Z",
  },
  {
    cycle_id: "CYCLE_006",
    success_rate: 0.95,
    action: "LOOSENING (excellent performance)",
    trust_threshold: { old: 0.68, new: 0.64 },
    suppression_threshold: { old: 0.77, new: 0.72 },
    drift_delta: { old: 0.10, new: 0.08 },
    timestamp: "2026-02-16T18:22:00Z",
  },
  {
    cycle_id: "CYCLE_007",
    success_rate: 0.90,
    action: "MINOR LOOSENING",
    trust_threshold: { old: 0.64, new: 0.62 },
    suppression_threshold: { old: 0.72, new: 0.72 },
    drift_delta: { old: 0.08, new: 0.08 },
    timestamp: "2026-02-16T18:24:00Z",
  },
  {
    cycle_id: "CYCLE_008",
    success_rate: 0.88,
    action: "MINOR LOOSENING",
    trust_threshold: { old: 0.62, new: 0.60 },
    suppression_threshold: { old: 0.72, new: 0.72 },
    drift_delta: { old: 0.08, new: 0.08 },
    timestamp: "2026-02-16T18:26:00Z",
  },
  {
    cycle_id: "CYCLE_009",
    success_rate: 0.83,
    action: "TIGHTENING (poor performance)",
    trust_threshold: { old: 0.60, new: 0.65 },
    suppression_threshold: { old: 0.72, new: 0.77 },
    drift_delta: { old: 0.08, new: 0.10 },
    timestamp: "2026-02-16T18:28:00Z",
  },
  {
    cycle_id: "CYCLE_010",
    success_rate: 0.91,
    action: "LOOSENING (excellent performance)",
    trust_threshold: { old: 0.65, new: 0.60 },
    suppression_threshold: { old: 0.77, new: 0.72 },
    drift_delta: { old: 0.10, new: 0.08 },
    timestamp: "2026-02-16T18:30:00Z",
  },
];

export const mockReflections: ReflectionItem[] = [
  {
    reflection_text: "Suppression reduced repeated error in a single branch.",
    constraint_score: 4,
    timestamp: "2026-02-16T18:21:00Z",
  },
  {
    reflection_text: "Drift warning triggered mutation tighten sequence.",
    constraint_score: 4,
    timestamp: "2026-02-16T18:25:00Z",
  },
  {
    reflection_text: "Recovered agent reintroduced under guarded routing.",
    constraint_score: 3,
    timestamp: "2026-02-16T18:29:00Z",
  },
];
