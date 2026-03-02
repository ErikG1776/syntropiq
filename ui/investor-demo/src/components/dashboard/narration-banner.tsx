"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { CycleData, DomainConfig, GovernanceEvent } from "@/lib/demo-data";
import {
  Activity,
  AlertTriangle,
  ShieldOff,
  ShieldCheck,
  Zap,
} from "lucide-react";

type Severity = "info" | "warning" | "danger" | "success";

function getNarration(
  currentCycle: CycleData | null,
  events: GovernanceEvent[],
  domain: DomainConfig
): { text: string; severity: Severity; icon: typeof Activity } {
  if (!currentCycle) {
    return {
      text: "Press play to begin the governance simulation",
      severity: "info",
      icon: Activity,
    };
  }

  const cycleEvents = events.filter((e) => e.cycle === currentCycle.cycle);

  const suppression = cycleEvents.find((e) => e.type === "agent_suppressed");
  if (suppression) {
    return {
      text: `Agent suppressed \u2014 ${domain.driftAgent.replace(/_/g, " ")} removed from active duty. Trust dropped below threshold.`,
      severity: "danger",
      icon: ShieldOff,
    };
  }

  const restoration = cycleEvents.find((e) => e.type === "agent_restored");
  if (restoration) {
    return {
      text: `Agent restored \u2014 ${(restoration.agent ?? "").replace(/_/g, " ")} completed probation and returned to active service.`,
      severity: "success",
      icon: ShieldCheck,
    };
  }

  const drift = cycleEvents.find((e) => e.type === "drift_detected");
  if (drift) {
    return {
      text: `Drift detected \u2014 ${domain.driftAgent.replace(/_/g, " ")} showing anomalous trust trajectory.`,
      severity: "warning",
      icon: AlertTriangle,
    };
  }

  const loss = cycleEvents.find((e) => e.type === "loss_detected");
  if (loss) {
    return { text: loss.message, severity: "danger", icon: AlertTriangle };
  }

  const mutation = cycleEvents.find((e) => e.type === "threshold_mutated");
  if (mutation) {
    return { text: mutation.message, severity: "info", icon: Zap };
  }

  const phase = currentCycle.phase;
  if (phase.includes("RAMP")) {
    return { text: "Ramp-up \u2014 agents building trust history on mixed workload", severity: "info", icon: Activity };
  }
  if (phase.includes("STRESS")) {
    return { text: "Stress phase \u2014 high-risk traffic entering system", severity: "warning", icon: AlertTriangle };
  }
  if (phase.includes("RECOVERY")) {
    return { text: "Recovery \u2014 low-risk workload allowing agent rehabilitation", severity: "success", icon: ShieldCheck };
  }

  return { text: "Steady state \u2014 governance maintaining optimal routing", severity: "info", icon: Activity };
}

const severityBadge: Record<Severity, "info" | "warning" | "destructive" | "success"> = {
  info: "info",
  warning: "warning",
  danger: "destructive",
  success: "success",
};

const severityBorder: Record<Severity, string> = {
  info: "border-info/15",
  warning: "border-warning/15",
  danger: "border-destructive/15",
  success: "border-success/15",
};

const severityBg: Record<Severity, string> = {
  info: "bg-info/[0.04]",
  warning: "bg-warning/[0.04]",
  danger: "bg-destructive/[0.04]",
  success: "bg-success/[0.04]",
};

interface NarrationBannerProps {
  currentCycle: CycleData | null;
  events: GovernanceEvent[];
  domain: DomainConfig;
}

export function NarrationBanner({ currentCycle, events, domain }: NarrationBannerProps) {
  const { text, severity, icon: Icon } = getNarration(currentCycle, events, domain);

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-500",
        severityBorder[severity],
        severityBg[severity]
      )}
    >
      <Badge variant={severityBadge[severity]} className="shrink-0">
        <Icon className="w-3 h-3 mr-1" />
        {severity === "danger" ? "Alert" : severity === "warning" ? "Warning" : severity === "success" ? "OK" : "Info"}
      </Badge>
      <span className="text-sm text-foreground">{text}</span>
      {currentCycle && (
        <span className="ml-auto text-[10px] font-mono text-muted-foreground shrink-0">
          Cycle {currentCycle.cycle}
        </span>
      )}
    </div>
  );
}
