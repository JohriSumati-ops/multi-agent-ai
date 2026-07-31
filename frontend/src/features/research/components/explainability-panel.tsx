"use client";

import * as React from "react";
import { Code2 } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { ReasoningPipeline } from "@/features/research/components/reasoning-pipeline";
import { useExplainResponse } from "@/features/research/hooks/use-research";
import { ApiError } from "@/types/api";

export function ExplainabilityPanel({ responseId }: { responseId: string }) {
  const { data, isLoading, error } = useExplainResponse(responseId);
  const [showRaw, setShowRaw] = React.useState(false);

  if (isLoading) return <Skeleton className="h-32 w-full" />;
  if (error) {
    return (
      <ErrorBanner message={error instanceof ApiError ? error.message : "Couldn't load the explainability trace."} />
    );
  }
  if (!data) return null;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>Reasoning trace</CardTitle>
        <Button variant="ghost" size="sm" onClick={() => setShowRaw((v) => !v)}>
          <Code2 /> {showRaw ? "Hide" : "Show"} raw payload
        </Button>
      </CardHeader>
      <CardContent className="pt-0">
        <ReasoningPipeline data={data} />
        {showRaw && (
          <pre className="mt-4 max-h-64 overflow-auto rounded-md bg-muted p-3 font-mono text-[11px] text-foreground">
            {JSON.stringify(data.explainability_payload, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
