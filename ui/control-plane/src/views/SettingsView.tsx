import { Upload } from "lucide-react";
import { CardPanel } from "../components/ui/CardPanel";
import type { Mode } from "../types/controlPlane";

interface SettingsViewProps {
  mode: Mode;
  setMode: (mode: Mode) => void;
  replayFileName: string;
  onOpenReplayLoader: () => void;
}

export function SettingsView({ mode, setMode, replayFileName, onOpenReplayLoader }: SettingsViewProps) {
  return (
    <CardPanel title="Settings" subtitle="Control plane mode and replay ingestion">
      <div className="space-y-3 text-xs">
        <div className="rounded border border-border bg-panelAlt px-3 py-2">
          <div className="mb-2 text-[10px] uppercase tracking-wide text-textMuted">Governance Data Mode</div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode("LIVE")}
              className={`rounded border px-3 py-1.5 ${mode === "LIVE" ? "border-accent bg-accent/20 text-[#c9ddff]" : "border-border text-textMuted"}`}
            >
              LIVE
            </button>
            <button
              type="button"
              onClick={() => setMode("REPLAY")}
              className={`rounded border px-3 py-1.5 ${mode === "REPLAY" ? "border-accent bg-accent/20 text-[#c9ddff]" : "border-border text-textMuted"}`}
            >
              REPLAY
            </button>
          </div>
        </div>

        <div className="rounded border border-border bg-panelAlt px-3 py-2">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-textMuted">Replay Source</div>
          <div className="mb-2 font-mono text-[11px] text-text">{replayFileName}</div>
          <button
            type="button"
            onClick={onOpenReplayLoader}
            className="inline-flex items-center gap-1 rounded border border-border bg-panel px-2.5 py-1.5 text-[11px] text-text"
          >
            <Upload size={12} /> Open Replay Loader
          </button>
        </div>
      </div>
    </CardPanel>
  );
}
