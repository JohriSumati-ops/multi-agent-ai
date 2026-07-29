"use client";

import { CheckCircle2, XCircle, Bot } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useCapabilities, useOrchestrationHealth } from "@/features/orchestration/hooks/use-orchestration";

export function CapabilitiesList() {
  const { data: capabilities, isLoading } = useCapabilities();
  const { data: health } = useOrchestrationHealth();

  const healthByCapability = new Map(health?.map((h) => [h.capability, h]) ?? []);

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {capabilities?.map((cap) => {
        const h = healthByCapability.get(cap.capability);
        return (
          <Card key={cap.capability}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-muted-foreground" />
                  <span className="font-mono text-sm font-medium text-foreground">{cap.capability}</span>
                </div>
                {h && (
                  <Badge variant={h.healthy ? "success" : "destructive"} className="gap-1">
                    {h.healthy ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                    {h.healthy ? "healthy" : "down"}
                  </Badge>
                )}
              </div>
              <p className="mt-2 text-xs text-muted-foreground">{cap.description}</p>
              <p className="mt-2 text-[11px] text-muted-foreground">
                agent: <span className="font-mono text-foreground">{cap.agent_name}</span>
              </p>
              {cap.depends_on.length > 0 && (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  depends on: <span className="font-mono">{cap.depends_on.join(", ")}</span>
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
