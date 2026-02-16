import type { ControlPlaneState } from "../types/controlPlane";
import { CardPanel } from "../components/ui/CardPanel";
import { DataTable } from "../components/ui/DataTable";
import { ThresholdChart } from "../components/charts/ThresholdChart";

interface MutationViewProps {
  state: ControlPlaneState;
}

export function MutationView({ state }: MutationViewProps) {
  return (
    <>
      <section className="grid gap-3 xl:grid-cols-2">
        <ThresholdChart title="Trust Threshold (τ)" data={state.thresholdSeries} dataKey="trust" stroke="#79c0ff" />
        <ThresholdChart title="Suppression Threshold (τ_s)" data={state.thresholdSeries} dataKey="suppression" stroke="#f2cc60" />
      </section>
      <CardPanel title="Mutation History" subtitle="Threshold evolution over governance timeline">
        <DataTable columns={["Cycle", "Trust τ", "Suppression τ_s", "Drift Δ"]}>
          {state.thresholdSeries.map((point) => (
            <tr key={point.cycle} className="odd:bg-panel even:bg-panelAlt/40">
              <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{point.cycle}</td>
              <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{point.trust.toFixed(3)}</td>
              <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{point.suppression.toFixed(3)}</td>
              <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{point.drift.toFixed(3)}</td>
            </tr>
          ))}
        </DataTable>
      </CardPanel>
    </>
  );
}
