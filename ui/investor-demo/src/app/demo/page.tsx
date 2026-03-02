"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  computeEnterpriseImpact,
  deriveNarrativeEvents,
  findDriftWindow,
  getAgentIds,
  loadDemoRunResult,
  type DemoRunResult,
  type NarrativeEvent,
} from "@/lib/demo-data";

const AGENT_COLORS = ["#22d3ee", "#a78bfa", "#34d399", "#f59e0b", "#f43f5e"];

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function eventVariant(type: NarrativeEvent["type"]): "default" | "warning" | "danger" | "success" | "accent" {
  if (type === "suppression" || type === "circuit_breaker") return "danger";
  if (type === "drift_detected") return "warning";
  if (type === "recovery") return "success";
  if (type === "threshold_adaptation") return "accent";
  return "default";
}

export default function DemoPage() {
  const [result, setResult] = useState<DemoRunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [annualVolumeInput, setAnnualVolumeInput] = useState("120000000");

  const loadDemo = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await loadDemoRunResult();
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run JSON");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDemo();
  }, [loadDemo]);

  const agentIds = useMemo(() => getAgentIds(result?.cycles ?? []), [result]);
  const trustRows = useMemo(
    () =>
      (result?.cycles ?? []).map((c) => ({
        cycle: c.cycle_index,
        ...c.trust,
      })),
    [result]
  );
  const suppressionCycles = useMemo(
    () => (result?.cycles ?? []).filter((c) => c.suppressed_agents.length > 0),
    [result]
  );
  const events = useMemo(() => deriveNarrativeEvents(result?.cycles ?? []), [result]);
  const driftWindow = useMemo(() => findDriftWindow(result?.cycles ?? []), [result]);

  const annualVolume = useMemo(() => {
    const parsed = Number(annualVolumeInput);
    if (!Number.isFinite(parsed) || parsed <= 0) return 0;
    return parsed;
  }, [annualVolumeInput]);

  const impact = useMemo(
    () => (result && annualVolume > 0 ? computeEnterpriseImpact(result, annualVolume) : null),
    [annualVolume, result]
  );

  const latest = result?.cycles[result.cycles.length - 1];
  const runId = result?.run_id ?? "--";

  return (
    <div className="min-h-screen bg-[#0b1220] text-zinc-100">
      <div className="mx-auto max-w-7xl px-8 py-8">
        <div className="mb-8 flex items-center justify-between border-b border-white/10 pb-5">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Enterprise Governance Demo</h1>
            <p className="text-sm text-zinc-400">Run: {runId}</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={result?.final.certified ? "success" : "default"}>
              {result?.final.certified ? "Certified" : "Not Certified"}
            </Badge>
            <Button variant="secondary" onClick={() => void loadDemo()} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Load Run JSON
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-6 flex items-center gap-2 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
            <AlertTriangle className="h-4 w-4" />
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
          <div className="xl:col-span-8">
            <Card className="border border-white/10 bg-[#111827]">
              <CardHeader>
                <CardTitle className="text-base normal-case tracking-normal text-zinc-100">Trust Trajectory</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[420px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trustRows}>
                      <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
                      <XAxis dataKey="cycle" stroke="rgba(255,255,255,0.45)" />
                      <YAxis domain={[0, 1]} stroke="rgba(255,255,255,0.45)" />
                      <Tooltip />
                      <Legend />

                      {typeof driftWindow.start === "number" && typeof driftWindow.end === "number" && (
                        <ReferenceArea
                          x1={driftWindow.start}
                          x2={driftWindow.end}
                          fill="rgba(244,63,94,0.11)"
                          strokeOpacity={0}
                        />
                      )}

                      {suppressionCycles.map((c) => (
                        <ReferenceDot
                          key={`s-${c.cycle_index}`}
                          x={c.cycle_index}
                          y={0.98}
                          r={4}
                          fill="#f43f5e"
                          stroke="none"
                        />
                      ))}

                      {typeof latest?.thresholds.trust_threshold === "number" && (
                        <ReferenceLine
                          y={latest.thresholds.trust_threshold}
                          stroke="rgba(56,189,248,0.6)"
                          strokeDasharray="6 6"
                          strokeWidth={1}
                        />
                      )}
                      {typeof latest?.thresholds.suppression_threshold === "number" && (
                        <ReferenceLine
                          y={latest.thresholds.suppression_threshold}
                          stroke="rgba(249,115,22,0.6)"
                          strokeDasharray="6 6"
                          strokeWidth={1}
                        />
                      )}

                      {agentIds.map((agent, idx) => (
                        <Line
                          key={agent}
                          type="monotone"
                          dataKey={agent}
                          name={agent}
                          stroke={AGENT_COLORS[idx % AGENT_COLORS.length]}
                          strokeWidth={2.1}
                          dot={false}
                          connectNulls
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6 xl:col-span-4">
            <Card className="border border-white/10 bg-[#111827]">
              <CardHeader>
                <CardTitle className="text-base normal-case tracking-normal text-zinc-100">Narrative Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px] space-y-3 overflow-y-auto pr-1">
                  {events.length === 0 ? (
                    <p className="text-sm text-zinc-400">Events will appear here.</p>
                  ) : (
                    events.map((event) => (
                      <div key={event.id} className="rounded-md border border-white/10 bg-[#0b1220] p-3">
                        <div className="mb-1 flex items-center justify-between">
                          <Badge variant={eventVariant(event.type)}>{event.title}</Badge>
                          <span className="text-xs text-zinc-500">Cycle {event.cycle}</span>
                        </div>
                        <p className="text-sm text-zinc-300">{event.detail}</p>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border border-white/10 bg-[#111827]">
              <CardHeader>
                <CardTitle className="text-base normal-case tracking-normal text-zinc-100">Enterprise Impact</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="mb-1 text-xs uppercase tracking-[0.14em] text-zinc-500">Annual Transaction Volume</p>
                  <input
                    className="w-full rounded-md border border-white/10 bg-[#0b1220] px-3 py-2 text-sm outline-none focus:border-sky-500"
                    value={annualVolumeInput}
                    onChange={(e) => setAnnualVolumeInput(e.target.value.replace(/[^0-9]/g, ""))}
                  />
                </div>
                <div className="rounded-md border border-white/10 bg-[#0b1220] px-3 py-2 text-sm">
                  <p className="text-zinc-400">Estimated Loss Without Governance</p>
                  <p className="mt-1 font-medium text-zinc-100">
                    {impact ? formatCurrency(impact.estimatedLossWithout) : "--"}
                  </p>
                </div>
                <div className="rounded-md border border-white/10 bg-[#0b1220] px-3 py-2 text-sm">
                  <p className="text-zinc-400">Estimated Loss With Syntropiq</p>
                  <p className="mt-1 font-medium text-zinc-100">
                    {impact ? formatCurrency(impact.estimatedLossWith) : "--"}
                  </p>
                </div>
                <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm">
                  <p className="text-emerald-300">Net Annual Savings</p>
                  <p className="mt-1 font-semibold text-emerald-300">
                    {impact ? formatCurrency(impact.savings) : "--"}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  <ShieldCheck className="h-4 w-4 text-zinc-400" />
                  {impact ? `${impact.reductionPct.toFixed(1)}% modeled annual reduction` : "Load run to compute modeled impact"}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
