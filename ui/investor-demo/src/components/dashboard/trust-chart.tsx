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
} from "recharts";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import type { DomainConfig, CycleData } from "@/lib/demo-data";
import { getAgentDisplayName } from "@/lib/demo-data";

const AGENT_COLORS: Record<string, string> = {
  rule_engine: "#3b82f6",
  ml_scorer: "#8b5cf6",
  ensemble: "#ef4444",
  conservative: "#3b82f6",
  balanced: "#8b5cf6",
  growth: "#ef4444",
  predictive: "#8b5cf6",
  rapid_screen: "#ef4444",
};

function getAgentColor(agent: string): string {
  return AGENT_COLORS[agent] || "#64748b";
}

interface TrustChartProps {
  trustHistory: Array<{ cycle: number } & Record<string, number>>;
  domain: DomainConfig;
  currentCycle: CycleData | null;
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
            {getAgentDisplayName(p.name)}
          </span>
          <span className="ml-auto text-xs font-mono font-medium tabular-nums pl-4 text-foreground">
            {p.value?.toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function TrustChart({ trustHistory, domain, currentCycle }: TrustChartProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Agent Trust Trajectories</CardTitle>
            <CardDescription className="mt-1">
              Real-time trust scores across governance cycles
            </CardDescription>
          </div>
          <div className="flex items-center gap-5">
            {domain.agentNames.map((agent) => (
              <div key={agent} className="flex items-center gap-2">
                <span
                  className="w-3 h-[2px] rounded-full block"
                  style={{ backgroundColor: getAgentColor(agent) }}
                />
                <span className="text-[11px] text-muted-foreground">
                  {getAgentDisplayName(agent)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={380}>
          <LineChart
            data={trustHistory}
            margin={{ top: 8, right: 20, left: 0, bottom: 4 }}
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
            <Tooltip content={<ChartTooltip />} />

            {/* Threshold lines */}
            <ReferenceLine
              y={currentCycle?.trust_threshold ?? 0.78}
              stroke="#eab308"
              strokeDasharray="8 6"
              strokeWidth={1}
              strokeOpacity={0.5}
              label={{
                value: "\u03c4 trust",
                position: "right",
                style: { fontSize: 10, fill: "#eab308", opacity: 0.6 },
              }}
            />
            <ReferenceLine
              y={currentCycle?.suppression_threshold ?? 0.84}
              stroke="#ef4444"
              strokeDasharray="8 6"
              strokeWidth={1}
              strokeOpacity={0.35}
              label={{
                value: "\u03c4 suppress",
                position: "right",
                style: { fontSize: 10, fill: "#ef4444", opacity: 0.5 },
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
                  fill: "#020617",
                }}
                animationDuration={400}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
