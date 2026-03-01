"use client";

import { useEffect, useRef, useState } from "react";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";
import { Shield, TrendingUp, AlertTriangle, DollarSign } from "lucide-react";
import type { CumulativeStats } from "@/lib/demo-data";

function useAnimatedValue(target: number, duration = 600): number {
  const [value, setValue] = useState(0);
  const prevRef = useRef(0);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const start = prevRef.current;
    const diff = target - start;
    if (Math.abs(diff) < 0.001) return;

    const startTime = performance.now();

    function animate(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + diff * eased;
      setValue(current);

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      } else {
        prevRef.current = target;
      }
    }

    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration]);

  return value;
}

interface KpiCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  accent?: "blue" | "emerald" | "red" | "amber";
  alert?: boolean;
}

function KpiCard({ label, value, icon, accent = "blue", alert }: KpiCardProps) {
  const borderAccent = {
    blue: "border-blue-500/15",
    emerald: "border-emerald-500/15",
    red: "border-red-500/15",
    amber: "border-amber-500/15",
  };

  const iconColor = {
    blue: "text-blue-400",
    emerald: "text-emerald-400",
    red: "text-red-400",
    amber: "text-amber-400",
  };

  return (
    <div
      className={cn(
        "panel px-5 py-4 transition-all duration-500",
        borderAccent[accent],
        alert && "pulse-danger"
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider">
          {label}
        </span>
        <span className={cn("opacity-50", iconColor[accent])}>{icon}</span>
      </div>
      <div className="text-2xl font-bold tabular-nums tracking-tight">
        {value}
      </div>
    </div>
  );
}

interface KpiStripProps {
  stats: CumulativeStats;
  lossLabel: string;
}

export function KpiStrip({ stats, lossLabel }: KpiStripProps) {
  const animatedSuccessRate = useAnimatedValue(stats.successRate);
  const animatedLoss = useAnimatedValue(stats.totalLoss);
  const animatedPrevented = useAnimatedValue(stats.lossePrevented);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <KpiCard
        label="Success Rate"
        value={formatPercent(animatedSuccessRate)}
        icon={<TrendingUp className="w-4 h-4" />}
        accent="emerald"
      />
      <KpiCard
        label="Active Agents"
        value={`${stats.activeAgents} / ${stats.totalAgents}`}
        icon={<Shield className="w-4 h-4" />}
        accent={stats.activeAgents < stats.totalAgents ? "red" : "blue"}
        alert={stats.activeAgents < stats.totalAgents}
      />
      <KpiCard
        label={lossLabel}
        value={formatCurrency(animatedLoss)}
        icon={<AlertTriangle className="w-4 h-4" />}
        accent={animatedLoss > 0 ? "red" : "emerald"}
      />
      <KpiCard
        label="Losses Prevented"
        value={formatCurrency(animatedPrevented)}
        icon={<DollarSign className="w-4 h-4" />}
        accent="emerald"
      />
    </div>
  );
}
