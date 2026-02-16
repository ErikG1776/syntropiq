import { Badge } from "../ui/Badge";

interface CycleTimelineBarProps {
  currentCycle: number;
  totalCycles: number;
  suppressionCycle: number | null;
  onCycleSelect: (cycle: number) => void;
  onJumpSuppression: () => void;
}

export function CycleTimelineBar({
  currentCycle,
  totalCycles,
  suppressionCycle,
  onCycleSelect,
  onJumpSuppression,
}: CycleTimelineBarProps) {
  return (
    <section className="rounded border border-border bg-panel px-3 py-2 shadow-panel">
      <div className="mb-2 flex items-center justify-between text-[11px] text-textMuted">
        <span>Replay Timeline</span>
        <div className="flex items-center gap-2">
          <span className="font-mono">Cycle {currentCycle} / {totalCycles}</span>
          {suppressionCycle ? <Badge label={`Suppression @ ${suppressionCycle}`} tone="danger" /> : null}
          <button
            type="button"
            onClick={onJumpSuppression}
            className="rounded border border-danger/50 bg-danger/10 px-2 py-1 text-[10px] uppercase tracking-wide text-[#ff7b72]"
          >
            Jump to Suppression
          </button>
        </div>
      </div>

      <input
        type="range"
        min={1}
        max={Math.max(1, totalCycles)}
        value={Math.min(currentCycle, totalCycles)}
        onChange={(event) => onCycleSelect(Number(event.target.value))}
        className="w-full accent-accent"
      />

      <div className="mt-2 flex h-2 w-full overflow-hidden rounded bg-panelAlt">
        {Array.from({ length: totalCycles }).map((_, idx) => {
          const cycle = idx + 1;
          const current = cycle === currentCycle;
          const suppression = suppressionCycle === cycle;
          return (
            <div
              key={cycle}
              className={`h-full flex-1 border-r border-bg last:border-r-0 ${
                current ? "bg-accent" : suppression ? "bg-danger" : "bg-border"
              }`}
            />
          );
        })}
      </div>

      <div className="mt-1 flex justify-between text-[10px] text-textMuted">
        <span>Cycle 1</span>
        <span>Cycle {totalCycles}</span>
      </div>
    </section>
  );
}
