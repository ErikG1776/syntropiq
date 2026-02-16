import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ControlPlaneState } from "../types/controlPlane";
import { AgentPoolTable } from "../components/overview/AgentPoolTable";
import { CardPanel } from "../components/ui/CardPanel";

interface AgentsViewProps {
  state: ControlPlaneState;
}

export function AgentsView({ state }: AgentsViewProps) {
  const agentKeys = Object.keys(state.agentHistory[0] ?? {}).filter((key) => key !== "cycle");
  const palette = ["#79c0ff", "#e3b341", "#7ee787", "#ff7b72", "#a5d6ff"];

  return (
    <>
      <CardPanel title="Agent Trust History" subtitle="Per-agent trust trajectory across governance cycles">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={state.agentHistory} margin={{ left: -18, right: 10, top: 8, bottom: 0 }}>
              <XAxis dataKey="cycle" tick={{ fill: "#8d98a7", fontSize: 10 }} />
              <YAxis domain={[0, 1]} tick={{ fill: "#8d98a7", fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: "#151b23", border: "1px solid #2a3442", color: "#d5dee8", fontSize: 11 }}
              />
              {agentKeys.map((agent, index) => (
                <Line key={agent} dataKey={agent} stroke={palette[index % palette.length]} dot={false} strokeWidth={2} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardPanel>
      <AgentPoolTable agents={state.agents} title="Current Agent State" subtitle="Execution authority and trust posture" />
    </>
  );
}
