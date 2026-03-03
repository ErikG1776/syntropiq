"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useControlPlane } from "@/lib/control-plane-context";

export default function ThresholdsPage() {
  const { visibleCycles } = useControlPlane();

  const thresholdData = useMemo(
    () =>
      visibleCycles.map((cycle) => ({
        cycle: cycle.cycle_index,
        trust_threshold: cycle.thresholds.trust_threshold ?? null,
        suppression_threshold: cycle.thresholds.suppression_threshold ?? null,
        drift_delta: cycle.thresholds.drift_delta ?? null,
      })),
    [visibleCycles]
  );

  const trustMarkers = useMemo(() => {
    const markers: Array<{ cycle: number; value: number; type: "tightened" | "loosened" }> = [];
    for (let i = 1; i < visibleCycles.length; i++) {
      const prev = visibleCycles[i - 1].thresholds.trust_threshold;
      const curr = visibleCycles[i].thresholds.trust_threshold;
      if (typeof prev !== "number" || typeof curr !== "number") continue;
      if (Math.abs(curr - prev) <= 0.0001) continue;
      markers.push({
        cycle: visibleCycles[i].cycle_index,
        value: curr,
        type: curr > prev ? "tightened" : "loosened",
      });
    }
    return markers;
  }, [visibleCycles]);

  const tightenCount = trustMarkers.filter((marker) => marker.type === "tightened").length;
  const loosenCount = trustMarkers.filter((marker) => marker.type === "loosened").length;

  return (
    <section className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardDescription>Tightening Markers</CardDescription>
            <CardTitle className="text-2xl">{tightenCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardDescription>Loosening Markers</CardDescription>
            <CardTitle className="text-2xl">{loosenCount}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle>Threshold Controls</CardTitle>
          <CardDescription>Trust threshold, suppression threshold, and drift delta across cycles.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[460px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={thresholdData}>
                <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                <XAxis dataKey="cycle" />
                <YAxis domain={[0, 1]} />
                <Tooltip />
                <Line type="monotone" dataKey="trust_threshold" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls />
                <Line type="monotone" dataKey="suppression_threshold" stroke="#ea580c" strokeWidth={2} dot={false} connectNulls />
                <Line type="monotone" dataKey="drift_delta" stroke="#059669" strokeWidth={2} dot={false} connectNulls />
                {trustMarkers.map((marker) => (
                  <ReferenceDot
                    key={`${marker.cycle}-${marker.type}`}
                    x={marker.cycle}
                    y={marker.value}
                    r={5}
                    fill={marker.type === "tightened" ? "#16a34a" : "#d97706"}
                    stroke="none"
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
