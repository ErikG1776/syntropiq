import { useRef } from "react";
import { Upload, X } from "lucide-react";

interface ReplayLoaderPanelProps {
  open: boolean;
  fileName: string;
  onClose: () => void;
  onUpload: (file: File) => Promise<void>;
}

export function ReplayLoaderPanel({ open, fileName, onClose, onUpload }: ReplayLoaderPanelProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 bg-black/60">
      <div className="absolute right-4 top-16 w-[440px] rounded-md border border-border bg-panel shadow-panel">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold text-text">Replay Loader</h3>
            <p className="text-[11px] text-textMuted">Upload demo_results.json from Lending Club governance demo</p>
          </div>
          <button type="button" onClick={onClose} className="rounded p-1 text-textMuted hover:bg-panelAlt">
            <X size={14} />
          </button>
        </header>

        <div className="space-y-3 px-4 py-3">
          <div className="rounded border border-border bg-panelAlt px-3 py-2 text-[11px] text-textMuted">
            Loaded file: <span className="font-mono text-text">{fileName}</span>
          </div>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="flex w-full items-center justify-center gap-2 rounded border border-accent/60 bg-accent/20 px-3 py-2 text-xs text-[#c9ddff]"
          >
            <Upload size={14} /> Upload demo_results.json
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              await onUpload(file);
              event.target.value = "";
            }}
          />
          <p className="text-[11px] text-textMuted">Replay duration is fixed to 25 seconds across full timeline.</p>
        </div>
      </div>
    </div>
  );
}
