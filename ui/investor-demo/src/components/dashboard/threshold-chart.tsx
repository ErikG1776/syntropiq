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

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: number }) {
  if (!active || !payload) return null;
  return (
    <div className="glass-card p-3 text-xs">
      <p className="text-text-muted mb-2 font-mono">Cycle {label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2 mb-1">
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: p.color }}
          />
          <span className="text-text-secondary">
            {p.name === "trust_threshold" ? "Trust τ" : "Suppress τ_s"}
          </span>
          <span className="ml-auto font-mono font-medium tabular-nums">
            {p.value?.toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ThresholdChart({ thresholdHistory }: ThresholdChartProps) {
  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider mb-4">
        Threshold Evolution
      </h3>

      <ResponsiveContainer width="100%" height={180}>
        <AreaChart
          data={thresholdHistory}
          margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.04)"
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
          <Tooltip content={<CustomTooltip />} />

          <Area
            type="monotone"
            dataKey="suppression_threshold"
            stroke="#f43f5e"
            fill="rgba(244,63,94,0.05)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            animationDuration={400}
          />
          <Area
            type="monotone"
            dataKey="trust_threshold"
            stroke="#fbbf24"
            fill="rgba(251,191,36,0.05)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            animationDuration={400}
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="flex items-center justify-center gap-6 mt-3">
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-px bg-amber-400 block" style={{ borderTop: "1.5px dashed #fbbf24" }} />
          <span className="text-[10px] text-text-muted">Trust Threshold (τ)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-px bg-rose-400 block" style={{ borderTop: "1.5px dashed #f43f5e" }} />
          <span className="text-[10px] text-text-muted">Suppression Threshold (τ_s)</span>
        </div>
      </div>
    </div>
  );
}
