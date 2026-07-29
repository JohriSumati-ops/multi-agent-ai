"use client";

import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from "recharts";
import { Bot } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { useOrchestrationHealth } from "@/features/orchestration/hooks/use-orchestration";

export function AgentHealthChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent health</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ErrorBoundary label="Agent health chart">
          <ChartBody />
        </ErrorBoundary>
      </CardContent>
    </Card>
  );
}

function ChartBody() {
  const { data: health, isLoading } = useOrchestrationHealth();

  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!health || health.length === 0) {
    return <EmptyState icon={Bot} title="No capabilities registered" className="h-48" />;
  }

  const healthyCount = health.filter((h) => h.healthy).length;
  const pct = Math.round((healthyCount / health.length) * 100);
  const data = [{ name: "healthy", value: pct, fill: pct === 100 ? "var(--color-success)" : "var(--color-warning)" }];

  return (
    <div className="flex items-center gap-4">
      <div
        className="relative h-32 w-32 shrink-0"
        role="img"
        aria-label={`${healthyCount} of ${health.length} agent capabilities healthy`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart innerRadius="70%" outerRadius="100%" barSize={10} data={data} startAngle={90} endAngle={-270}>
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar dataKey="value" cornerRadius={6} background={{ fill: "var(--muted)" }} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-lg font-semibold text-foreground">{pct}%</span>
        </div>
      </div>
      <div className="space-y-1 text-xs">
        <p className="text-foreground">
          {healthyCount} of {health.length} capabilities healthy
        </p>
        <ul className="space-y-0.5">
          {health
            .filter((h) => !h.healthy)
            .map((h) => (
              <li key={h.capability} className="font-mono text-destructive">
                {h.capability} — {h.detail}
              </li>
            ))}
        </ul>
      </div>
    </div>
  );
}