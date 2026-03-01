"use client";

import { cn } from "@/lib/utils";
import type { CycleData, DomainConfig } from "@/lib/demo-data";
import { getAgentDisplayName, getAgentStatus } from "@/lib/demo-data";
import { ShieldCheck, ShieldOff, ShieldAlert, AlertTriangle } from "lucide-react";

interface AgentCardsProps {
  currentCycle: CycleData | null;
  domain: DomainConfig;
}

export function AgentCards({ currentCycle, domain }: AgentCardsProps) {
  if (!currentCycle) {
    return (
      <div className="glass-card p-5">
        <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider mb-4">
          Agent Pool
        </h3>
        <div className="flex items-center justify-center h-32 text-text-muted text-sm">
          Waiting for demo to start...
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider mb-4">
        Agent Pool
      </h3>
      <div className="space-y-3">
        {domain.agentNames.map((agent) => {
          const status = getAgentStatus(agent, currentCycle);
          const trust = currentCycle.trust_scores[agent] ?? 0;
          const isDrift = agent === domain.driftAgent;

          const statusConfig = {
            active: {
              icon: ShieldCheck,
              label: "Active",
              color: "text-emerald-400",
              bg: "bg-emerald-400/10",
              border: "border-emerald-500/20",
              barColor: "bg-emerald-400",
            },
            suppressed: {
              icon: ShieldOff,
              label: "Suppressed",
              color: "text-rose-400",
              bg: "bg-rose-400/10",
              border: "border-rose-500/30",
              barColor: "bg-rose-400",
            },
            probation: {
              icon: ShieldAlert,
              label: "Probation",
              color: "text-amber-400",
              bg: "bg-amber-400/10",
              border: "border-amber-500/20",
              barColor: "bg-amber-400",
            },
            drifting: {
              icon: AlertTriangle,
              label: "Drifting",
              color: "text-amber-400",
              bg: "bg-amber-400/10",
              border: "border-amber-500/20",
              barColor: "bg-amber-400",
            },
          };

          const config = statusConfig[status];
          const StatusIcon = config.icon;

          return (
            <div
              key={agent}
              className={cn(
                "p-3 rounded-xl border transition-all duration-500",
                config.bg,
                config.border,
                status === "suppressed" && "pulse-danger"
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <StatusIcon className={cn("w-4 h-4", config.color)} />
                  <span className="text-sm font-medium">
                    {getAgentDisplayName(agent)}
                  </span>
                  {isDrift && (
                    <span className="text-[10px] font-mono text-text-muted bg-white/5 px-1.5 py-0.5 rounded">
                      DRIFT TARGET
                    </span>
                  )}
                </div>
                <span className={cn("text-xs font-medium", config.color)}>
                  {config.label}
                </span>
              </div>

              {/* Trust bar */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      config.barColor
                    )}
                    style={{ width: `${trust * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-text-secondary tabular-nums w-12 text-right">
                  {trust.toFixed(3)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
