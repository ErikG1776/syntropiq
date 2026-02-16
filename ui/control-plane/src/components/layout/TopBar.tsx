import { Search, Upload } from "lucide-react";
import { Badge } from "../ui/Badge";
import { MetricChip } from "../ui/MetricChip";
import type { ControlPlaneState, Environment, Mode } from "../../types/controlPlane";

interface TopBarProps {
  state: ControlPlaneState;
  mode: Mode;
  setMode: (mode: Mode) => void;
  onOpenReplayLoader: () => void;
}

const environment = (import.meta.env.VITE_ENVIRONMENT ?? "DEMO") as Environment;

export function TopBar({ state, mode, setMode, onOpenReplayLoader }: TopBarProps) {
  const suppressionActive = state.systemHealth === "SUPPRESSION ACTIVE";

  return (
    <header className="sticky top-0 z-30 space-y-2 border-b border-border bg-bg/95 px-4 py-2 backdrop-blur">
      <div className="grid grid-cols-[420px_1fr_760px] items-center gap-4">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-wide text-text">Syntropiq Trust Operating System</h1>
            <p className="text-[10px] uppercase tracking-wide text-textMuted">Autonomous Decision Governance</p>
            <p className="text-[10px] uppercase tracking-wide text-textMuted">Dataset: Lending Club (Demo Only)</p>
          </div>
          <Badge label={environment} tone={environment === "PROD" ? "danger" : environment === "STAGING" ? "warn" : "accent"} />
        </div>

        <label className="flex items-center gap-2 rounded border border-border bg-panel px-3 py-2 text-xs text-textMuted">
          <Search size={14} />
          <input
            className="w-full bg-transparent text-text outline-none placeholder:text-textMuted"
            placeholder="Search agents, cycles, or events"
            readOnly
          />
        </label>

        <div className="flex items-center justify-end gap-2 overflow-auto">
          <div className="flex items-center rounded border border-border bg-panelAlt p-0.5 text-[10px] uppercase tracking-wide">
            <button
              type="button"
              onClick={() => setMode("LIVE")}
              className={`rounded px-2.5 py-1 ${mode === "LIVE" ? "bg-accent text-white" : "text-textMuted"}`}
            >
              Mode: Live
            </button>
            <button
              type="button"
              onClick={() => setMode("REPLAY")}
              className={`rounded px-2.5 py-1 ${mode === "REPLAY" ? "bg-accent text-white" : "text-textMuted"}`}
            >
              Mode: Replay
            </button>
          </div>
          <button
            type="button"
            onClick={onOpenReplayLoader}
            className="inline-flex items-center gap-1 rounded border border-border bg-panelAlt px-2.5 py-1.5 text-[11px] text-text hover:bg-panel"
          >
            <Upload size={12} /> Replay Loader
          </button>
          <MetricChip label="Routing Mode" value={state.routingMode} />
          <MetricChip label="Trust Threshold" value={state.thresholds.trustThreshold.toFixed(2)} />
          <MetricChip label="Suppression Threshold" value={state.thresholds.suppressionThreshold.toFixed(2)} />
          <MetricChip label="Drift Delta" value={state.thresholds.driftDelta.toFixed(2)} />
          <MetricChip label="System Health" value={state.systemHealth} alert={suppressionActive} />
        </div>
      </div>

      <div className={`rounded border px-3 py-1.5 text-xs font-semibold tracking-wide ${suppressionActive ? "border-danger bg-danger/20 text-[#ff7b72]" : "border-ok/40 bg-ok/10 text-[#7ee787]"}`}>
        GOVERNANCE STATE: {suppressionActive ? "SUPPRESSION ACTIVE" : "HEALTHY"}
      </div>
    </header>
  );
}
