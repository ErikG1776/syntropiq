"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

interface ThresholdChartProps {
  thresholdHistory: Array<{
    cycle: number;
    trust_threshold: number;
    suppression_threshold: number;
  }>;
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: number;
}) {
  if (!active || !payload) return null;
  return (
    <div className="bg-card border border-border rounded-xl p-3 shadow-2xl">
      <p className="text-muted-foreground text-[10px] font-mono mb-2">
        Cycle {label}
      </p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2 mb-1 last:mb-0">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: p.color }}
          />
          <span className="text-xs text-muted-foreground">
            {p.name === "trust_threshold" ? "Trust \u03c4" : "Suppress \u03c4\u209b"}
          </span>
          <span className="ml-auto text-xs font-mono font-medium tabular-nums pl-3 text-foreground">
            {p.value?.toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ThresholdChart({ thresholdHistory }: ThresholdChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Threshold Adaptation</CardTitle>
        <CardDescription>Governance boundaries responding to system state</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={170}>
          <AreaChart
            data={thresholdHistory}
            margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(148,163,184,0.06)"
              vertical={false}
            />
            <XAxis
              dataKey="cycle"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "#64748b" }}
            />
            <YAxis
              domain={[0.5, 1.0]}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "#64748b" }}
              tickFormatter={(v: number) => v.toFixed(2)}
            />
            <Tooltip content={<ChartTooltip />} />

            <Area
              type="monotone"
              dataKey="suppression_threshold"
              stroke="#ef4444"
              fill="rgba(239,68,68,0.04)"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              animationDuration={400}
            />
            <Area
              type="monotone"
              dataKey="trust_threshold"
              stroke="#eab308"
              fill="rgba(234,179,8,0.04)"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              animationDuration={400}
            />
          </AreaChart>
        </ResponsiveContainer>

        <div className="flex items-center justify-center gap-6 mt-2 pt-2 border-t border-border">
          <div className="flex items-center gap-2">
            <span className="w-4 h-[1.5px] rounded-full bg-warning/60 block" />
            <span className="text-[10px] text-muted-foreground">Trust \u03c4</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-[1.5px] rounded-full bg-destructive/60 block" />
            <span className="text-[10px] text-muted-foreground">Suppress \u03c4\u209b</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
