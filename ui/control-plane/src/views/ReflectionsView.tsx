import type { ControlPlaneState } from "../types/controlPlane";
import { CardPanel } from "../components/ui/CardPanel";

interface ReflectionsViewProps {
  state: ControlPlaneState;
}

export function ReflectionsView({ state }: ReflectionsViewProps) {
  return (
    <CardPanel title="Reflections" subtitle="Governance reflection feed">
      <div className="space-y-2">
        {state.reflections.length === 0 ? (
          <div className="rounded border border-border bg-panelAlt px-3 py-2 text-xs text-textMuted">
            Replay mode uses timeline-grounded events. Switch to LIVE to inspect reflection feed.
          </div>
        ) : (
          state.reflections.map((item, index) => (
            <div key={`${item.timestamp}-${index}`} className="rounded border border-border bg-panelAlt px-3 py-2">
              <div className="mb-1 text-[10px] uppercase tracking-wide text-textMuted">
                Constraint Score {item.constraint_score} | {new Date(item.timestamp).toLocaleString()}
              </div>
              <div className="text-xs text-text">{item.reflection_text}</div>
            </div>
          ))
        )}
      </div>
    </CardPanel>
  );
}
