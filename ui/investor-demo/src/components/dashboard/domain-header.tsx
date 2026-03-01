"use client";

import { cn } from "@/lib/utils";
import { DOMAINS, type DomainId } from "@/lib/demo-data";
import {
  ShieldAlert,
  Landmark,
  HeartPulse,
  Activity,
} from "lucide-react";
import Link from "next/link";

const domainIcons: Record<DomainId, typeof ShieldAlert> = {
  fraud: ShieldAlert,
  lending: Landmark,
  readmission: HeartPulse,
};

const domainColors: Record<DomainId, { active: string; inactive: string }> = {
  fraud: {
    active: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    inactive: "text-text-muted hover:text-rose-400/70 border-transparent hover:border-rose-500/15",
  },
  lending: {
    active: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
    inactive: "text-text-muted hover:text-cyan-400/70 border-transparent hover:border-cyan-500/15",
  },
  readmission: {
    active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    inactive: "text-text-muted hover:text-emerald-400/70 border-transparent hover:border-emerald-500/15",
  },
};

interface DomainHeaderProps {
  activeDomain: DomainId;
  onDomainChange: (domain: DomainId) => void;
}

export function DomainHeader({ activeDomain, onDomainChange }: DomainHeaderProps) {
  return (
    <header className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-2.5 mr-4">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center">
            <Activity className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-base font-semibold tracking-tight">syntropiq</span>
        </Link>

        <div className="h-6 w-px bg-border" />

        {/* Domain tabs */}
        <div className="flex items-center gap-1">
          {(Object.keys(DOMAINS) as DomainId[]).map((id) => {
            const domain = DOMAINS[id];
            const Icon = domainIcons[id];
            const isActive = id === activeDomain;
            const colors = domainColors[id];

            return (
              <button
                key={id}
                onClick={() => onDomainChange(id)}
                className={cn(
                  "flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium border transition-all duration-200 cursor-pointer",
                  isActive ? colors.active : colors.inactive
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {domain.shortLabel}
              </button>
            );
          })}
        </div>
      </div>

      <span className="text-[10px] font-mono text-text-muted bg-white/5 px-3 py-1.5 rounded-full border border-border">
        DEMO MODE
      </span>
    </header>
  );
}
