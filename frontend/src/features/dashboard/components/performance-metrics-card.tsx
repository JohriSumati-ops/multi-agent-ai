"use client";

import { Gauge } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { useNavigationTiming } from "@/hooks/use-navigation-timing";

export function PerformanceMetricsCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <Gauge className="h-3.5 w-3.5" /> This session
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ErrorBoundary label="Performance metrics">
          <MetricsBody />
        </ErrorBoundary>
      </CardContent>
    </Card>
  );
}

function MetricsBody() {
  const timing = useNavigationTiming();

  if (!timing) {
    return <p className="text-xs text-muted-foreground">Measuring…</p>;
  }

  const metrics: { label: string; value: number | null }[] = [
    { label: "Time to first byte", value: timing.ttfb },
    { label: "First contentful paint", value: timing.firstContentfulPaint },
    { label: "DOM content loaded", value: timing.domContentLoaded },
    { label: "Full page load", value: timing.loadComplete },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {metrics.map((m) => (
        <div key={m.label}>
          <p className="text-[11px] text-muted-foreground">{m.label}</p>
          <p className="font-mono text-sm font-medium text-foreground">
            {m.value !== null ? `${m.value}ms` : "—"}
          </p>
        </div>
      ))}
    </div>
  );
}