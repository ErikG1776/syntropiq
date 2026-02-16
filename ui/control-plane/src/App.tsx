import { Navigate, Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/layout/Sidebar";
import { TopBar } from "./components/layout/TopBar";
import { ReplayLoaderPanel } from "./components/replay/ReplayLoaderPanel";
import { Badge } from "./components/ui/Badge";
import { useControlPlaneData } from "./hooks/useControlPlaneData";
import { API_BASE_URL } from "./lib/api";
import { AgentsView } from "./views/AgentsView";
import { EventsView } from "./views/EventsView";
import { GovernanceCyclesView } from "./views/GovernanceCyclesView";
import { MutationView } from "./views/MutationView";
import { OverviewView } from "./views/OverviewView";
import { ReflectionsView } from "./views/ReflectionsView";
import { SettingsView } from "./views/SettingsView";

export default function App() {
  const { state, loading, error, isMock, mode, setMode, replay } = useControlPlaneData();

  return (
    <div className="min-h-screen bg-bg text-text">
      <TopBar
        state={state}
        mode={mode}
        setMode={setMode}
        onOpenReplayLoader={() => replay.setShowReplayLoader(true)}
      />

      <ReplayLoaderPanel
        open={replay.showReplayLoader}
        fileName={replay.replayFileName}
        onClose={() => replay.setShowReplayLoader(false)}
        onUpload={replay.uploadReplay}
      />

      <div className="grid min-h-[calc(100vh-104px)] grid-cols-[220px_1fr]">
        <Sidebar />

        <main className="space-y-3 px-4 py-3">
          <section className="flex flex-wrap items-center gap-2 text-[11px] text-textMuted">
            <Badge label={isMock ? "API fallback active" : "API connected"} tone={isMock ? "warn" : "ok"} />
            <span className="font-mono">{API_BASE_URL}</span>
            {loading ? <span className="font-mono">syncing...</span> : null}
            {error ? <span className="text-danger">{error}</span> : null}
            {mode === "REPLAY" ? <Badge label={`Replay File: ${state.replayFileName}`} tone="accent" /> : null}
          </section>

          <Routes>
            <Route path="/" element={<OverviewView state={state} replay={replay} />} />
            <Route path="/agents" element={<AgentsView state={state} />} />
            <Route path="/governance-cycles" element={<GovernanceCyclesView state={state} />} />
            <Route path="/events" element={<EventsView state={state} />} />
            <Route path="/mutation" element={<MutationView state={state} />} />
            <Route path="/reflections" element={<ReflectionsView state={state} />} />
            <Route
              path="/settings"
              element={
                <SettingsView
                  mode={mode}
                  setMode={setMode}
                  replayFileName={replay.replayFileName}
                  onOpenReplayLoader={() => replay.setShowReplayLoader(true)}
                />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
