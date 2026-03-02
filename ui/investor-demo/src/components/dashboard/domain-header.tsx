"use client";

import { cn } from "@/lib/utils";
import { DOMAINS, type DomainId } from "@/lib/demo-data";
import { ShieldAlert, Landmark, HeartPulse, Activity } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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
    <nav className="flex items-center justify-between border-b border-border pb-4">
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
            <Activity className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-base font-semibold tracking-tight">
            syntropiq
          </span>
        </Link>

        <div className="h-5 w-px bg-border ml-2" />

        {/* Domain tabs */}
        <div className="flex items-center gap-1 bg-card rounded-lg p-1 border border-border">
          {(Object.keys(DOMAINS) as DomainId[]).map((id) => {
            const domain = DOMAINS[id];
            const Icon = domainIcons[id];
            const isActive = id === activeDomain;

            return (
              <button
                key={id}
                onClick={() => onDomainChange(id)}
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer",
                  isActive
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {domain.shortLabel}
              </button>
            );
          })}
        </div>
      </div>

      <Badge variant="outline" className="text-[10px] tracking-wider">
        DEMO MODE
      </Badge>
    </nav>
  );
}
