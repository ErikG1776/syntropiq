"use client";

import { useMemo } from "react";
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
import {
  getNewlyRestored,
  getNewlySuppressed,
  getSuppressedAfter,
} from "@/lib/governance";
import { useControlPlane } from "@/lib/control-plane-context";

export default function CyclesPage() {
  const { cycles } = useControlPlane();

  const rows = useMemo(() => {
    return cycles.map((cycle, index) => {
      const prev = index > 0 ? cycles[index - 1] : null;
      return {
        cycle,
        suppressed: getSuppressedAfter(cycle),
        newlySuppressed: getNewlySuppressed(cycle, prev),
        newlyRestored: getNewlyRestored(cycle, prev),
      };
    });
  }, [cycles]);

  return (
    <section>
      <Card className="bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle>Cycle Breakdown</CardTitle>
          <CardDescription>Per-cycle phase, thresholds, suppressed agents, and governance transitions.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cycle</TableHead>
                <TableHead>Phase</TableHead>
                <TableHead>Trust Threshold</TableHead>
                <TableHead>Suppression Threshold</TableHead>
                <TableHead>Drift Delta</TableHead>
                <TableHead>Suppressed Agents</TableHead>
                <TableHead>Newly Suppressed</TableHead>
                <TableHead>Newly Restored</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map(({ cycle, suppressed, newlySuppressed, newlyRestored }) => (
                <TableRow key={cycle.cycle_index}>
                  <TableCell className="font-medium">{cycle.cycle_index}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={cn(
                        "border",
                        cycle.phase === "baseline" && "border-blue-200 bg-blue-50 text-blue-700",
                        cycle.phase === "drift" && "border-amber-200 bg-amber-50 text-amber-700",
                        cycle.phase === "recovery" && "border-emerald-200 bg-emerald-50 text-emerald-700",
                        cycle.phase === "stabilized" && "border-zinc-200 bg-zinc-100 text-zinc-700"
                      )}
                    >
                      {cycle.phase}
                    </Badge>
                  </TableCell>
                  <TableCell>{cycle.thresholds.trust_threshold?.toFixed(3) ?? "--"}</TableCell>
                  <TableCell>{cycle.thresholds.suppression_threshold?.toFixed(3) ?? "--"}</TableCell>
                  <TableCell>{cycle.thresholds.drift_delta?.toFixed(3) ?? "--"}</TableCell>
                  <TableCell>{suppressed.length > 0 ? suppressed.join(", ") : "None"}</TableCell>
                  <TableCell>{newlySuppressed.length > 0 ? newlySuppressed.join(", ") : "--"}</TableCell>
                  <TableCell>{newlyRestored.length > 0 ? newlyRestored.join(", ") : "--"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </section>
  );
}
