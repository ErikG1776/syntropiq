"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { formatMoney } from "@/lib/governance";
import { useControlPlane } from "@/lib/control-plane-context";

export default function ImpactPage() {
  const {
    annualVolumeInput,
    setAnnualVolumeInput,
    baselineLossRateInput,
    setBaselineLossRateInput,
    lossPerFailureInput,
    setLossPerFailureInput,
    impact,
    hasTriggeredGovernance,
  } = useControlPlane();

  const reductionWidth = Math.max(0, Math.min(100, impact.reductionPct));

  return (
    <section className="space-y-6">
      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle>Enterprise Impact Model</CardTitle>
          <CardDescription>Annual fraud exposure and governance-adjusted savings projection.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">Annual Transactions</p>
              <Input value={annualVolumeInput} onChange={(e) => setAnnualVolumeInput(e.target.value.replace(/[^0-9]/g, ""))} />
            </div>
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">Fraud Rate (Decimal)</p>
              <Input value={baselineLossRateInput} onChange={(e) => setBaselineLossRateInput(e.target.value.replace(/[^0-9.]/g, ""))} />
            </div>
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">Loss Per Fraud Event</p>
              <Input value={lossPerFailureInput} onChange={(e) => setLossPerFailureInput(e.target.value.replace(/[^0-9.]/g, ""))} />
            </div>
          </div>

          <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4 space-y-1 text-sm">
            <p className="font-medium text-zinc-700 dark:text-zinc-300">Formula</p>
            <p className="text-zinc-600 dark:text-zinc-400">Annual Fraud Events = Annual Transactions x Fraud Rate</p>
            <p className="text-zinc-600 dark:text-zinc-400">Annual Risk Exposure = Annual Fraud Events x Loss Per Fraud Event</p>
            <p className="text-zinc-600 dark:text-zinc-400">Without Governance = Annual Risk Exposure x (1 + Drift Amplification)</p>
            <p className="text-zinc-600 dark:text-zinc-400">With Syntropiq = Annual Risk Exposure x (1 - Governance Reduction)</p>
            <p className="text-zinc-600 dark:text-zinc-400">Net Annual Savings = Without Governance - With Syntropiq</p>
          </div>

          <Separator />

          {!hasTriggeredGovernance ? (
            <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 text-center">
              <p className="text-base font-semibold text-zinc-700 dark:text-zinc-300">
                Projected risk exposure: {formatMoney(impact.annualRiskExposure)}
              </p>
              <p className="text-sm text-zinc-500 mt-2">
                Net annual savings unlocks after first governance suppression event.
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 transition-all duration-500">
                <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
                  <p className="text-xs uppercase tracking-wide text-zinc-500">Annual Fraud Events</p>
                  <p className="mt-1 text-2xl font-semibold">{impact.annualFraudEvents.toLocaleString()}</p>
                </div>
                <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
                  <p className="text-xs uppercase tracking-wide text-zinc-500">Fraud Events Avoided</p>
                  <p className="mt-1 text-2xl font-semibold">{impact.fraudEventsAvoided.toLocaleString()}</p>
                </div>
                <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
                  <p className="text-xs uppercase tracking-wide text-zinc-500">Annual Risk Exposure</p>
                  <p className="mt-1 text-2xl font-semibold">{formatMoney(impact.annualRiskExposure)}</p>
                </div>
                <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
                  <p className="text-xs uppercase tracking-wide text-zinc-500">Without Governance</p>
                  <p className="mt-1 text-2xl font-semibold">{formatMoney(impact.withoutGovernance)}</p>
                  <p className="text-xs text-zinc-500 mt-1">Drift Amplification: {(impact.driftAmplification * 100).toFixed(1)}%</p>
                </div>
                <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4 md:col-span-2">
                  <p className="text-xs uppercase tracking-wide text-zinc-500">With Syntropiq</p>
                  <p className="mt-1 text-2xl font-semibold">{formatMoney(impact.withSyntropiq)}</p>
                  <p className="text-xs text-zinc-500 mt-1">Governance Reduction: {(impact.governanceReduction * 100).toFixed(1)}%</p>
                </div>
              </div>

              <div className="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-4 space-y-2 transition-all duration-500">
                <p className="text-xs text-emerald-700">Unlocked after governance intervention</p>
                <p className="text-xs uppercase tracking-wide text-emerald-700">Net Annual Savings</p>
                <p className="text-sm text-emerald-700">
                  {impact.fraudEventsAvoided.toLocaleString()} fraud events prevented annually
                </p>
                <p className="text-3xl font-semibold text-emerald-700">{formatMoney(impact.netSavings)}</p>
                <p className="text-sm text-emerald-700">Risk Reduction: {impact.reductionPct.toFixed(1)}%</p>
                <div className="h-2 rounded-full bg-emerald-100 overflow-hidden">
                  <div className="h-full bg-emerald-600" style={{ width: `${reductionWidth}%` }} />
                </div>
              </div>

              <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4 space-y-3">
                <p className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Governance Mechanics Driving Savings</p>
                <div className="grid grid-cols-1 gap-3 text-sm text-zinc-700 dark:text-zinc-300 md:grid-cols-2">
                  <p>Drift cycles detected: {impact.driftWindowLength}</p>
                  <p>Suppression events: {impact.totalSuppressionEvents}</p>
                  <p>Avg time to containment: {impact.avgTimeToContainment.toFixed(1)} cycles</p>
                  <p>Avg suppression duration: {impact.avgSuppressionDuration.toFixed(1)} cycles</p>
                  <p>Governance reduction: {(impact.governanceReduction * 100).toFixed(1)}%</p>
                  <p>Drift amplification: {(impact.driftAmplification * 100).toFixed(1)}%</p>
                </div>
                <p className="text-xs text-zinc-500">
                  Impact is computed from observed trust degradation, suppression latency, and adaptive threshold
                  enforcement across the playback window.
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
