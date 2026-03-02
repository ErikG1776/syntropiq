"use client";

import { useEffect, useRef, useState } from "react";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, Shield, AlertTriangle, DollarSign } from "lucide-react";
import type { CumulativeStats, DomainConfig } from "@/lib/demo-data";
import { computeEnterpriseProjection } from "@/lib/enterprise-scaling";

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

interface KpiStripProps {
  stats: CumulativeStats;
  domain: DomainConfig;
}

export function KpiStrip({ stats, domain }: KpiStripProps) {
  const animatedSuccessRate = useAnimatedValue(stats.successRate);
  const projection = computeEnterpriseProjection(stats, domain);
  const animatedSavings = useAnimatedValue(projection.netAnnualSavings);

  const kpis = [
    {
      label: "Success Rate",
      value: formatPercent(animatedSuccessRate),
      icon: TrendingUp,
      iconColor: "text-success",
    },
    {
      label: "Active Agents",
      value: `${stats.activeAgents} / ${stats.totalAgents}`,
      icon: Shield,
      iconColor: stats.activeAgents < stats.totalAgents ? "text-destructive" : "text-primary",
    },
    {
      label: "Suppressions",
      value: `${stats.suppressionCycles}`,
      icon: AlertTriangle,
      iconColor: stats.suppressionCycles > 0 ? "text-warning" : "text-muted-foreground",
    },
    {
      label: "Est. Annual Savings",
      value: formatCurrency(animatedSavings),
      icon: DollarSign,
      iconColor: "text-success",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {kpis.map((kpi) => (
        <Card key={kpi.label}>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                {kpi.label}
              </span>
              <kpi.icon className={`w-4 h-4 ${kpi.iconColor} opacity-60`} />
            </div>
            <div className="text-2xl font-bold tabular-nums tracking-tight">
              {kpi.value}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
