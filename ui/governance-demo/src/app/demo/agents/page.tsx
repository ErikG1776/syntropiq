"use client";

import { useMemo } from "react";
import { Line, LineChart, Tooltip } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { getNewlyRestored, getNewlySuppressed, getSuppressedAfter } from "@/lib/governance";
import { useControlPlane } from "@/lib/control-plane-context";

export default function AgentsPage() {
  const { allAgentIds, visibleCycles, currentCycle, allEvents } = useControlPlane();

  const rows = useMemo(() => {
    return allAgentIds.map((agentId) => {
      const trustScore = currentCycle?.trust?.[agentId] ?? 0;
      const isSuppressed = getSuppressedAfter(currentCycle ?? null).includes(agentId);

      const suppressionCount = visibleCycles.reduce((count, cycle, index) => {
        const prev = index > 0 ? visibleCycles[index - 1] : null;
        return count + (getNewlySuppressed(cycle, prev).includes(agentId) ? 1 : 0);
      }, 0);

      const recoveryCount = visibleCycles.reduce((count, cycle, index) => {
        const prev = index > 0 ? visibleCycles[index - 1] : null;
        return count + (getNewlyRestored(cycle, prev).includes(agentId) ? 1 : 0);
      }, 0);
      const totalSuppressionCycles = visibleCycles.reduce((count, cycle) => {
        return count + (getSuppressedAfter(cycle).includes(agentId) ? 1 : 0);
      }, 0);
      let probationCycles = 0;
      for (let i = visibleCycles.length - 1; i >= 0; i--) {
        const cycle = visibleCycles[i];
        const prev = i > 0 ? visibleCycles[i - 1] : null;
        if (getNewlyRestored(cycle, prev).includes(agentId)) {
          probationCycles = visibleCycles.length - 1 - i;
          break;
        }
      }
      const firstDriftCycle = visibleCycles.find((cycle) => cycle.phase === "drift")?.cycle_index;
      const firstSuppressionCycle = visibleCycles.find((cycle, index) => {
        const prev = index > 0 ? visibleCycles[index - 1] : null;
        return getNewlySuppressed(cycle, prev).includes(agentId);
      })?.cycle_index;
      const containmentSpeed =
        typeof firstDriftCycle === "number" && typeof firstSuppressionCycle === "number"
          ? Math.max(0, firstSuppressionCycle - firstDriftCycle)
          : null;

      const openSuppressions: number[] = [];
      const suppressionDurations: number[] = [];
      for (let i = 0; i < visibleCycles.length; i++) {
        const cycle = visibleCycles[i];
        const prev = i > 0 ? visibleCycles[i - 1] : null;
        if (getNewlySuppressed(cycle, prev).includes(agentId)) {
          openSuppressions.push(cycle.cycle_index);
        }
        if (getNewlyRestored(cycle, prev).includes(agentId) && openSuppressions.length > 0) {
          const start = openSuppressions.shift();
          if (typeof start === "number") {
            suppressionDurations.push(Math.max(0, cycle.cycle_index - start));
          }
        }
      }
      const lastCycleIndex = visibleCycles[visibleCycles.length - 1]?.cycle_index ?? 0;
      for (const start of openSuppressions) {
        suppressionDurations.push(Math.max(0, lastCycleIndex - start + 1));
      }
      const avgSuppressionDuration =
        suppressionDurations.length > 0
          ? suppressionDurations.reduce((sum, value) => sum + value, 0) / suppressionDurations.length
          : null;

      const history = visibleCycles.map((cycle) => ({
        cycle: cycle.cycle_index,
        trust: cycle.trust?.[agentId] ?? null,
      }));

      const latestEvent = [...allEvents].reverse().find((event) => event.agent === agentId)?.message ?? "Routed normally";

      return {
        agentId,
        trustScore,
        status: isSuppressed ? "Suppressed" : recoveryCount > 0 ? "Probation" : "Active",
        suppressionCount,
        totalSuppressionCycles,
        probationCycles,
        recoveryCount,
        containmentSpeed,
        avgSuppressionDuration,
        history,
        latestEvent,
      };
    });
  }, [allAgentIds, allEvents, currentCycle, visibleCycles]);

  return (
    <section>
      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle>Agent Governance Table</CardTitle>
          <CardDescription>Trust history, suppression/recovery counts, and live status by agent.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Current Trust</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Trust History</TableHead>
                <TableHead>Suppressions</TableHead>
                <TableHead>Total Suppression Cycles</TableHead>
                <TableHead>Cycles in Probation</TableHead>
                <TableHead>Avg Suppression Duration</TableHead>
                <TableHead>Containment Speed (cycles)</TableHead>
                <TableHead>Recoveries</TableHead>
                <TableHead>Last Governance Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.agentId}>
                  <TableCell className="font-medium">{row.agentId}</TableCell>
                  <TableCell>{row.trustScore.toFixed(3)}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={cn(
                        "border",
                        row.status === "Active" && "border-emerald-200 bg-emerald-50 text-emerald-700",
                        row.status === "Suppressed" && "border-red-200 bg-red-50 text-red-700",
                        row.status === "Probation" && "border-amber-200 bg-amber-50 text-amber-700"
                      )}
                    >
                      {row.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <LineChart width={130} height={36} data={row.history}>
                      <Tooltip />
                      <Line type="monotone" dataKey="trust" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls />
                    </LineChart>
                  </TableCell>
                  <TableCell>{row.suppressionCount}</TableCell>
                  <TableCell>{row.totalSuppressionCycles}</TableCell>
                  <TableCell>
                    {row.status === "Suppressed" && row.probationCycles === 0
                      ? "—"
                      : row.probationCycles}
                  </TableCell>
                  <TableCell>
                    {typeof row.avgSuppressionDuration === "number" ? `${row.avgSuppressionDuration.toFixed(1)} cycles` : "—"}
                  </TableCell>
                  <TableCell>
                    {typeof row.containmentSpeed === "number" ? `${row.containmentSpeed} cycles` : "—"}
                  </TableCell>
                  <TableCell>{row.recoveryCount}</TableCell>
                  <TableCell className="max-w-[320px] truncate text-zinc-600 dark:text-zinc-400">{row.latestEvent}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </section>
  );
}
