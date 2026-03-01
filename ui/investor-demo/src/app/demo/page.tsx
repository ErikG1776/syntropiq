"use client";

import { useDemoPlayer } from "@/hooks/use-demo-player";
import { DomainHeader } from "@/components/dashboard/domain-header";
import { NarrationBanner } from "@/components/dashboard/narration-banner";
import { KpiStrip } from "@/components/dashboard/kpi-strip";
import { TrustChart } from "@/components/dashboard/trust-chart";
import { AgentCards } from "@/components/dashboard/agent-cards";
import { EventStream } from "@/components/dashboard/event-stream";
import { ComparisonPanel } from "@/components/dashboard/comparison-panel";
import { ThresholdChart } from "@/components/dashboard/threshold-chart";
import { TimelineControls } from "@/components/dashboard/timeline-controls";

export default function DemoPage() {
  const player = useDemoPlayer();

  return (
    <div className="min-h-screen flex flex-col">
      <div className="relative z-10 flex flex-col flex-1 px-5 pt-4 pb-2 gap-4 max-w-[1520px] mx-auto w-full">
        {/* Header with domain tabs */}
        <DomainHeader
          activeDomain={player.domain}
          onDomainChange={player.setDomain}
        />

        {/* Narration banner */}
        <NarrationBanner
          currentCycle={player.currentCycle}
          events={player.visibleEvents}
          domain={player.domainConfig}
        />

        {/* KPI strip */}
        <KpiStrip
          stats={player.stats}
          lossLabel={player.domainConfig.lossLabel}
        />

        {/* Main content: trust chart (8 cols) + sidebar (4 cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0">
          {/* Left: charts stacked */}
          <div className="lg:col-span-8 flex flex-col gap-4">
            <TrustChart
              trustHistory={player.trustHistory}
              domain={player.domainConfig}
              currentCycle={player.currentCycle}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ThresholdChart thresholdHistory={player.thresholdHistory} />
              <ComparisonPanel
                stats={player.stats}
                lossLabel={player.domainConfig.lossLabel}
              />
            </div>
          </div>

          {/* Right: agents + events */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            <AgentCards
              currentCycle={player.currentCycle}
              domain={player.domainConfig}
            />
            <div className="flex-1 min-h-0">
              <EventStream events={player.visibleEvents} />
            </div>
          </div>
        </div>

        {/* Timeline controls - sticky bottom */}
        <TimelineControls
          playState={player.playState}
          speed={player.speed}
          currentCycleIndex={player.currentCycleIndex}
          totalCycles={player.timeline.length}
          currentPhase={player.stats.currentPhase}
          onPlay={player.play}
          onPause={player.pause}
          onReset={player.reset}
          onSetSpeed={player.setSpeed}
          onSkipTo={player.skipTo}
        />
      </div>
    </div>
  );
}
