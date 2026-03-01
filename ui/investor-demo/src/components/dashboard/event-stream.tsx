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
  { icon: typeof ShieldOff; color: string }
> = {
  agent_suppressed: { icon: ShieldOff, color: "text-red-400" },
  agent_restored: { icon: ShieldCheck, color: "text-emerald-400" },
  drift_detected: { icon: AlertTriangle, color: "text-amber-400" },
  threshold_mutated: { icon: Settings, color: "text-blue-400" },
  loss_detected: { icon: TrendingDown, color: "text-red-400" },
  system_healthy: { icon: Activity, color: "text-emerald-400" },
  probation_started: { icon: ShieldCheck, color: "text-amber-400" },
};

interface EventStreamProps {
  events: GovernanceEvent[];
  maxEvents?: number;
}

export function EventStream({ events, maxEvents = 25 }: EventStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  const visible = events.slice(-maxEvents);

  return (
    <div className="panel p-5 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold">Event Feed</h3>
        <span className="text-[11px] font-mono text-text-muted">
          {events.length}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-1.5 min-h-0"
        style={{ maxHeight: 280 }}
      >
        {visible.length === 0 ? (
          <div className="flex items-center justify-center h-full text-text-muted text-sm">
            No events yet
          </div>
        ) : (
          visible.map((event, i) => {
            const cfg = eventConfig[event.type];
            const Icon = cfg.icon;

            return (
              <div
                key={`${event.cycle}-${event.type}-${i}`}
                className="flex items-start gap-2.5 px-3 py-2 rounded-lg hover:bg-white/[0.02] transition-colors fade-in"
              >
                <div className={cn("mt-0.5 shrink-0", cfg.color)}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <p className="text-xs text-text-secondary leading-relaxed flex-1 min-w-0">
                  {event.message}
                </p>
                <span className="text-[10px] font-mono text-text-muted shrink-0 mt-0.5">
                  {event.cycle}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
