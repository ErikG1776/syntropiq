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
  const reductionPct =
    withoutSyntropiq > 0
      ? ((prevented / withoutSyntropiq) * 100).toFixed(0)
      : "0";

  return (
    <div className="panel p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold mb-0.5">Governance Impact</h3>
        <p className="text-[11px] text-text-muted">
          Projected vs actual {lossLabel.toLowerCase()}
        </p>
      </div>

      <div className="space-y-3">
        {/* Without */}
        <div className="flex items-center justify-between py-2.5 px-3 rounded-xl border border-red-500/10 bg-red-500/[0.03]">
          <div className="flex items-center gap-2">
            <ShieldOff className="w-3.5 h-3.5 text-red-400 opacity-70" />
            <span className="text-xs text-text-secondary">
              Without governance
            </span>
          </div>
          <span className="text-sm font-bold text-red-400 tabular-nums">
            {formatCurrency(withoutSyntropiq)}
          </span>
        </div>

        {/* With */}
        <div className="flex items-center justify-between py-2.5 px-3 rounded-xl border border-emerald-500/10 bg-emerald-500/[0.03]">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 opacity-70" />
            <span className="text-xs text-text-secondary">
              With Syntropiq
            </span>
          </div>
          <span className="text-sm font-bold text-emerald-400 tabular-nums">
            {formatCurrency(withSyntropiq)}
          </span>
        </div>

        {/* Impact */}
        <div
          className={cn(
            "text-center py-4 px-3 rounded-xl border",
            prevented > 0
              ? "border-blue-500/15 bg-blue-500/[0.04]"
              : "border-border bg-white/[0.02]"
          )}
        >
          <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block mb-1">
            Losses Prevented
          </span>
          <span className="text-3xl font-extrabold text-blue-400 tabular-nums block">
            {formatCurrency(prevented)}
          </span>
          {prevented > 0 && (
            <span className="text-xs text-blue-400/60 mt-1 block">
              {reductionPct}% reduction
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
