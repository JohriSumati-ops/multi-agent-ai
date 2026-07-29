"use client";

import * as React from "react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip, Cell } from "recharts";
import { FileText } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import { DOCUMENT_STATUS_LABEL } from "@/features/documents/status";
import type { DocumentStatus } from "@/types/document";

const STATUS_COLOR: Record<DocumentStatus, string> = {
  uploaded: "var(--color-muted-foreground)",
  parsing: "var(--color-info)",
  parsed: "var(--color-info)",
  chunked: "var(--color-accent)",
  embedding: "var(--color-warning)",
  ready: "var(--color-success)",
  failed: "var(--color-destructive)",
};

export function DocumentStatusChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Documents by status</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ErrorBoundary label="Document status chart">
          <ChartBody />
        </ErrorBoundary>
      </CardContent>
    </Card>
  );
}

function ChartBody() {
  const { data: documents, isLoading } = useDocuments();

  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!documents || documents.length === 0) {
    return <EmptyState icon={FileText} title="No documents uploaded yet" className="h-48" />;
  }

  const counts = documents.reduce<Record<string, number>>((acc, doc) => {
    acc[doc.status] = (acc[doc.status] ?? 0) + 1;
    return acc;
  }, {});

  const data = (Object.keys(DOCUMENT_STATUS_LABEL) as DocumentStatus[])
    .filter((status) => counts[status] > 0)
    .map((status) => ({ status, label: DOCUMENT_STATUS_LABEL[status], count: counts[status] }));

  return (
    <div className="h-48" role="img" aria-label="Bar chart of documents grouped by processing status">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
          <YAxis
            type="category"
            dataKey="label"
            width={70}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          />
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
              <Cell key={entry.status} fill={STATUS_COLOR[entry.status]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}