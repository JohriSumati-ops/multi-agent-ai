"use client";

import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip, Cell } from "recharts";
import { Activity } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { useActivityLog } from "@/features/analytics/hooks/use-activity-log";
import type { ActivityType } from "@/features/analytics/activity-log";

const TYPE_LABEL: Record<ActivityType, string> = {
  upload: "Uploads",
  search: "Searches",
  research: "Research queries",
  orchestration: "Agent executions",
  memory: "Memory actions",
};

const TYPE_COLOR: Record<ActivityType, string> = {
  upload: "var(--color-chart-1)",
  search: "var(--color-chart-2)",
  research: "var(--color-chart-3)",
  orchestration: "var(--color-chart-4)",
  memory: "var(--color-chart-5)",
};

export function ActivityFrequencyChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5" /> Activity by type
        </CardTitle>
        <CardDescription>Actions taken in this browser since activity logging started.</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <ErrorBoundary label="Activity frequency chart">
          <ChartBody />
        </ErrorBoundary>
      </CardContent>
    </Card>
  );
}

function ChartBody() {
  const entries = useActivityLog();

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No activity recorded yet"
        description="Run a search, ask a research question, or execute an agent goal — activity will appear here."
        className="h-48"
      />
    );
  }

  const counts = entries.reduce<Record<string, number>>((acc, entry) => {
    acc[entry.type] = (acc[entry.type] ?? 0) + 1;
    return acc;
  }, {});

  const data = (Object.keys(TYPE_LABEL) as ActivityType[])
    .filter((type) => counts[type] > 0)
    .map((type) => ({ type, label: TYPE_LABEL[type], count: counts[type] }));

  return (
    <div className="h-48" role="img" aria-label="Bar chart of recorded actions grouped by type">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
          <YAxis type="category" dataKey="label" width={110} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
          <RechartsTooltip
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
            cursor={{ fill: "var(--muted)" }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={18}>
            {data.map((entry) => (
              <Cell key={entry.type} fill={TYPE_COLOR[entry.type]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
