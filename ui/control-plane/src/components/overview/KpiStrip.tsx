import { formatCurrency, formatPercent } from "../../lib/format";
import type { KpiRow } from "../../types/controlPlane";

interface KpiStripProps {
  kpis: KpiRow;
  suppressionPulse?: boolean;
}

export function KpiStrip({ kpis, suppressionPulse = false }: KpiStripProps) {
  const items = [
    { label: "Prevented Delta ($)", value: formatCurrency(kpis.preventedDelta) },
    { label: "Drift Loss Before Suppression", value: formatCurrency(kpis.driftLossBeforeSuppression) },
    { label: "Drift Loss After Suppression", value: formatCurrency(kpis.driftLossAfterSuppression) },
    { label: "Overall Success Rate", value: formatPercent(kpis.overallSuccessRate) },
    { label: "Cycles Executed", value: `${kpis.cyclesExecuted}` },
  ];

  return (
    <section className="grid gap-2 md:grid-cols-3 xl:grid-cols-6">
      {items.map((item, idx) => (
        <div
          key={item.label}
          className={`rounded border border-border bg-panel px-3 py-2 shadow-panel ${
            idx === 0 ? "xl:col-span-2 border-accent/45 bg-accent/10" : ""
          } ${idx === 0 && suppressionPulse ? "kpi-pulse" : ""}`}
        >
          <div className="text-[10px] uppercase tracking-wide text-textMuted">{item.label}</div>
          <div className={`mt-1 font-mono text-text ${idx === 0 ? "text-2xl font-semibold" : "text-sm"}`}>{item.value}</div>
        </div>
      ))}
    </section>
  );
}
