import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CardPanel } from "../ui/CardPanel";
import type { ThresholdPoint } from "../../types/controlPlane";

interface ThresholdChartProps {
  title: string;
  data: ThresholdPoint[];
  dataKey: "trust" | "suppression";
  stroke: string;
}

export function ThresholdChart({ title, data, dataKey, stroke }: ThresholdChartProps) {
  return (
    <CardPanel title={title} subtitle="Rolling governance threshold history">
      <div className="h-[180px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ left: -14, right: 8, top: 5, bottom: 0 }}>
            <CartesianGrid stroke="#2a3442" strokeDasharray="3 3" />
            <XAxis
              dataKey="cycle"
              tick={{ fill: "#8d98a7", fontSize: 10 }}
              interval="preserveStartEnd"
              minTickGap={20}
            />
            <YAxis domain={[0.5, 1]} tick={{ fill: "#8d98a7", fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                background: "#151b23",
                border: "1px solid #2a3442",
                color: "#d5dee8",
                fontSize: 11,
              }}
            />
            <Line type="monotone" dataKey={dataKey} stroke={stroke} strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </CardPanel>
  );
}
