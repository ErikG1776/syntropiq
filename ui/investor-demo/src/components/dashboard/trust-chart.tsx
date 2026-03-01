"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import type { DomainConfig, CycleData } from "@/lib/demo-data";

const AGENT_COLORS: Record<string, string> = {
  // Fraud
  rule_engine: "#22d3ee",
  ml_scorer: "#818cf8",
  ensemble: "#f43f5e",
  // Lending
  conservative: "#22d3ee",
  balanced: "#818cf8",
  growth: "#f43f5e",
  // Readmission
  predictive: "#818cf8",
  rapid_screen: "#f43f5e",
};

function getAgentColor(agent: string): string {
  return AGENT_COLORS[agent] || "#94a3b8";
}

interface TrustChartProps {
  trustHistory: Array<{ cycle: number } & Record<string, number>>;
  domain: DomainConfig;
  currentCycle: CycleData | null;
  suppressionRanges?: Array<{ start: number; end: number }>;
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
          <span className="text-text-secondary">{p.name}</span>
          <span className="ml-auto font-mono font-medium tabular-nums">
            {p.value?.toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function TrustChart({
  trustHistory,
  domain,
  currentCycle,
}: TrustChartProps) {
  const suppressionThreshold = currentCycle?.suppression_threshold ?? 0.84;

  // Find suppression ranges from data
  const supRanges: Array<{ start: number; end: number }> = [];
  let rangeStart: number | null = null;
  for (const point of trustHistory) {
    const hasSuppression = domain.agentNames.some(
      (a) => (point[a] ?? 1) < suppressionThreshold
    );
    if (hasSuppression && rangeStart === null) {
      rangeStart = point.cycle;
    } else if (!hasSuppression && rangeStart !== null) {
      supRanges.push({ start: rangeStart, end: point.cycle });
      rangeStart = null;
    }
  }
  if (rangeStart !== null && trustHistory.length > 0) {
    supRanges.push({
      start: rangeStart,
      end: trustHistory[trustHistory.length - 1].cycle,
    });
  }

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider">
          Agent Trust Trajectories
        </h3>
        <div className="flex items-center gap-4">
          {domain.agentNames.map((agent) => (
            <div key={agent} className="flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: getAgentColor(agent) }}
              />
              <span className="text-xs text-text-muted">
                {agent.replace(/_/g, " ")}
              </span>
            </div>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <LineChart
          data={trustHistory}
          margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
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
            tick={{ fontSize: 11, fill: "#64748b" }}
            label={{
              value: "Governance Cycle",
              position: "insideBottom",
              offset: -2,
              style: { fontSize: 11, fill: "#64748b" },
            }}
          />
          <YAxis
            domain={[0.5, 1.05]}
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickFormatter={(v: number) => v.toFixed(2)}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Suppression zones */}
          {supRanges.map((r, i) => (
            <ReferenceArea
              key={i}
              x1={r.start}
              x2={r.end}
              fill="rgba(244,63,94,0.06)"
              fillOpacity={1}
            />
          ))}

          {/* Threshold lines */}
          <ReferenceLine
            y={currentCycle?.trust_threshold ?? 0.78}
            stroke="#fbbf24"
            strokeDasharray="6 4"
            strokeWidth={1}
            label={{
              value: "τ trust",
              position: "right",
              style: { fontSize: 10, fill: "#fbbf24" },
            }}
          />
          <ReferenceLine
            y={suppressionThreshold}
            stroke="#f43f5e"
            strokeDasharray="6 4"
            strokeWidth={1}
            label={{
              value: "τ suppress",
              position: "right",
              style: { fontSize: 10, fill: "#f43f5e" },
            }}
          />

          {/* Agent trust lines */}
          {domain.agentNames.map((agent) => (
            <Line
              key={agent}
              type="monotone"
              dataKey={agent}
              stroke={getAgentColor(agent)}
              strokeWidth={agent === domain.driftAgent ? 2.5 : 1.5}
              dot={false}
              activeDot={{
                r: 4,
                stroke: getAgentColor(agent),
                strokeWidth: 2,
                fill: "#06080f",
              }}
              animationDuration={400}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
