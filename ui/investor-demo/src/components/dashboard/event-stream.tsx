"use client";

import { useEffect, useRef } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  {
    icon: typeof ShieldOff;
    badge: "info" | "warning" | "destructive" | "success";
    label: string;
  }
> = {
  agent_suppressed: { icon: ShieldOff, badge: "destructive", label: "Suppressed" },
  agent_restored: { icon: ShieldCheck, badge: "success", label: "Restored" },
  drift_detected: { icon: AlertTriangle, badge: "warning", label: "Drift" },
  threshold_mutated: { icon: Settings, badge: "info", label: "Adapted" },
  loss_detected: { icon: TrendingDown, badge: "destructive", label: "Loss" },
  system_healthy: { icon: Activity, badge: "success", label: "Healthy" },
  probation_started: { icon: ShieldCheck, badge: "warning", label: "Probation" },
};

interface EventStreamProps {
  events: GovernanceEvent[];
  maxEvents?: number;
}

export function EventStream({ events, maxEvents = 20 }: EventStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  const visible = events.slice(-maxEvents);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Governance Events</CardTitle>
            <CardDescription className="mt-1">Decision log</CardDescription>
          </div>
          <span className="text-[11px] font-mono text-muted-foreground">
            {events.length}
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 pt-0">
        <div
          ref={scrollRef}
          className="overflow-y-auto space-y-1.5"
          style={{ maxHeight: 260 }}
        >
          {visible.length === 0 ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
              No events yet
            </div>
          ) : (
            visible.map((event, i) => {
              const cfg = eventConfig[event.type];

              return (
                <div
                  key={`${event.cycle}-${event.type}-${i}`}
                  className="flex items-start gap-2.5 px-2 py-2 rounded-lg hover:bg-muted/50 transition-colors fade-in"
                >
                  <Badge variant={cfg.badge} className="shrink-0 mt-0.5 text-[9px] px-1.5">
                    {cfg.label}
                  </Badge>
                  <p className="text-xs text-muted-foreground leading-relaxed flex-1 min-w-0">
                    {event.message}
                  </p>
                  <span className="text-[10px] font-mono text-muted-foreground shrink-0 mt-0.5">
                    {event.cycle}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
