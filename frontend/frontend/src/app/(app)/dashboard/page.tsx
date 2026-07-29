import type { Metadata } from "next";

import {
  QuickActions,
  RecentDocumentsCard,
  MemorySummaryCard,
  OrchestrationHealthCard,
  SystemHealthStrip,
} from "@/features/dashboard/components/dashboard-widgets";

export const metadata: Metadata = { title: "Dashboard — Research Assistant Console" };

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">An overview of your research workspace.</p>
        </div>
        <SystemHealthStrip />
      </div>

      <QuickActions />

      <div className="grid gap-4 lg:grid-cols-2">
        <RecentDocumentsCard />
        <MemorySummaryCard />
        <OrchestrationHealthCard />
      </div>
    </div>
  );
}
