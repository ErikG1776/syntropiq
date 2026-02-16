interface MetricChipProps {
  label: string;
  value: string;
  alert?: boolean;
}

export function MetricChip({ label, value, alert = false }: MetricChipProps) {
  return (
    <div className={`rounded border px-2.5 py-1 ${alert ? "border-danger/60 bg-danger/10" : "border-border bg-panelAlt"}`}>
      <div className="text-[10px] uppercase tracking-wide text-textMuted">{label}</div>
      <div className={`font-mono text-xs ${alert ? "text-[#ff7b72]" : "text-text"}`}>{value}</div>
    </div>
  );
}
