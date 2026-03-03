"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertTriangle, Loader2, Moon, Pause, Play, RefreshCw, Sun } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTheme } from "@/lib/use-theme";
import { useControlPlane } from "@/lib/control-plane-context";

const NAV_ITEMS = [
  { label: "Overview", href: "/demo/overview" },
  { label: "Events", href: "/demo/events" },
  { label: "Agents", href: "/demo/agents" },
  { label: "Cycles", href: "/demo/cycles" },
  { label: "Thresholds", href: "/demo/thresholds" },
  { label: "Impact", href: "/demo/impact" },
];
const STAGES = ["Baseline", "Drift", "Suppression", "Adaptation", "Recovery", "Stabilized"] as const;
const GOVERNANCE_LOOP = [
  "Observe",
  "Detect Drift",
  "Suppress",
  "Adapt Threshold",
  "Recover",
  "Certify",
] as const;

function getPhaseBadgeClasses(phase: string | undefined, circuitBreaker: boolean | undefined): string {
  const base =
    "rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide shadow-sm";
  if (!phase) return `${base} border-zinc-200 bg-zinc-100 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200`;
  if (circuitBreaker) return `${base} border-red-200 bg-red-100 text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300`;
  if (phase === "baseline") return `${base} border-blue-200 bg-blue-100 text-blue-700 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-300`;
  if (phase === "drift") return `${base} border-amber-200 bg-amber-100 text-amber-700 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300`;
  if (phase === "recovery") return `${base} border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-300`;
  return `${base} border-zinc-200 bg-zinc-100 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200`;
}

function getSystemStatus(
  phase: string | undefined,
  circuitBreaker: boolean | undefined,
  suppressedAgents: number
): "Healthy" | "Degraded" | "Suppressed" {
  if (!phase) return "Degraded";
  if (suppressedAgents > 0) return "Suppressed";
  if (phase === "drift" || circuitBreaker) return "Degraded";
  return "Healthy";
}

function getSystemStatusClasses(status: "Healthy" | "Degraded" | "Suppressed"): string {
  const base = "rounded-full px-3 py-1 text-xs font-semibold border shadow-sm";
  if (status === "Healthy") {
    return `${base} border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300`;
  }
  if (status === "Degraded") {
    return `${base} border-amber-200 bg-amber-100 text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300`;
  }
  return `${base} border-red-200 bg-red-100 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300`;
}

export function ControlShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const {
    run,
    loading,
    error,
    mode,
    setMode,
    cycles,
    currentCycle,
    playing,
    setPlaying,
    speed,
    setSpeed,
    loadRun,
    suppressedAgents,
    currentNewlySuppressed,
    currentNewlyRestored,
  } = useControlPlane();

  const status = getSystemStatus(currentCycle?.phase, currentCycle?.circuit_breaker, suppressedAgents);
  const stageIndex = (() => {
    if (!currentCycle) return 0;
    if (currentCycle.phase === "stabilized") return 5;
    if (currentCycle.phase === "recovery" || currentNewlyRestored.length > 0) return 4;
    if (suppressedAgents > 0 && currentNewlySuppressed.length === 0) return 3;
    if (currentNewlySuppressed.length > 0 || suppressedAgents > 0) return 2;
    if (currentCycle.phase === "drift") return 1;
    return 0;
  })();
  const loopIndex = (() => {
    if (!currentCycle) return 0;
    if (currentCycle.phase === "stabilized") return 5;
    if (currentCycle.phase === "recovery" || currentNewlyRestored.length > 0) return 4;
    if (suppressedAgents > 0 && currentNewlySuppressed.length === 0) return 3;
    if (currentNewlySuppressed.length > 0 || suppressedAgents > 0) return 2;
    if (currentCycle.phase === "drift") return 1;
    return 0;
  })();

  return (
    <div className="min-h-screen bg-slate-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100 transition-colors">
      <div className="flex min-h-screen">
        <aside className="w-64 shrink-0 border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-6 sticky top-0 h-screen">
          <div className="mb-8 px-2">
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Syntropiq</p>
            <h2 className="mt-1 text-lg font-semibold">Control Plane</h2>
          </div>
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex w-full items-center rounded-lg px-3 py-2 text-sm transition-colors",
                  pathname === item.href
                    ? "bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>

        <div className="flex-1 min-w-0">
          <header className="sticky top-0 z-10 border-b border-zinc-200 dark:border-zinc-800 bg-white/95 dark:bg-zinc-950/90 backdrop-blur">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-8 py-4 gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Enterprise Governance</p>
                <h1 className="mt-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                  Large Regional Bank — Fraud Detection Governance
                </h1>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                  Monitoring 120M annual transactions across 3 fraud models
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">Run ID: {run?.run_id ?? "--"}</p>
                  <Badge variant="outline" className={cn(getPhaseBadgeClasses(currentCycle?.phase, currentCycle?.circuit_breaker))}>
                    Phase: {currentCycle?.circuit_breaker ? "circuit_breaker" : currentCycle?.phase ?? "--"}
                  </Badge>
                  <Badge variant="outline" className="ml-2">
                    {mode === "live" ? "LIVE ENGINE" : "REPLAY"}
                  </Badge>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Badge className={cn(getSystemStatusClasses(status))}>{status}</Badge>

                <Button
                  size="sm"
                  className={cn(
                    "rounded-lg transition-all",
                    playing
                      ? "border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800"
                      : "bg-blue-600 text-white hover:bg-blue-500 shadow-sm"
                  )}
                  variant={playing ? "outline" : "default"}
                  onClick={() => setPlaying(!playing)}
                  disabled={cycles.length === 0}
                >
                  {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
                  {playing ? "Pause" : "Play"}
                </Button>

                <div className="flex items-center gap-1 rounded-lg border border-zinc-200 bg-zinc-100 p-1 dark:border-zinc-700 dark:bg-zinc-800">
                  {[1, 2, 3].map((itemSpeed) => (
                    <Button
                      key={itemSpeed}
                      size="xs"
                      className={cn(
                        "min-w-8 rounded-md",
                        speed === itemSpeed
                          ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-100"
                          : "bg-transparent text-zinc-600 hover:bg-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-700"
                      )}
                      variant={speed === itemSpeed ? "default" : "ghost"}
                      onClick={() => setSpeed(itemSpeed as 1 | 2 | 3)}
                    >
                      {itemSpeed}x
                    </Button>
                  ))}
                </div>

                <div className="flex items-center gap-1 rounded-lg border border-zinc-200 bg-zinc-100 p-1 dark:border-zinc-700 dark:bg-zinc-800">
                  <Button
                    size="xs"
                    variant={mode === "replay" ? "default" : "ghost"}
                    onClick={() => setMode("replay")}
                  >
                    Replay
                  </Button>
                  <Button
                    size="xs"
                    variant={mode === "live" ? "default" : "ghost"}
                    onClick={() => setMode("live")}
                  >
                    Live
                  </Button>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-lg border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
                  onClick={() => void loadRun()}
                  disabled={loading}
                >
                  {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
                  Load JSON
                </Button>

                <Button variant="outline" size="sm" onClick={toggleTheme}>
                  {theme === "light" ? <Moon className="size-4" /> : <Sun className="size-4" />}
                </Button>
              </div>
            </div>
            <div className="mx-auto max-w-7xl px-8 pb-4">
              <div className="grid grid-cols-6 gap-2">
                {STAGES.map((stage, index) => (
                  <div key={stage} className="space-y-1">
                    <p
                      className={cn(
                        "text-[11px] font-medium uppercase tracking-wide",
                        index <= stageIndex
                          ? "text-blue-700 dark:text-blue-300"
                          : "text-zinc-400 dark:text-zinc-500"
                      )}
                    >
                      {stage}
                    </p>
                    <div
                      className={cn(
                        "h-1.5 rounded-full",
                        index <= stageIndex
                          ? "bg-blue-600"
                          : "bg-zinc-200 dark:bg-zinc-800"
                      )}
                    />
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-lg border border-zinc-200 bg-white px-3 py-3 dark:border-zinc-800 dark:bg-zinc-900">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Governance Loop</p>
                <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-6">
                  {GOVERNANCE_LOOP.map((label, index) => (
                    <div key={label} className="space-y-1">
                      <p
                        className={cn(
                          "text-xs",
                          index < loopIndex && "text-zinc-700 dark:text-zinc-300",
                          index === loopIndex && "font-semibold text-blue-700 dark:text-blue-300",
                          index > loopIndex && "text-zinc-400 dark:text-zinc-500"
                        )}
                      >
                        {label}
                      </p>
                      <div className="h-1.5 rounded-full bg-zinc-200 dark:bg-zinc-800">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            index < loopIndex && "bg-blue-300 dark:bg-blue-700",
                            index === loopIndex && "bg-blue-600",
                            index > loopIndex && "w-0"
                          )}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </header>

          <main className="mx-auto max-w-7xl px-8 py-8">
            {error && (
              <div className="mb-6 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                <AlertTriangle className="size-4" />
                {error}
              </div>
            )}
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
