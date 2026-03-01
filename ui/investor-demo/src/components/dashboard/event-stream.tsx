"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { GovernanceEvent } from "@/lib/demo-data";
import {
  ShieldOff,
  ShieldCheck,
  AlertTriangle,
  Settings,
  TrendingDown,
  Activity,
} from "lucide-react";

const eventConfig: Record<
  GovernanceEvent["type"],
  { icon: typeof ShieldOff; color: string; bg: string }
> = {
  agent_suppressed: {
    icon: ShieldOff,
    color: "text-rose-400",
    bg: "bg-rose-400/10",
  },
  agent_restored: {
    icon: ShieldCheck,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  drift_detected: {
    icon: AlertTriangle,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
  },
  threshold_mutated: {
    icon: Settings,
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
  },
  loss_detected: {
    icon: TrendingDown,
    color: "text-rose-400",
    bg: "bg-rose-400/10",
  },
  system_healthy: {
    icon: Activity,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  probation_started: {
    icon: ShieldCheck,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
  },
};

interface EventStreamProps {
  events: GovernanceEvent[];
  maxEvents?: number;
}

export function EventStream({ events, maxEvents = 20 }: EventStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  const visible = events.slice(-maxEvents);

  return (
    <div className="glass-card p-5 flex flex-col" style={{ height: "100%" }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider">
          Governance Events
        </h3>
        <span className="text-xs font-mono text-text-muted">
          {events.length} events
        </span>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-2 min-h-0"
        style={{ maxHeight: 320 }}
      >
        {visible.length === 0 ? (
          <div className="flex items-center justify-center h-full text-text-muted text-sm">
            No events yet...
          </div>
        ) : (
          visible.map((event, i) => {
            const cfg = eventConfig[event.type];
            const Icon = cfg.icon;

            return (
              <div
                key={`${event.cycle}-${event.type}-${i}`}
                className={cn(
                  "flex items-start gap-3 p-2.5 rounded-lg fade-in-up",
                  cfg.bg,
                  "border border-transparent"
                )}
              >
                <div className={cn("mt-0.5", cfg.color)}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-text-primary leading-relaxed">
                    {event.message}
                  </p>
                </div>
                <span className="text-[10px] font-mono text-text-muted shrink-0">
                  C{event.cycle}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
