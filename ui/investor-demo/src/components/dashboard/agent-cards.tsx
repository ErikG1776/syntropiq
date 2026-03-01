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
      <div className="panel p-5">
        <h3 className="text-sm font-semibold mb-4">Agent Status</h3>
        <div className="flex items-center justify-center h-28 text-text-muted text-sm">
          Waiting for demo to start...
        </div>
      </div>
    );
  }

  return (
    <div className="panel p-5">
      <h3 className="text-sm font-semibold mb-4">Agent Status</h3>
      <div className="space-y-3">
        {domain.agentNames.map((agent) => {
          const status = getAgentStatus(agent, currentCycle);
          const trust = currentCycle.trust_scores[agent] ?? 0;
          const isDrift = agent === domain.driftAgent;

          const config = {
            active: {
              icon: ShieldCheck,
              label: "Active",
              color: "text-emerald-400",
              border: "border-emerald-500/20",
              barColor: "bg-emerald-500",
              bg: "",
            },
            suppressed: {
              icon: ShieldOff,
              label: "Suppressed",
              color: "text-red-400",
              border: "border-red-500/25",
              barColor: "bg-red-500",
              bg: "bg-red-500/[0.04]",
            },
            probation: {
              icon: ShieldAlert,
              label: "Probation",
              color: "text-amber-400",
              border: "border-amber-500/20",
              barColor: "bg-amber-500",
              bg: "bg-amber-500/[0.04]",
            },
            drifting: {
              icon: AlertTriangle,
              label: "Drifting",
              color: "text-amber-400",
              border: "border-amber-500/20",
              barColor: "bg-amber-500",
              bg: "bg-amber-500/[0.04]",
            },
          };

          const cfg = config[status];
          const StatusIcon = cfg.icon;

          return (
            <div
              key={agent}
              className={cn(
                "p-3.5 rounded-xl border transition-all duration-500",
                cfg.border,
                cfg.bg,
                status === "suppressed" && "pulse-danger"
              )}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <StatusIcon className={cn("w-4 h-4", cfg.color)} />
                  <span className="text-sm font-medium">
                    {getAgentDisplayName(agent)}
                  </span>
                  {isDrift && (
                    <span className="text-[9px] font-mono text-text-muted bg-white/5 px-1.5 py-0.5 rounded tracking-wider">
                      DRIFT TARGET
                    </span>
                  )}
                </div>
                <span className={cn("text-[11px] font-medium", cfg.color)}>
                  {cfg.label}
                </span>
              </div>

              {/* Trust bar */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      cfg.barColor
                    )}
                    style={{ width: `${Math.max(trust * 100, 0)}%` }}
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
