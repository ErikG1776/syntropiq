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
      {/* Background */}
      <div className="fixed inset-0 dot-grid opacity-30 pointer-events-none" />

      <div className="relative z-10 flex flex-col flex-1 p-5 gap-4 max-w-[1600px] mx-auto w-full">
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

        {/* Main content area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
          {/* Trust chart - takes 2/3 */}
          <div className="lg:col-span-2">
            <TrustChart
              trustHistory={player.trustHistory}
              domain={player.domainConfig}
              currentCycle={player.currentCycle}
            />
          </div>

          {/* Agent cards - takes 1/3 */}
          <div>
            <AgentCards
              currentCycle={player.currentCycle}
              domain={player.domainConfig}
            />
          </div>
        </div>

        {/* Bottom row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Event stream */}
          <div className="lg:col-span-1">
            <EventStream events={player.visibleEvents} />
          </div>

          {/* Threshold chart */}
          <div className="lg:col-span-1">
            <ThresholdChart thresholdHistory={player.thresholdHistory} />
          </div>

          {/* Comparison panel */}
          <div className="lg:col-span-1">
            <ComparisonPanel
              stats={player.stats}
              lossLabel={player.domainConfig.lossLabel}
            />
          </div>
        </div>

        {/* Timeline controls */}
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
