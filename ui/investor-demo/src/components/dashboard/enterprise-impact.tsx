"use client";

import { formatCurrency } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, ShieldOff, TrendingDown } from "lucide-react";
import type { CumulativeStats, DomainConfig } from "@/lib/demo-data";
import { computeEnterpriseProjection } from "@/lib/enterprise-scaling";

interface EnterpriseImpactProps {
  stats: CumulativeStats;
  domain: DomainConfig;
}

export function EnterpriseImpact({ stats, domain }: EnterpriseImpactProps) {
  const projection = computeEnterpriseProjection(stats, domain);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Enterprise Impact</CardTitle>
            <CardDescription>Annualized projection at scale</CardDescription>
          </div>
          <Badge variant="outline" className="text-[9px]">
            {projection.volumeLabel}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Without */}
        <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-destructive/[0.04] border border-destructive/10">
          <div className="flex items-center gap-2">
            <ShieldOff className="w-3.5 h-3.5 text-destructive opacity-60" />
            <span className="text-xs text-muted-foreground">
              Without governance
            </span>
          </div>
          <span className="text-sm font-semibold text-destructive tabular-nums">
            {formatCurrency(projection.withoutGovernance)}
          </span>
        </div>

        {/* With */}
        <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-success/[0.04] border border-success/10">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-success opacity-60" />
            <span className="text-xs text-muted-foreground">
              With Syntropiq
            </span>
          </div>
          <span className="text-sm font-semibold text-success tabular-nums">
            {formatCurrency(projection.withSyntropiq)}
          </span>
        </div>

        {/* Net Savings */}
        <div className="text-center py-3 px-3 rounded-lg bg-primary/[0.04] border border-primary/10">
          <div className="flex items-center justify-center gap-1.5 mb-1">
            <TrendingDown className="w-3 h-3 text-primary opacity-60" />
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
              Net Annual Savings
            </span>
          </div>
          <span className="text-2xl font-bold text-primary tabular-nums block">
            {formatCurrency(projection.netAnnualSavings)}
          </span>
          {projection.reductionPct > 0 && (
            <span className="text-xs text-primary/60 mt-0.5 block">
              {projection.reductionPct.toFixed(0)}% risk reduction
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
