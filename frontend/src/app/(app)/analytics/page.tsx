"use client";

import { Card, CardContent } from "@/components/ui/card";
import { UploadActivityChart } from "@/features/analytics/components/upload-activity-chart";
import { ActivityFrequencyChart } from "@/features/analytics/components/activity-frequency-chart";
import { LatencyChart } from "@/features/analytics/components/latency-chart";
import { RecentActivityTable } from "@/features/analytics/components/recent-activity-table";
import { DocumentStatusChart } from "@/features/dashboard/components/document-status-chart";
import { MemoryCompositionChart } from "@/features/dashboard/components/memory-composition-chart";
import { AgentHealthChart } from "@/features/dashboard/components/agent-health-chart";

export default function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Trends and activity across documents, retrieval, memory, and agents.
        </p>
      </div>

      <Card>
        <CardContent className="p-4 text-xs text-muted-foreground">
          The backend doesn&apos;t expose history/audit-log endpoints for searches, research queries, or agent
          executions (see the Phase 7/8 notes), so &quot;Activity&quot; and &quot;Latency&quot; below reflect real
          actions logged in <em>this browser</em> going forward, not all-time server history. Document and memory
          charts are live snapshots pulled straight from the API.
        </CardContent>
      </Card>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-foreground">Documents</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <UploadActivityChart />
          <DocumentStatusChart />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-foreground">Session activity &amp; latency</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <ActivityFrequencyChart />
          <LatencyChart />
        </div>
        <RecentActivityTable />
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-foreground">Memory &amp; agents</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <MemoryCompositionChart />
          <AgentHealthChart />
        </div>
      </section>
    </div>
  );
}
