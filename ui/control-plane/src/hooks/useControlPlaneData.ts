import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getAgents, getMutationHistory, getReflections, getStatistics } from "../lib/api";
import { mockAgents, mockMutationHistory, mockReflections, mockStatistics } from "../lib/mockData";
import {
  agentHistoryFromTimeline,
  agentsFromCycle,
  buildFallbackReplayResult,
  cumulativeKpis,
  cycleSummariesFromTimeline,
  eventsFromTimeline,
  parseReplayJson,
  thresholdSeriesFromTimeline,
  timelineSuppressionCycle,
} from "../lib/replay";
import type {
  AgentApi,
  AgentHistoryPoint,
  AgentRow,
  ControlPlaneState,
  GovernanceEvent,
  Mode,
  MutationHistoryItem,
  ReflectionItem,
  ReplayCycle,
  ReplayResult,
  StatisticsResponse,
  ThresholdPoint,
} from "../types/controlPlane";

const POLL_INTERVAL_MS = 2000;
const REPLAY_DURATION_MS = 25_000;

const DEFAULT_REPLAY = buildFallbackReplayResult();

const DEFAULT_STATE: ControlPlaneState = {
  source: "replay",
  mode: "REPLAY",
  thresholds: {
    trustThreshold: DEFAULT_REPLAY.timeline[0].trust_threshold ?? 0.7,
    suppressionThreshold: DEFAULT_REPLAY.timeline[0].suppression_threshold ?? 0.75,
    driftDelta: DEFAULT_REPLAY.timeline[0].drift_tolerance ?? 0.1,
  },
  routingMode: DEFAULT_REPLAY.config.routing_mode,
  systemHealth: "HEALTHY",
  agents: [],
  events: [],
  thresholdSeries: thresholdSeriesFromTimeline(DEFAULT_REPLAY.timeline),
  kpis: {
    preventedDelta: 0,
    driftLossBeforeSuppression: 0,
    driftLossAfterSuppression: 0,
    overallSuccessRate: 0,
    cyclesExecuted: 0,
  },
  agentHistory: agentHistoryFromTimeline(DEFAULT_REPLAY.timeline),
  cycleSummaries: cycleSummariesFromTimeline(DEFAULT_REPLAY.timeline),
  reflections: [],
  replayTimeline: {
    currentCycle: 1,
    totalCycles: DEFAULT_REPLAY.timeline.length,
    suppressionCycle:
      timelineSuppressionCycle(DEFAULT_REPLAY.timeline) === null
        ? null
        : timelineSuppressionCycle(DEFAULT_REPLAY.timeline)! + 1,
    progress: 0,
  },
  suppressionPulse: false,
  replayFileName: "fallback-demo-results",
};

function normalizeAgentRows(
  agents: AgentApi[],
  trustThreshold: number,
  suppressionThreshold: number
): AgentRow[] {
  return agents
    .map((agent, idx) => {
      const normalized = agent.status.toLowerCase();
      const suppressed = normalized.includes("suppress") || agent.trust_score < suppressionThreshold;
      const drifting = !suppressed && agent.trust_score < trustThreshold + 0.03;

      return {
        name: agent.agent_id,
        trust: agent.trust_score,
        status: suppressed ? "SUPPRESSED" : drifting ? "DRIFTING" : "ACTIVE",
        drifting,
        lastSeen: suppressed ? "policy lock" : `${idx + 1}s ago`,
        tasks: Math.max(0, Math.round(agent.trust_score * 18) - idx),
        executionBlocked: suppressed,
        frozen: suppressed,
      };
    })
    .sort((a, b) => b.trust - a.trust);
}

function liveThresholdSeries(
  mutationHistory: MutationHistoryItem[],
  trustThreshold: number,
  suppressionThreshold: number
): ThresholdPoint[] {
  if (mutationHistory.length === 0) {
    return [
      { cycle: "LIVE_001", cycleNumber: 1, trust: trustThreshold, suppression: suppressionThreshold, drift: 0.1 },
      { cycle: "LIVE_002", cycleNumber: 2, trust: trustThreshold, suppression: suppressionThreshold, drift: 0.1 },
    ];
  }

  return mutationHistory.map((m, index) => ({
    cycle: m.cycle_id,
    cycleNumber: index + 1,
    trust: m.trust_threshold.new,
    suppression: m.suppression_threshold.new,
    drift: m.drift_delta.new,
  }));
}

function liveAgentHistory(agentRows: AgentRow[]): AgentHistoryPoint[] {
  return [
    {
      cycle: 1,
      ...Object.fromEntries(agentRows.map((a) => [a.name, a.trust])),
    },
  ];
}

function liveEvents(
  mutationHistory: MutationHistoryItem[],
  reflections: ReflectionItem[],
  agentRows: AgentRow[],
  previousSuppressed: Set<string>
): { events: GovernanceEvent[]; suppressionPulse: boolean } {
  const statusEvents: GovernanceEvent[] = [];
  const currentSuppressed = new Set(agentRows.filter((a) => a.status === "SUPPRESSED").map((a) => a.name));
  let suppressionPulse = false;

  for (const id of currentSuppressed) {
    if (!previousSuppressed.has(id)) {
      suppressionPulse = true;
      statusEvents.push({
        timestamp: new Date().toISOString(),
        cycle: mutationHistory.length || 1,
        type: "SUPPRESSED",
        agent: id,
        message: `${id} suppressed. Execution blocked by governance policy.`,
      });
    }
  }

  for (const id of previousSuppressed) {
    if (!currentSuppressed.has(id)) {
      statusEvents.push({
        timestamp: new Date().toISOString(),
        cycle: mutationHistory.length || 1,
        type: "REDEEMED",
        agent: id,
        message: `${id} redeemed and restored to active routing.`,
      });
    }
  }

  previousSuppressed.clear();
  currentSuppressed.forEach((id) => previousSuppressed.add(id));

  agentRows
    .filter((a) => a.status === "DRIFTING")
    .forEach((agent) => {
      statusEvents.push({
        timestamp: new Date().toISOString(),
        cycle: mutationHistory.length || 1,
        type: "DRIFT DETECTED",
        agent: agent.name,
        message: `${agent.name} trust trend near suppression boundary`,
      });
    });

  const mutationEvents: GovernanceEvent[] = mutationHistory.map((m, idx) => ({
    timestamp: m.timestamp,
    cycle: idx + 1,
    type: m.action.toUpperCase().includes("TIGHT") ? "MUTATION TIGHTEN" : "MUTATION LOOSEN",
    agent: "governance",
    message: `${m.cycle_id}: ${m.action}`,
  }));

  const reflectionEvents: GovernanceEvent[] = reflections.map((r, idx) => ({
    timestamp: r.timestamp,
    cycle: idx + 1,
    type: "DRIFT DETECTED",
    agent: "reflection-engine",
    message: r.reflection_text,
  }));

  const events = [...statusEvents, ...mutationEvents, ...reflectionEvents].sort(
    (a, b) => +new Date(b.timestamp) - +new Date(a.timestamp)
  );

  return { events, suppressionPulse };
}

function mapLiveState(
  statistics: StatisticsResponse,
  agents: AgentApi[],
  mutationHistory: MutationHistoryItem[],
  reflections: ReflectionItem[],
  previousSuppressed: Set<string>
): ControlPlaneState {
  const latest = mutationHistory[mutationHistory.length - 1];
  const trustThreshold = latest?.trust_threshold.new ?? 0.7;
  const suppressionThreshold = latest?.suppression_threshold.new ?? 0.75;
  const driftDelta = latest?.drift_delta.new ?? 0.1;

  const agentRows = normalizeAgentRows(agents, trustThreshold, suppressionThreshold);

  const { events, suppressionPulse } = liveEvents(mutationHistory, reflections, agentRows, previousSuppressed);

  // ✅ FIX: LIVE health derived from CURRENT agent status, not historical counter
  const hasSuppressed = agentRows.some((a) => a.status === "SUPPRESSED");

  const driftCount = agentRows.filter((a) => a.status === "DRIFTING").length;
  const suppressedCount = agentRows.filter((a) => a.status === "SUPPRESSED").length;
  const beforeLoss = driftCount * 4800 + suppressedCount * 2700;
  const afterLoss = Math.max(900, beforeLoss * 0.34);

  const cycleSummaries = mutationHistory.map((item, index) => ({
    cycle: index + 1,
    phase: "LIVE",
    status: "executed",
    successes: Math.round(item.success_rate * 10),
    failures: 10 - Math.round(item.success_rate * 10),
    badApprovals: 0,
    potentialLoss: 0,
    suppressedAgents: [],
  }));

  return {
    source: "live",
    mode: "LIVE",
    routingMode: (import.meta.env.VITE_ROUTING_MODE ?? "deterministic") as "competitive" | "deterministic",
    thresholds: { trustThreshold, suppressionThreshold, driftDelta },
    systemHealth: hasSuppressed ? "SUPPRESSION ACTIVE" : "HEALTHY",
    agents: agentRows,
    events,
    thresholdSeries: liveThresholdSeries(mutationHistory, trustThreshold, suppressionThreshold),
    kpis: {
      preventedDelta: Math.max(0, beforeLoss - afterLoss) * 2.4,
      driftLossBeforeSuppression: beforeLoss,
      driftLossAfterSuppression: afterLoss,
      overallSuccessRate: statistics.success_rate,
      cyclesExecuted: Math.max(statistics.total_executions, mutationHistory.length),
    },
    agentHistory: liveAgentHistory(agentRows),
    cycleSummaries,
    reflections,
    replayTimeline: {
      currentCycle: Math.max(1, mutationHistory.length),
      totalCycles: Math.max(50, mutationHistory.length),
      suppressionCycle: null,
      progress: 0,
    },
    suppressionPulse,
    replayFileName: "",
  };
}

function mapReplayState(
  replay: ReplayResult,
  currentIndex: number,
  suppressionPulse: boolean,
  replayFileName: string
): ControlPlaneState {
  const timeline = replay.timeline;
  const cycle = timeline[Math.max(0, Math.min(currentIndex, timeline.length - 1))];
  const prevCycle: ReplayCycle | null = cycle.cycle > 0 ? timeline[cycle.cycle - 1] : null;

  const suppressionCycle = timelineSuppressionCycle(timeline);

  const thresholdSeries = thresholdSeriesFromTimeline(timeline);
  const events = eventsFromTimeline(timeline, cycle.cycle);

  const trustThreshold = cycle.trust_threshold ?? replay.final_state.trust_threshold;
  const suppressionThreshold = cycle.suppression_threshold ?? replay.final_state.suppression_threshold;
  const driftDelta = cycle.drift_tolerance ?? replay.final_state.drift_tolerance_final ?? 0.1;

  return {
    source: "replay",
    mode: "REPLAY",
    routingMode: replay.config.routing_mode,
    thresholds: { trustThreshold, suppressionThreshold, driftDelta },
    systemHealth: (cycle.suppressed_agents ?? []).length > 0 ? "SUPPRESSION ACTIVE" : "HEALTHY",
    agents: agentsFromCycle(cycle, prevCycle, replay.config.drift_agent ?? "growth"),
    events,
    thresholdSeries,
    kpis: cumulativeKpis(timeline, cycle.cycle),
    agentHistory: agentHistoryFromTimeline(timeline),
    cycleSummaries: cycleSummariesFromTimeline(timeline),
    reflections: [],
    replayTimeline: {
      currentCycle: cycle.cycle + 1,
      totalCycles: timeline.length,
      suppressionCycle: suppressionCycle === null ? null : suppressionCycle + 1,
      progress: timeline.length > 1 ? cycle.cycle / (timeline.length - 1) : 0,
    },
    suppressionPulse,
    replayFileName,
  };
}

export function useControlPlaneData() {
  const [mode, setMode] = useState<Mode>("REPLAY");
  const [liveState, setLiveState] = useState<ControlPlaneState>(DEFAULT_STATE);
  const [replayData, setReplayData] = useState<ReplayResult>(DEFAULT_REPLAY);
  const [replayFileName, setReplayFileName] = useState<string>("fallback-demo-results");
  const [currentReplayIndex, setCurrentReplayIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showReplayLoader, setShowReplayLoader] = useState(false);
  const [suppressionPulse, setSuppressionPulse] = useState(false);

  const previousSuppressedLive = useRef<Set<string>>(new Set());
  const previousSuppressedReplay = useRef<Set<string>>(new Set());

  // LIVE poll
  useEffect(() => {
    let mounted = true;

    async function loadLive() {
      try {
        const [statistics, agents, mutationHistory, reflections] = await Promise.all([
          getStatistics(),
          getAgents(),
          getMutationHistory(120),
          getReflections(120),
        ]);

        if (!mounted) return;

        const mapped = mapLiveState(statistics, agents, mutationHistory, reflections, previousSuppressedLive.current);
        setLiveState(mapped);
        setError(null);
      } catch (err) {
        if (!mounted) return;

        const fallback = mapLiveState(
          mockStatistics,
          mockAgents,
          mockMutationHistory,
          mockReflections,
          previousSuppressedLive.current
        );
        fallback.source = "mock";
        setLiveState(fallback);
        setError(err instanceof Error ? err.message : "API unavailable");
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadLive();
    const pollId = setInterval(loadLive, POLL_INTERVAL_MS);

    return () => {
      mounted = false;
      clearInterval(pollId);
    };
  }, []);

  // REPLAY playback (25 sec)
  useEffect(() => {
    if (mode !== "REPLAY" || !isPlaying || replayData.timeline.length <= 1) return;

    const stepMs = Math.max(120, Math.floor(REPLAY_DURATION_MS / replayData.timeline.length));
    const timer = setInterval(() => {
      setCurrentReplayIndex((prev) => {
        if (prev >= replayData.timeline.length - 1) return prev;
        return prev + 1;
      });
    }, stepMs);

    return () => clearInterval(timer);
  }, [mode, isPlaying, replayData]);

  // suppression pulse in replay
  useEffect(() => {
    const timeline = replayData.timeline;
    const current = timeline[Math.max(0, Math.min(currentReplayIndex, timeline.length - 1))];
    const currentSuppressed = new Set(current?.suppressed_agents ?? []);

    let fired = false;
    for (const id of currentSuppressed) {
      if (!previousSuppressedReplay.current.has(id)) {
        fired = true;
        break;
      }
    }

    if (fired) {
      setSuppressionPulse(true);
      const timeout = setTimeout(() => setSuppressionPulse(false), 1800);
      previousSuppressedReplay.current = currentSuppressed;
      return () => clearTimeout(timeout);
    }

    previousSuppressedReplay.current = currentSuppressed;
    return undefined;
  }, [currentReplayIndex, replayData]);

  const state = useMemo(() => {
    if (mode === "LIVE") {
      return { ...liveState, mode: "LIVE" as const, suppressionPulse: liveState.suppressionPulse };
    }
    return mapReplayState(replayData, currentReplayIndex, suppressionPulse, replayFileName);
  }, [mode, liveState, replayData, currentReplayIndex, suppressionPulse, replayFileName]);

  const jumpToSuppression = useCallback(() => {
    const index = timelineSuppressionCycle(replayData.timeline);
    if (index !== null) {
      setCurrentReplayIndex(index);
      setIsPlaying(false);
    }
  }, [replayData]);

  const uploadReplay = useCallback(async (file: File) => {
    const text = await file.text();
    const parsed = parseReplayJson(text);

    setReplayData(parsed);
    setReplayFileName(file.name);
    setCurrentReplayIndex(0);
    setIsPlaying(true);
    setMode("REPLAY");
    setShowReplayLoader(false);
    previousSuppressedReplay.current = new Set();
  }, []);

  const setReplayCycle = useCallback(
    (cycleNumber: number) => {
      const index = Math.max(0, Math.min(cycleNumber - 1, replayData.timeline.length - 1));
      setCurrentReplayIndex(index);
    },
    [replayData.timeline.length]
  );

  return {
    state,
    loading,
    error,
    isMock: state.source === "mock",
    mode,
    setMode,
    replay: {
      isPlaying,
      setIsPlaying,
      currentCycle: currentReplayIndex + 1,
      totalCycles: replayData.timeline.length,
      setReplayCycle,
      jumpToSuppression,
      uploadReplay,
      showReplayLoader,
      setShowReplayLoader,
      replayFileName,
    },
  };
}