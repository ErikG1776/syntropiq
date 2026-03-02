"use client";

import { cn } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { CycleData, DomainConfig } from "@/lib/demo-data";
import { getAgentDisplayName, getAgentStatus } from "@/lib/demo-data";
import { ShieldCheck, ShieldOff, ShieldAlert, AlertTriangle } from "lucide-react";

interface AgentCardsProps {
  currentCycle: CycleData | null;
  domain: DomainConfig;
}

const statusConfig = {
  active: {
    icon: ShieldCheck,
    label: "Active",
    badge: "success" as const,
    barColor: "bg-success",
  },
  suppressed: {
    icon: ShieldOff,
    label: "Suppressed",
    badge: "destructive" as const,
    barColor: "bg-destructive",
  },
  probation: {
    icon: ShieldAlert,
    label: "Probation",
    badge: "warning" as const,
    barColor: "bg-warning",
  },
  drifting: {
    icon: AlertTriangle,
    label: "Drifting",
    badge: "warning" as const,
    barColor: "bg-warning",
  },
};

export function AgentCards({ currentCycle, domain }: AgentCardsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!currentCycle ? (
          <div className="flex items-center justify-center h-28 text-muted-foreground text-sm">
            Waiting for demo...
          </div>
        ) : (
          domain.agentNames.map((agent) => {
            const status = getAgentStatus(agent, currentCycle);
            const trust = currentCycle.trust_scores[agent] ?? 0;
            const isDrift = agent === domain.driftAgent;
            const cfg = statusConfig[status];
            const StatusIcon = cfg.icon;

            return (
              <div
                key={agent}
                className={cn(
                  "p-3 rounded-lg border transition-all duration-500",
                  status === "suppressed"
                    ? "border-destructive/20 bg-destructive/[0.03] pulse-danger"
                    : status === "probation"
                      ? "border-warning/20 bg-warning/[0.03]"
                      : "border-border"
                )}
              >
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-2">
                    <StatusIcon className={cn("w-3.5 h-3.5", {
                      "text-success": status === "active",
                      "text-destructive": status === "suppressed",
                      "text-warning": status === "probation" || status === "drifting",
                    })} />
                    <span className="text-sm font-medium">
                      {getAgentDisplayName(agent)}
                    </span>
                    {isDrift && (
                      <Badge variant="outline" className="text-[9px] py-0">
                        DRIFT TARGET
                      </Badge>
                    )}
                  </div>
                  <Badge variant={cfg.badge}>{cfg.label}</Badge>
                </div>

                {/* Trust bar */}
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-700",
                        cfg.barColor
                      )}
                      style={{ width: `${Math.max(trust * 100, 0)}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground tabular-nums w-12 text-right">
                    {trust.toFixed(3)}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
