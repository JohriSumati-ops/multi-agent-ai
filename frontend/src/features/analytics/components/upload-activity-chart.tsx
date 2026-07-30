"use client";

import * as React from "react";
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip, CartesianGrid } from "recharts";
import { UploadCloud } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { useDocuments } from "@/features/documents/hooks/use-documents";

const DAYS_SHOWN = 14;

function dayKey(iso: string): string {
  return iso.slice(0, 10); // YYYY-MM-DD
}

export function UploadActivityChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <UploadCloud className="h-3.5 w-3.5" /> Uploads over time
        </CardTitle>
        <CardDescription>Documents uploaded per day, last {DAYS_SHOWN} days — from real upload timestamps.</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <ErrorBoundary label="Upload activity chart">
          <ChartBody />
        </ErrorBoundary>
      </CardContent>
    </Card>
  );
}

function ChartBody() {
  const { data: documents, isLoading } = useDocuments();

  if (isLoading) return <Skeleton className="h-56 w-full" />;
  if (!documents || documents.length === 0) {
    return <EmptyState icon={UploadCloud} title="No documents uploaded yet" className="h-56" />;
  }

  const counts = new Map<string, number>();
  const today = new Date();
  for (let i = DAYS_SHOWN - 1; i >= 0; i -= 1) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    counts.set(d.toISOString().slice(0, 10), 0);
  }
  for (const doc of documents) {
    const key = dayKey(doc.created_at);
    if (counts.has(key)) counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  const data = Array.from(counts.entries()).map(([date, count]) => ({
    date: date.slice(5), // MM-DD
    count,
  }));

  return (
    <div className="h-56" role="img" aria-label={`Area chart of document uploads per day over the last ${DAYS_SHOWN} days`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
          <defs>
            <linearGradient id="uploadFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.4} />
              <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} interval={1} />
          <YAxis allowDecimals={false} width={28} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
          <RechartsTooltip
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Area type="monotone" dataKey="count" stroke="var(--color-chart-1)" fill="url(#uploadFill)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
