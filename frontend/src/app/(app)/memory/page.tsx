import type { Metadata } from "next";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { MemoryStatisticsPanel } from "@/features/memory/components/memory-statistics-panel";
import { MemoryTimeline } from "@/features/memory/components/memory-timeline";
import { MemorySearchPanel } from "@/features/memory/components/memory-search-panel";
import { SessionLookupPanel } from "@/features/memory/components/session-lookup-panel";

export const metadata: Metadata = { title: "Memory — Research Assistant Console" };

export default function MemoryPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Memory</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Working, session, short-term, and long-term memory — statistics, timeline, and cleanup.
        </p>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="session">Session</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <MemoryStatisticsPanel />
        </TabsContent>
        <TabsContent value="timeline">
          <MemoryTimeline />
        </TabsContent>
        <TabsContent value="search">
          <MemorySearchPanel />
        </TabsContent>
        <TabsContent value="session">
          <SessionLookupPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
