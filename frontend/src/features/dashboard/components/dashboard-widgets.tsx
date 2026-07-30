"use client";

import Link from "next/link";
import { FileText, Search, Sparkles, Workflow, ArrowRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import { useMemoryStatistics } from "@/features/memory/hooks/use-memory";
import { useSystemHealth } from "@/features/system/hooks/use-system";
import { useOrchestrationHealth } from "@/features/orchestration/hooks/use-orchestration";
import { DOCUMENT_STATUS_LABEL, DOCUMENT_STATUS_VARIANT } from "@/features/documents/status";

const QUICK_ACTIONS = [
  { label: "Upload a document", href: "/documents", icon: FileText },
  { label: "Run a semantic search", href: "/retrieval", icon: Search },
  { label: "Ask a research question", href: "/research", icon: Sparkles },
  { label: "Execute an agent goal", href: "/orchestration", icon: Workflow },
];

export function QuickActions() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {QUICK_ACTIONS.map((action) => (
        <Link key={action.href} href={action.href}>
          <Card className="h-full transition-colors hover:border-accent">
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-2.5">
                <action.icon className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium text-foreground">{action.label}</span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export function RecentDocumentsCard() {
  const { data: documents, isLoading } = useDocuments();
  const recent = [...(documents ?? [])]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>Recent documents</CardTitle>
        <Link href="/documents" className="text-xs text-primary hover:underline">
          View all
        </Link>
      </CardHeader>
      <CardContent className="space-y-2 pt-0">
        {isLoading && Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
        {!isLoading && recent.length === 0 && (
          <p className="py-6 text-center text-sm text-muted-foreground">No documents uploaded yet.</p>
        )}
        {recent.map((doc) => (
          <div key={doc.id} className="flex items-center justify-between gap-2 border-b border-border py-2 last:border-0">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{doc.title}</p>
              <p className="truncate font-mono text-[11px] text-muted-foreground">{doc.file_name}</p>
            </div>
            <Badge variant={DOCUMENT_STATUS_VARIANT[doc.status]}>{DOCUMENT_STATUS_LABEL[doc.status]}</Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function MemorySummaryCard() {
  const { data: stats, isLoading } = useMemoryStatistics();

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>Memory</CardTitle>
        <Link href="/memory" className="text-xs text-primary hover:underline">
          View all
        </Link>
      </CardHeader>
      <CardContent className="pt-0">
        {isLoading || !stats ? (
          <Skeleton className="h-16 w-full" />
        ) : (
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Total</p>
              <p className="font-mono font-medium text-foreground">{stats.total_memories}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Pending cleanup</p>
              <p className="font-mono font-medium text-foreground">{stats.expired_pending_cleanup}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Health</p>
              <Badge variant={stats.memory_health === "healthy" ? "success" : "warning"}>
                {stats.memory_health}
              </Badge>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function OrchestrationHealthCard() {
  const { data: health, isLoading } = useOrchestrationHealth();
  const healthyCount = health?.filter((h) => h.healthy).length ?? 0;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>Agent health</CardTitle>
        <Link href="/orchestration" className="text-xs text-primary hover:underline">
          View all
        </Link>
      </CardHeader>
      <CardContent className="pt-0">
        {isLoading || !health ? (
          <Skeleton className="h-16 w-full" />
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-foreground">
              {healthyCount} of {health.length} capabilities healthy
            </p>
            <div className="flex flex-wrap gap-1.5">
              {health.map((h) => (
                <Badge key={h.capability} variant={h.healthy ? "success" : "destructive"} className="font-mono">
                  {h.capability}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function SystemHealthStrip() {
  const { data: health } = useSystemHealth();
  if (!health) return null;
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span className={`h-1.5 w-1.5 rounded-full ${health.status === "healthy" ? "bg-success" : "bg-warning"}`} />
      Backend {health.status} · {health.environment}
    </div>
  );
}
