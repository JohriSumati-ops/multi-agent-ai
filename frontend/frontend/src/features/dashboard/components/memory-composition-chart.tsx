"use client";

import * as React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { useMemoryStatistics } from "@/features/memory/hooks/use-memory";
import { BrainCircuit } from "lucide-react";

const COLORS = ["var(--color-chart-1)", "var(--color-chart-2)", "var(--color-chart-3)", "var(--color-chart-4)"];

export function MemoryCompositionChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Memory composition</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ErrorBoundary label="Memory composition chart">
          <ChartBody />
        </ErrorBoundary>
      </CardContent>
    </Card>
  );
}

function ChartBody() {
  const { data: stats, isLoading } = useMemoryStatistics();

  if (isLoading) return <Skeleton className="h-48 w-full" />;

  const entries = Object.entries(stats?.counts_by_type ?? {}).filter(([, count]) => count > 0);
  if (entries.length === 0) {
    return <EmptyState icon={BrainCircuit} title="No memories stored yet" className="h-48" />;
  }

  const data = entries.map(([type, count]) => ({ name: type, value: count }));

  return (
    <div className="flex items-center gap-4">
      <div className="h-48 w-40 shrink-0" role="img" aria-label="Pie chart of memory counts by type">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={40} outerRadius={70} paddingAngle={2}>
              {data.map((entry, i) => (
                <Cell key={entry.name} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <RechartsTooltip
              contentStyle={{
                background: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="space-y-1.5 text-xs">
        {data.map((entry, i) => (
          <li key={entry.name} className="flex items-center gap-2">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: COLORS[i % COLORS.length] }}
              aria-hidden="true"
            />
            <span className="font-mono text-muted-foreground">{entry.name}</span>
            <span className="font-medium text-foreground">{entry.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}