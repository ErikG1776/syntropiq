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
    <div className="bg-surface-elevated border border-border-bright rounded-xl p-3 text-xs shadow-2xl">
      <p className="text-text-muted mb-2 font-mono text-[10px]">
        Cycle {label}
      </p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2 mb-1 last:mb-0">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: p.color }}
          />
          <span className="text-text-secondary">
            {p.name === "trust_threshold"
              ? "Trust \u03c4"
              : "Suppress \u03c4\u209b"}
          </span>
          <span className="ml-auto font-mono font-medium tabular-nums pl-3">
            {p.value?.toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ThresholdChart({ thresholdHistory }: ThresholdChartProps) {
  return (
    <div className="panel p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold mb-0.5">Threshold Adaptation</h3>
        <p className="text-[11px] text-text-muted">
          Governance boundaries mutating in response to system state
        </p>
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <AreaChart
          data={thresholdHistory}
          margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.03)"
            vertical={false}
          />
          <XAxis
            dataKey="cycle"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fill: "#52525b" }}
          />
          <YAxis
            domain={[0.5, 1.0]}
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fill: "#52525b" }}
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

      <div className="flex items-center justify-center gap-6 mt-3">
        <div className="flex items-center gap-2">
          <span className="w-4 h-[1.5px] rounded-full bg-amber-500/60 block" />
          <span className="text-[10px] text-text-muted">
            Trust Threshold (\u03c4)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-[1.5px] rounded-full bg-red-500/60 block" />
          <span className="text-[10px] text-text-muted">
            Suppression Threshold (\u03c4\u209b)
          </span>
        </div>
      </div>
    </div>
  );
}
