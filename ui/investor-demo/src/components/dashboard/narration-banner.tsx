"use client";

import { cn } from "@/lib/utils";
import type { CycleData, DomainConfig, GovernanceEvent } from "@/lib/demo-data";
import {
  Activity,
  AlertTriangle,
  ShieldOff,
  ShieldCheck,
  Zap,
} from "lucide-react";

function getNarration(
  currentCycle: CycleData | null,
  events: GovernanceEvent[],
  domain: DomainConfig
): {
  text: string;
  severity: "info" | "warning" | "danger" | "success";
  icon: typeof Activity;
} {
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
      text: `Agent suppressed \u2014 ${domain.driftAgent.replace(/_/g, " ")} removed from active duty. Trust dropped below governance threshold.`,
      severity: "danger",
      icon: ShieldOff,
    };
  }

  const restoration = cycleEvents.find((e) => e.type === "agent_restored");
  if (restoration) {
    return {
      text: `Agent restored \u2014 ${restoration.agent?.replace(/_/g, " ")} completed probation and returned to active service.`,
      severity: "success",
      icon: ShieldCheck,
    };
  }

  const drift = cycleEvents.find((e) => e.type === "drift_detected");
  if (drift) {
    return {
      text: `Drift detected \u2014 ${domain.driftAgent.replace(/_/g, " ")} showing anomalous trust trajectory. Monitoring intensified.`,
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
    return {
      text: "Ramp-up phase \u2014 all agents building trust history on mixed workload",
      severity: "info",
      icon: Activity,
    };
  }
  if (phase.includes("STRESS")) {
    return {
      text: "High-risk traffic entering system \u2014 governance monitoring at maximum sensitivity",
      severity: "warning",
      icon: AlertTriangle,
    };
  }
  if (phase.includes("RECOVERY")) {
    return {
      text: "Recovery phase \u2014 low-risk workload allowing agent rehabilitation",
      severity: "success",
      icon: ShieldCheck,
    };
  }

  return {
    text: "Steady state \u2014 governance maintaining optimal agent routing",
    severity: "info",
    icon: Activity,
  };
}

const severityStyles = {
  info: "bg-blue-500/[0.06] border-blue-500/15 text-blue-300",
  warning: "bg-amber-500/[0.06] border-amber-500/15 text-amber-300",
  danger: "bg-red-500/[0.06] border-red-500/15 text-red-300",
  success: "bg-emerald-500/[0.06] border-emerald-500/15 text-emerald-300",
};

const severityDot = {
  info: "bg-blue-400",
  warning: "bg-amber-400",
  danger: "bg-red-400",
  success: "bg-emerald-400",
};

interface NarrationBannerProps {
  currentCycle: CycleData | null;
  events: GovernanceEvent[];
  domain: DomainConfig;
}

export function NarrationBanner({
  currentCycle,
  events,
  domain,
}: NarrationBannerProps) {
  const { text, severity, icon: Icon } = getNarration(
    currentCycle,
    events,
    domain
  );

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-5 py-3 rounded-xl border transition-all duration-500",
        severityStyles[severity]
      )}
    >
      <span
        className={cn(
          "w-2 h-2 rounded-full shrink-0",
          severityDot[severity],
          severity === "danger" && "animate-pulse"
        )}
      />
      <Icon className="w-4 h-4 shrink-0 opacity-70" />
      <span className="text-sm font-medium">{text}</span>
      {currentCycle && (
        <span className="ml-auto text-[10px] font-mono opacity-50 shrink-0">
          CYCLE {currentCycle.cycle}
        </span>
      )}
    </div>
  );
}
