import type { ControlPlaneState } from "../types/controlPlane";
import { CardPanel } from "../components/ui/CardPanel";
import { DataTable } from "../components/ui/DataTable";

interface GovernanceCyclesViewProps {
  state: ControlPlaneState;
}

export function GovernanceCyclesView({ state }: GovernanceCyclesViewProps) {
  return (
    <CardPanel title="Governance Cycles" subtitle="Cycle-level execution and suppression summary">
      <DataTable columns={["Cycle", "Phase", "Status", "Successes", "Failures", "Bad Approvals", "Potential Loss", "Suppressed"]}>
        {state.cycleSummaries.map((row) => (
          <tr key={row.cycle} className="odd:bg-panel even:bg-panelAlt/40">
            <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{row.cycle}</td>
            <td className="border-b border-border px-3 py-2 text-textMuted">{row.phase}</td>
            <td className="border-b border-border px-3 py-2 text-text">{row.status}</td>
            <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{row.successes}</td>
            <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{row.failures}</td>
            <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{row.badApprovals}</td>
            <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">${row.potentialLoss.toLocaleString()}</td>
            <td className="border-b border-border px-3 py-2 text-danger">{row.suppressedAgents.join(", ") || "-"}</td>
          </tr>
        ))}
      </DataTable>
    </CardPanel>
  );
}
