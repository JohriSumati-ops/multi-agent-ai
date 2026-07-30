"use client";

import * as React from "react";
import { Database, Gauge, AlertCircle, Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useMemoryStatistics,
  usePruneMemory,
  useClearMemory,
} from "@/features/memory/hooks/use-memory";
import { usePreferences } from "@/context/preferences-context";

const HEALTH_VARIANT: Record<string, "success" | "warning" | "destructive" | "muted"> = {
  healthy: "success",
  degraded: "warning",
  critical: "destructive",
};

export function MemoryStatisticsPanel() {
  const { data: stats, isLoading } = useMemoryStatistics();
  const { mutate: prune, isPending: pruning } = usePruneMemory();
  const { mutate: clear, isPending: clearing } = useClearMemory();
  const [confirmClear, setConfirmClear] = React.useState(false);
  const { preferences } = usePreferences();
  const keepTopN = preferences.memory.defaultPruneKeepTopN;

  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard icon={Database} label="Total memories" value={stats.total_memories.toLocaleString()} />
        <StatCard icon={Gauge} label="Total accesses" value={stats.total_accesses.toLocaleString()} />
        <StatCard
          icon={AlertCircle}
          label="Pending cleanup"
          value={stats.expired_pending_cleanup.toLocaleString()}
        />
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-xs text-muted-foreground">Memory health</p>
              <Badge variant={HEALTH_VARIANT[stats.memory_health] ?? "muted"} className="mt-1.5">
                {stats.memory_health}
              </Badge>
            </div>
            <Sparkles className="h-5 w-5 text-muted-foreground" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>By type</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 pt-0">
          {Object.entries(stats.counts_by_type).map(([type, count]) => (
            <Badge key={type} variant="outline" className="font-mono">
              {type}: {count}
            </Badge>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cleanup</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 pt-0">
          <Button variant="outline" size="sm" disabled={pruning} onClick={() => prune(keepTopN)}>
            Prune expired &amp; over-cap (keep top {keepTopN.toLocaleString()})
          </Button>
          {!confirmClear ? (
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:text-destructive"
              onClick={() => setConfirmClear(true)}
            >
              Clear all memory
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Clear everything? This can&apos;t be undone.</span>
              <Button variant="destructive" size="sm" disabled={clearing} onClick={() => clear()}>
                Confirm
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirmClear(false)}>
                Cancel
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-1 font-mono text-lg font-semibold text-foreground">{value}</p>
        </div>
        <Icon className="h-5 w-5 text-muted-foreground" />
      </CardContent>
    </Card>
  );
}
