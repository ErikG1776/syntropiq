"use client";

import { useEffect, useRef, useState } from "react";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";
import { Shield, TrendingUp, AlertTriangle, DollarSign } from "lucide-react";
import type { CumulativeStats } from "@/lib/demo-data";

function useAnimatedValue(target: number, duration = 800): number {
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
      // Ease out cubic
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
  trend?: "up" | "down" | "neutral";
  accent?: "cyan" | "emerald" | "rose" | "amber";
  pulse?: boolean;
}

function KpiCard({ label, value, icon, accent = "cyan", pulse }: KpiCardProps) {
  const accentStyles = {
    cyan: "border-cyan-500/20 bg-cyan-500/[0.03]",
    emerald: "border-emerald-500/20 bg-emerald-500/[0.03]",
    rose: "border-rose-500/20 bg-rose-500/[0.03]",
    amber: "border-amber-500/20 bg-amber-500/[0.03]",
  };

  const iconColors = {
    cyan: "text-cyan-400",
    emerald: "text-emerald-400",
    rose: "text-rose-400",
    amber: "text-amber-400",
  };

  return (
    <div
      className={cn(
        "glass-card p-5 transition-all duration-500 relative overflow-hidden",
        accentStyles[accent],
        pulse && "pulse-danger"
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
          {label}
        </span>
        <span className={cn("opacity-60", iconColors[accent])}>{icon}</span>
      </div>
      <div className="text-2xl font-bold tabular-nums tracking-tight">{value}</div>
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
        accent={stats.activeAgents < stats.totalAgents ? "rose" : "cyan"}
        pulse={stats.activeAgents < stats.totalAgents}
      />
      <KpiCard
        label={lossLabel}
        value={formatCurrency(animatedLoss)}
        icon={<AlertTriangle className="w-4 h-4" />}
        accent={animatedLoss > 0 ? "rose" : "emerald"}
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
