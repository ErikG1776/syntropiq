import type { GovernanceEvent } from "../../types/controlPlane";
import { CardPanel } from "../ui/CardPanel";
import { Badge, eventTone } from "../ui/Badge";
import { formatTimestamp } from "../../lib/format";

interface GovernanceEventStreamProps {
  events: GovernanceEvent[];
  maxHeightClassName?: string;
  title?: string;
}

export function GovernanceEventStream({
  events,
  maxHeightClassName = "max-h-[370px]",
  title = "Governance Events",
}: GovernanceEventStreamProps) {
  return (
    <CardPanel title={title} subtitle="Realtime policy and anomaly stream" className="h-full">
      <div className={`${maxHeightClassName} space-y-1 overflow-y-auto pr-1`}>
        {events.map((event, idx) => (
          <div key={`${event.type}-${event.timestamp}-${idx}`} className="grid grid-cols-[82px_145px_120px_1fr] items-center gap-2 rounded border border-border bg-panelAlt/35 px-2 py-1.5 text-[11px]">
            <span className="font-mono text-textMuted">{formatTimestamp(event.timestamp)}</span>
            <Badge label={event.type} tone={eventTone(event.type)} />
            <span className="truncate font-mono text-text">{event.agent}</span>
            <span className="truncate text-textMuted">{event.message}</span>
          </div>
        ))}
      </div>
    </CardPanel>
  );
}
