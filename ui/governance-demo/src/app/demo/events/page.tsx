"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { getEventBadgeClasses, type GovernanceEventType } from "@/lib/governance";
import { useControlPlane } from "@/lib/control-plane-context";

const FILTERS: Array<{ label: string; value: "all" | GovernanceEventType }> = [
  { label: "All", value: "all" },
  { label: "Drift", value: "drift" },
  { label: "Suppression", value: "suppression" },
  { label: "Recovery", value: "recovery" },
  { label: "Threshold", value: "threshold" },
  { label: "Circuit", value: "circuit" },
  { label: "Stabilized", value: "stabilized" },
];

export default function EventsPage() {
  const { allEvents } = useControlPlane();
  const [filter, setFilter] = useState<"all" | GovernanceEventType>("all");

  const filteredEvents = useMemo(() => {
    if (filter === "all") return allEvents;
    return allEvents.filter((event) => event.type === filter);
  }, [allEvents, filter]);

  const grouped = useMemo(() => {
    const map = new Map<number, typeof filteredEvents>();
    for (const event of filteredEvents) {
      const current = map.get(event.cycle) ?? [];
      current.push(event);
      map.set(event.cycle, current);
    }
    return Array.from(map.entries()).sort((a, b) => b[0] - a[0]);
  }, [filteredEvents]);

  return (
    <section className="space-y-6">
      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle>Governance Event Ledger</CardTitle>
          <CardDescription>Structured event stream grouped by cycle with type filters.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((item) => (
              <Button
                key={item.value}
                size="sm"
                variant={filter === item.value ? "default" : "outline"}
                className={cn(filter === item.value && "bg-blue-600 text-white hover:bg-blue-500")}
                onClick={() => setFilter(item.value)}
              >
                {item.label}
              </Button>
            ))}
          </div>

          <ScrollArea className="h-[620px] pr-3">
            <div className="space-y-4">
              {grouped.length === 0 && (
                <p className="text-sm text-zinc-500">No events for this filter.</p>
              )}
              {grouped.map(([cycle, events]) => (
                <Card key={cycle} className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Cycle {cycle}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {events.map((event, index) => (
                      <div
                        key={`${event.cycle ?? "c"}-${event.type ?? "t"}-${event.agent ?? "system"}-${index}`}
                        className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-3 flex items-start justify-between gap-3"
                      >
                        <div>
                          <p className="text-sm text-zinc-700 dark:text-zinc-300">{event.message}</p>
                          {event.agent && <p className="text-xs text-zinc-500 mt-1">Agent: {event.agent}</p>}
                        </div>
                        <Badge variant="outline" className={cn("border", getEventBadgeClasses(event.type))}>
                          {event.type}
                        </Badge>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </section>
  );
}
