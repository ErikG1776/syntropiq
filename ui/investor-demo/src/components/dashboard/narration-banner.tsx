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
): { text: string; severity: "info" | "warning" | "danger" | "success"; icon: typeof Activity } {
  if (!currentCycle) {
    return {
      text: "Press play to begin the governance simulation",
      severity: "info",
      icon: Activity,
    };
  }

  // Get events for this cycle
  const cycleEvents = events.filter((e) => e.cycle === currentCycle.cycle);

  // Check for suppression
  const suppression = cycleEvents.find((e) => e.type === "agent_suppressed");
  if (suppression) {
    return {
      text: `AGENT SUPPRESSED — ${domain.driftAgent.replace(/_/g, " ")} removed from active duty. Trust dropped below governance threshold.`,
      severity: "danger",
      icon: ShieldOff,
    };
  }

  // Check for restoration
  const restoration = cycleEvents.find((e) => e.type === "agent_restored");
  if (restoration) {
    return {
      text: `AGENT RESTORED — ${restoration.agent?.replace(/_/g, " ")} completed probation and returned to active service.`,
      severity: "success",
      icon: ShieldCheck,
    };
  }

  // Check for drift
  const drift = cycleEvents.find((e) => e.type === "drift_detected");
  if (drift) {
    return {
      text: `DRIFT DETECTED — ${domain.driftAgent.replace(/_/g, " ")} showing anomalous trust trajectory. Governance monitoring intensified.`,
      severity: "warning",
      icon: AlertTriangle,
    };
  }

  // Check for losses
  const loss = cycleEvents.find((e) => e.type === "loss_detected");
  if (loss) {
    return {
      text: loss.message,
      severity: "danger",
      icon: AlertTriangle,
    };
  }

  // Check for threshold mutation
  const mutation = cycleEvents.find((e) => e.type === "threshold_mutated");
  if (mutation) {
    return {
      text: mutation.message.toUpperCase(),
      severity: "info",
      icon: Zap,
    };
  }

  // Default phase narration
  const phase = currentCycle.phase;
  if (phase.includes("RAMP")) {
    return {
      text: `System processing mixed workload — all agents building trust history`,
      severity: "info",
      icon: Activity,
    };
  }
  if (phase.includes("STRESS")) {
    return {
      text: `High-risk traffic entering system — governance monitoring at maximum sensitivity`,
      severity: "warning",
      icon: AlertTriangle,
    };
  }
  if (phase.includes("RECOVERY")) {
    return {
      text: `Recovery phase — low-risk workload allowing agent rehabilitation`,
      severity: "success",
      icon: ShieldCheck,
    };
  }

  return {
    text: `Steady state — governance maintaining optimal agent routing`,
    severity: "info",
    icon: Activity,
  };
}

const severityStyles = {
  info: "bg-cyan-500/[0.06] border-cyan-500/20 text-cyan-300",
  warning: "bg-amber-500/[0.06] border-amber-500/20 text-amber-300",
  danger: "bg-rose-500/[0.06] border-rose-500/20 text-rose-300",
  success: "bg-emerald-500/[0.06] border-emerald-500/20 text-emerald-300",
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
  const { text, severity, icon: Icon } = getNarration(currentCycle, events, domain);

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-5 py-3 rounded-xl border transition-all duration-500",
        severityStyles[severity]
      )}
    >
      <Icon className="w-4 h-4 shrink-0" />
      <span className="text-sm font-medium">{text}</span>
    </div>
  );
}
