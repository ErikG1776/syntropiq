import type { ReactNode } from "react";

interface CardPanelProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function CardPanel({ title, subtitle, children, actions, className = "" }: CardPanelProps) {
  return (
    <section className={`rounded-md border border-border bg-panel shadow-panel ${className}`}>
      <header className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div>
          <h2 className="text-sm font-semibold text-text">{title}</h2>
          {subtitle ? <p className="text-[11px] text-textMuted">{subtitle}</p> : null}
        </div>
        {actions}
      </header>
      <div className="p-3">{children}</div>
    </section>
  );
}
