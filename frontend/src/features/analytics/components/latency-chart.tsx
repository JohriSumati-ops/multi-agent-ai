"use client";

import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";
import { Timer } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { useActivityLog } from "@/features/analytics/hooks/use-activity-log";
import type { ActivityType } from "@/features/analytics/activity-log";

const TYPE_LABEL: Record<ActivityType, string> = {
  upload: "Uploads",
  search: "Searches",
  research: "Research",
  orchestration: "Orchestration",
  memory: "Memory",
};

export function LatencyChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <Timer className="h-3.5 w-3.5" /> Average response latency
        </CardTitle>
        <CardDescription>
          Averaged from logged actions. Research latency is the backend&apos;s own reported time; other actions are
          measured client-side (request round-trip).
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <ErrorBoundary label="Latency chart">
          <ChartBody />
        </ErrorBoundary>
      </CardContent>
    </Card>
  );
}

function ChartBody() {
  const entries = useActivityLog().filter((e) => e.success && e.latencyMs !== null);

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={Timer}
        title="No timed actions yet"
        description="Latency appears here once a search, research query, or agent execution completes."
        className="h-48"
      />
    );
  }

  const byType = entries.reduce<Record<string, { total: number; count: number }>>((acc, entry) => {
    const bucket = acc[entry.type] ?? { total: 0, count: 0 };
    bucket.total += entry.latencyMs ?? 0;
    bucket.count += 1;
    acc[entry.type] = bucket;
    return acc;
  }, {});

  const data = (Object.keys(TYPE_LABEL) as ActivityType[])
    .filter((type) => byType[type])
    .map((type) => ({
      label: TYPE_LABEL[type],
      avgMs: Math.round(byType[type].total / byType[type].count),
    }));

  return (
    <div className="h-48" role="img" aria-label="Bar chart of average response latency in milliseconds by action type">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
          <YAxis
            width={40}
            tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
            label={{ value: "ms", angle: -90, position: "insideLeft", fontSize: 10, fill: "var(--muted-foreground)" }}
          />
          <RechartsTooltip
            formatter={(value) => [`${value} ms`, "Avg latency"]}
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
            cursor={{ fill: "var(--muted)" }}
          />
          <Bar dataKey="avgMs" fill="var(--color-chart-2)" radius={[4, 4, 0, 0]} maxBarSize={48} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
