"use client";

import { CheckCircle2, XCircle, Database, Layers } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useSystemHealth, useSystemVersion } from "@/features/system/hooks/use-system";

export default function SystemPage() {
  const { data: health, isLoading: healthLoading } = useSystemHealth();
  const { data: version, isLoading: versionLoading } = useSystemVersion();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">System</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Live backend health and version, polled from the API.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5">
              <Database className="h-3.5 w-3.5" /> Health
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {healthLoading || !health ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Badge variant={health.status === "healthy" ? "success" : "warning"}>{health.status}</Badge>
                </div>
                <p className="flex items-center gap-1.5 text-muted-foreground">
                  {health.database ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-destructive" />
                  )}
                  Database connectivity
                </p>
                <p className="text-muted-foreground">Environment: {health.environment}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5" /> Version
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {versionLoading || !version ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <div className="space-y-1 text-sm text-muted-foreground">
                <p className="text-foreground">{version.app_name}</p>
                <p className="font-mono">v{version.version}</p>
                <p>{version.environment}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-4 text-xs text-muted-foreground">
          Configuration, usage metering, model information, and log streaming aren&apos;t exposed by the
          current backend — only <code className="font-mono">/health</code> and{" "}
          <code className="font-mono">/version</code> exist under <code className="font-mono">/system</code>{" "}
          today. These panels can be added once corresponding endpoints exist.
        </CardContent>
      </Card>
    </div>
  );
}
