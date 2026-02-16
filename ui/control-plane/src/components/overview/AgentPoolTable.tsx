import { MoreHorizontal, TriangleAlert } from "lucide-react";
import type { AgentRow } from "../../types/controlPlane";
import { DataTable } from "../ui/DataTable";
import { Badge, statusTone } from "../ui/Badge";
import { CardPanel } from "../ui/CardPanel";

interface AgentPoolTableProps {
  agents: AgentRow[];
  title?: string;
  subtitle?: string;
}

function trustBarColor(status: AgentRow["status"]): string {
  if (status === "SUPPRESSED") return "bg-danger";
  if (status === "DRIFTING") return "bg-warn";
  return "bg-ok";
}

export function AgentPoolTable({
  agents,
  title = "Agent Pool",
  subtitle = "Trust-sorted active decision agents",
}: AgentPoolTableProps) {
  return (
    <CardPanel
      title={title}
      subtitle={subtitle}
      className="h-full"
      actions={<span className="text-[10px] uppercase tracking-wide text-textMuted">sorted by trust</span>}
    >
      <DataTable columns={["Agent", "Trust", "Status", "Drift", "Last Seen", "Tasks", "Actions"]}>
        {agents.map((agent) => (
          <tr
            key={agent.name}
            className={`odd:bg-panel even:bg-panelAlt/40 hover:bg-panelAlt/60 ${agent.executionBlocked ? "bg-danger/10" : ""}`}
          >
            <td className="border-b border-border px-3 py-2 font-medium text-text">{agent.name}</td>
            <td className="border-b border-border px-3 py-2">
              <div className="flex items-center gap-2">
                <div className="h-2 w-28 overflow-hidden rounded bg-[#0f1722]">
                  <div
                    className={`h-full ${trustBarColor(agent.status)} ${agent.frozen ? "opacity-50" : ""}`}
                    style={{ width: `${Math.round(agent.trust * 100)}%` }}
                  />
                </div>
                <span className="font-mono text-[11px] text-text">{agent.trust.toFixed(3)}</span>
                {agent.frozen ? <span className="text-[10px] uppercase tracking-wide text-danger">frozen</span> : null}
              </div>
            </td>
            <td className="border-b border-border px-3 py-2">
              <Badge label={agent.status} tone={statusTone(agent.status)} />
              {agent.executionBlocked ? (
                <div className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-danger">Execution Blocked</div>
              ) : null}
            </td>
            <td className="border-b border-border px-3 py-2 text-textMuted">
              {agent.drifting ? <TriangleAlert size={14} className="text-warn" /> : <span className="text-[11px]">-</span>}
            </td>
            <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-textMuted">{agent.lastSeen}</td>
            <td className="border-b border-border px-3 py-2 font-mono text-[11px] text-text">{agent.tasks}</td>
            <td className="border-b border-border px-3 py-2 text-textMuted">
              <button type="button" className="rounded p-1 hover:bg-panelAlt" aria-label={`Actions for ${agent.name}`}>
                <MoreHorizontal size={14} />
              </button>
            </td>
          </tr>
        ))}
      </DataTable>
    </CardPanel>
  );
}
