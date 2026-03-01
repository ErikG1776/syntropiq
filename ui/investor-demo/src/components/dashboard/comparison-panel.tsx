"use client";

import { cn, formatCurrency } from "@/lib/utils";
import type { CumulativeStats } from "@/lib/demo-data";
import { ShieldCheck, ShieldOff } from "lucide-react";

interface ComparisonPanelProps {
  stats: CumulativeStats;
  lossLabel: string;
}

export function ComparisonPanel({ stats, lossLabel }: ComparisonPanelProps) {
  const withSyntropiq = stats.totalLoss;
  const withoutSyntropiq = stats.totalLossWithout;
  const prevented = stats.lossePrevented;

  // Percentage reduction
  const reductionPct =
    withoutSyntropiq > 0
      ? ((prevented / withoutSyntropiq) * 100).toFixed(0)
      : "0";

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider mb-5">
        Governance Impact
      </h3>

      <div className="space-y-4">
        {/* Without Syntropiq */}
        <div className="p-3 rounded-xl bg-rose-500/5 border border-rose-500/15">
          <div className="flex items-center gap-2 mb-2">
            <ShieldOff className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-xs font-medium text-rose-400">
              Without Governance
            </span>
          </div>
          <div className="text-xl font-bold text-rose-400 tabular-nums">
            {formatCurrency(withoutSyntropiq)}
          </div>
          <p className="text-[10px] text-text-muted mt-1">
            Projected {lossLabel.toLowerCase()} without intervention
          </p>
        </div>

        {/* With Syntropiq */}
        <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/15">
          <div className="flex items-center gap-2 mb-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-xs font-medium text-emerald-400">
              With Syntropiq
            </span>
          </div>
          <div className="text-xl font-bold text-emerald-400 tabular-nums">
            {formatCurrency(withSyntropiq)}
          </div>
          <p className="text-[10px] text-text-muted mt-1">
            Actual {lossLabel.toLowerCase()} with governance
          </p>
        </div>

        {/* Divider with impact */}
        <div
          className={cn(
            "text-center p-3 rounded-xl border",
            prevented > 0
              ? "bg-cyan-500/5 border-cyan-500/20"
              : "bg-white/[0.02] border-border"
          )}
        >
          <span className="text-xs text-text-muted block mb-1">
            Losses Prevented
          </span>
          <span className="text-2xl font-bold text-cyan-400 tabular-nums">
            {formatCurrency(prevented)}
          </span>
          {prevented > 0 && (
            <span className="block text-xs text-cyan-400/70 mt-1">
              {reductionPct}% reduction
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
