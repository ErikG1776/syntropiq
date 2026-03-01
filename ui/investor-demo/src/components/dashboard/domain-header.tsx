"use client";

import { cn } from "@/lib/utils";
import { DOMAINS, type DomainId } from "@/lib/demo-data";
import { ShieldAlert, Landmark, HeartPulse, Activity } from "lucide-react";
import Link from "next/link";

const domainIcons: Record<DomainId, typeof ShieldAlert> = {
  fraud: ShieldAlert,
  lending: Landmark,
  readmission: HeartPulse,
};

interface DomainHeaderProps {
  activeDomain: DomainId;
  onDomainChange: (domain: DomainId) => void;
}

export function DomainHeader({
  activeDomain,
  onDomainChange,
}: DomainHeaderProps) {
  return (
    <header className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-2.5 mr-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
            <Activity className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-base font-semibold tracking-tight">
            syntropiq
          </span>
        </Link>

        <div className="h-5 w-px bg-border" />

        {/* Domain tabs */}
        <div className="flex items-center gap-1 bg-surface rounded-xl p-1 border border-border">
          {(Object.keys(DOMAINS) as DomainId[]).map((id) => {
            const domain = DOMAINS[id];
            const Icon = domainIcons[id];
            const isActive = id === activeDomain;

            return (
              <button
                key={id}
                onClick={() => onDomainChange(id)}
                className={cn(
                  "flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer",
                  isActive
                    ? "bg-white/[0.08] text-text-primary shadow-sm"
                    : "text-text-muted hover:text-text-secondary"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {domain.shortLabel}
              </button>
            );
          })}
        </div>
      </div>

      <div className="text-[10px] font-mono text-text-muted bg-surface px-3 py-1.5 rounded-full border border-border tracking-wider">
        DEMO
      </div>
    </header>
  );
}
