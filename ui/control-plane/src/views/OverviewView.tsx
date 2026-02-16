import { Play, Pause, SkipForward } from "lucide-react";
import type { ControlPlaneState } from "../types/controlPlane";
import { ThresholdChart } from "../components/charts/ThresholdChart";
import { AgentPoolTable } from "../components/overview/AgentPoolTable";
import { GovernanceEventStream } from "../components/overview/GovernanceEventStream";
import { KpiStrip } from "../components/overview/KpiStrip";
import { CycleTimelineBar } from "../components/overview/CycleTimelineBar";
import { Badge } from "../components/ui/Badge";

interface OverviewViewProps {
  state: ControlPlaneState;
  replay: {
    isPlaying: boolean;
    setIsPlaying: (isPlaying: boolean) => void;
    currentCycle: number;
    totalCycles: number;
    setReplayCycle: (cycle: number) => void;
    jumpToSuppression: () => void;
  };
}

export function OverviewView({ state, replay }: OverviewViewProps) {
  const replayMode = state.mode === "REPLAY";

  return (
    <>
      <section className="flex flex-wrap items-center gap-2 text-[11px] text-textMuted">
        <span className="uppercase tracking-wide">Syntropiq Control Plane</span>
        <Badge label={`Mode: ${state.mode}`} tone={state.mode === "REPLAY" ? "accent" : "ok"} />
        <Badge label={`Data Source: ${state.source.toUpperCase()}`} tone={state.source === "mock" ? "warn" : "ok"} />

        {replayMode ? (
          <>
            <button
              type="button"
              onClick={() => replay.setIsPlaying(!replay.isPlaying)}
              className="inline-flex items-center gap-1 rounded border border-border bg-panelAlt px-2 py-1 text-[11px] text-text"
            >
              {replay.isPlaying ? <Pause size={12} /> : <Play size={12} />}
              {replay.isPlaying ? "Pause" : "Play"}
            </button>
            <button
              type="button"
              onClick={replay.jumpToSuppression}
              className="inline-flex items-center gap-1 rounded border border-danger/50 bg-danger/10 px-2 py-1 text-[11px] text-[#ff7b72]"
            >
              <SkipForward size={12} /> Jump to Suppression
            </button>
          </>
        ) : null}
      </section>

      {replayMode ? (
        <CycleTimelineBar
          currentCycle={replay.currentCycle}
          totalCycles={replay.totalCycles}
          suppressionCycle={state.replayTimeline.suppressionCycle}
          onCycleSelect={(cycle) => {
            replay.setReplayCycle(cycle);
            replay.setIsPlaying(false);
          }}
          onJumpSuppression={replay.jumpToSuppression}
        />
      ) : null}

      <section className="grid gap-3 xl:grid-cols-2">
        <ThresholdChart
          title="Trust Threshold (τ)"
          data={state.thresholdSeries}
          dataKey="trust"
          stroke="#79c0ff"
        />
        <ThresholdChart
          title="Suppression Threshold (τ_s)"
          data={state.thresholdSeries}
          dataKey="suppression"
          stroke="#f2cc60"
        />
      </section>

      <section className="grid gap-3 xl:grid-cols-[1.9fr_1.1fr]">
        <AgentPoolTable
          agents={state.agents}
          subtitle="Trust-sorted decision agents with governance lock state"
        />
        <GovernanceEventStream events={state.events.slice(0, 32)} />
      </section>

      <KpiStrip kpis={state.kpis} suppressionPulse={state.suppressionPulse} />
    </>
  );
}
