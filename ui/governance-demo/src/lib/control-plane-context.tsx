"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  computeImpact,
  deriveEvents,
  getNarrative,
  getNewlyRestored,
  getNewlySuppressed,
  getSuppressedAfter,
  playbackIntervalMs,
  type DemoRun,
  type ImpactModel,
  type PlaySpeed,
  type RunCycle,
} from "@/lib/governance";

type ControlPlaneContextValue = {
  run: DemoRun | null;
  loading: boolean;
  error: string | null;
  mode: "replay" | "live";
  setMode: (mode: "replay" | "live") => void;
  cycles: RunCycle[];
  visibleCycles: RunCycle[];
  currentCycle: RunCycle | undefined;
  currentIndex: number;
  setCurrentIndex: (index: number) => void;
  playing: boolean;
  setPlaying: (playing: boolean) => void;
  speed: PlaySpeed;
  setSpeed: (speed: PlaySpeed) => void;
  loadRun: () => Promise<void>;
  annualVolumeInput: string;
  setAnnualVolumeInput: (value: string) => void;
  baselineLossRateInput: string;
  setBaselineLossRateInput: (value: string) => void;
  lossPerFailureInput: string;
  setLossPerFailureInput: (value: string) => void;
  impact: ImpactModel;
  hasTriggeredGovernance: boolean;
  allAgentIds: string[];
  allEvents: ReturnType<typeof deriveEvents>;
  currentNewlySuppressed: string[];
  currentNewlyRestored: string[];
  narrative: string;
  successRate: number;
  activeAgents: number;
  suppressedAgents: number;
  chartData: Array<Record<string, number>>;
  driftRange: { start: number; end: number } | null;
  suppressionMarkers: RunCycle[];
};

const ControlPlaneContext = createContext<ControlPlaneContextValue | null>(null);

export function ControlPlaneProvider({ children }: { children: ReactNode }) {
  const [run, setRun] = useState<DemoRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState<PlaySpeed>(1);
  const [mode, setMode] = useState<"replay" | "live">("replay");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [annualVolumeInput, setAnnualVolumeInput] = useState("120000000");
  const [baselineLossRateInput, setBaselineLossRateInput] = useState("0.003");
  const [lossPerFailureInput, setLossPerFailureInput] = useState("185");

  const loadRun = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (mode === "live") {
        // 1️⃣ Start fraud demo
        const startResponse = await fetch(
          "http://localhost:8000/api/v1/fraud-demo/start",
          {
            method: "POST",
          }
        );

        if (!startResponse.ok) {
          throw new Error("Live engine unavailable");
        }

        // 2️⃣ Fetch generated cycles
        const cyclesResponse = await fetch(
          "http://localhost:8000/api/v1/cycles"
        );

        if (!cyclesResponse.ok) {
          throw new Error("Failed to fetch live cycles");
        }

        const cyclesJson = await cyclesResponse.json();

        const liveCycles = Array.isArray(cyclesJson)
          ? cyclesJson
          : cyclesJson.cycles ?? [];
        const normalizedCycles = liveCycles.map((cycle: RunCycle) => ({
          ...cycle,
          thresholds: {
            trust_threshold: cycle?.thresholds?.trust_threshold ?? 0.70,
            suppression_threshold: cycle?.thresholds?.suppression_threshold ?? 0.75,
            drift_delta: cycle?.thresholds?.drift_delta ?? 0.10,
          },
        }));

        const normalized = {
          run_id: "LIVE_ENGINE",
          window_minutes: 5,
          txn_count_per_cycle: 0,
          cycles: normalizedCycles,
          final: { certified: false },
        };

        setRun(normalized);
        setCurrentIndex(0);
        setPlaying(normalized.cycles.length > 0);

        return;
      } else {
        const response = await fetch(`/demo_results.json?ts=${Date.now()}`, {
          cache: "no-store",
        });

        if (!response.ok) throw new Error("Replay load failed");

        const json = (await response.json()) as DemoRun;
        const normalizedCycles = Array.isArray(json.cycles) ? json.cycles : [];
        setRun({ ...json, cycles: normalizedCycles });
      }

      setCurrentIndex(0);
      setPlaying(true);
    } catch (err) {
      setError("Engine unavailable. Falling back to replay.");
      setMode("replay");
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    void loadRun();
  }, [loadRun]);

  const cycles = run?.cycles ?? [];

  useEffect(() => {
    if (!playing || cycles.length === 0) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => {
        const next = prev + 1;
        if (next >= cycles.length) {
          setPlaying(false);
          return cycles.length - 1;
        }
        return next;
      });
    }, playbackIntervalMs(speed));

    return () => clearInterval(timer);
  }, [playing, cycles, speed]);

  useEffect(() => {
    if (cycles.length === 0) return;
    if (currentIndex >= cycles.length - 1) {
      setPlaying(false);
    }
  }, [currentIndex, cycles.length]);

  const visibleCycles = useMemo(() => cycles.slice(0, currentIndex + 1), [cycles, currentIndex]);
  const currentCycle = visibleCycles[visibleCycles.length - 1];

  const allAgentIds = useMemo(() => {
    const ids = new Set<string>();
    for (const cycle of cycles) {
      for (const agent of Object.keys(cycle.trust || {})) ids.add(agent);
    }
    return Array.from(ids).sort();
  }, [cycles]);

  const allEvents = useMemo(() => deriveEvents(cycles), [cycles]);

  const currentCycleIndex = visibleCycles.length - 1;
  const currentPrevCycle = currentCycleIndex > 0 ? visibleCycles[currentCycleIndex - 1] : null;
  const currentNewlySuppressed = currentCycle
    ? getNewlySuppressed(currentCycle, currentPrevCycle)
    : [];
  const currentNewlyRestored = currentCycle
    ? getNewlyRestored(currentCycle, currentPrevCycle)
    : [];

  const narrative = useMemo(
    () => getNarrative(currentCycle, currentNewlySuppressed, currentNewlyRestored),
    [currentCycle, currentNewlySuppressed, currentNewlyRestored]
  );

  const chartData = useMemo(
    () =>
      visibleCycles.map((cycle) => ({
        cycle: cycle.cycle_index,
        ...cycle.trust,
      })),
    [visibleCycles]
  );

  const driftRange = useMemo(() => {
    const driftCycles = cycles
      .filter((cycle) => cycle.phase === "drift")
      .map((cycle) => cycle.cycle_index);
    if (driftCycles.length === 0) return null;
    return { start: Math.min(...driftCycles), end: Math.max(...driftCycles) };
  }, [cycles]);

  const suppressionMarkers = useMemo(
    () => visibleCycles.filter((cycle) => getSuppressedAfter(cycle).length > 0),
    [visibleCycles]
  );

  const successRate = useMemo(() => {
    if (visibleCycles.length === 0) return 0;
    const successful = visibleCycles.filter((cycle) => !cycle.circuit_breaker).length;
    return (successful / visibleCycles.length) * 100;
  }, [visibleCycles]);

  const activeAgents = allAgentIds.length - getSuppressedAfter(currentCycle ?? null).length;
  const suppressedAgents = getSuppressedAfter(currentCycle ?? null).length;

  const annualVolume = Number(annualVolumeInput) || 0;
  const baselineLossRate = Number(baselineLossRateInput) || 0;
  const lossPerFailure = Number(lossPerFailureInput) || 0;

  const impact = useMemo(
    () => computeImpact(visibleCycles, annualVolume, baselineLossRate, lossPerFailure),
    [visibleCycles, annualVolume, baselineLossRate, lossPerFailure]
  );
  const hasTriggeredGovernance = useMemo(
    () =>
      visibleCycles.some(
        (cycle, index) =>
          getNewlySuppressed(cycle, index > 0 ? visibleCycles[index - 1] : null).length > 0
      ),
    [visibleCycles]
  );

  const value: ControlPlaneContextValue = {
    run,
    loading,
    error,
    mode,
    setMode,
    cycles,
    visibleCycles,
    currentCycle,
    currentIndex,
    setCurrentIndex,
    playing,
    setPlaying,
    speed,
    setSpeed,
    loadRun,
    annualVolumeInput,
    setAnnualVolumeInput,
    baselineLossRateInput,
    setBaselineLossRateInput,
    lossPerFailureInput,
    setLossPerFailureInput,
    impact,
    hasTriggeredGovernance,
    allAgentIds,
    allEvents,
    currentNewlySuppressed,
    currentNewlyRestored,
    narrative,
    successRate,
    activeAgents,
    suppressedAgents,
    chartData,
    driftRange,
    suppressionMarkers,
  };

  return <ControlPlaneContext.Provider value={value}>{children}</ControlPlaneContext.Provider>;
}

export function useControlPlane() {
  const context = useContext(ControlPlaneContext);
  if (!context) {
    throw new Error("useControlPlane must be used within ControlPlaneProvider");
  }
  return context;
}
