"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useExplainResponse } from "@/features/research/hooks/use-research";
import { ApiError } from "@/types/api";

export function ExplainabilityPanel({ responseId }: { responseId: string }) {
  const { data, isLoading, error } = useExplainResponse(responseId);

  if (isLoading) return <Skeleton className="h-32 w-full" />;
  if (error) {
    return (
      <ErrorBanner message={error instanceof ApiError ? error.message : "Couldn't load the explainability trace."} />
    );
  }
  if (!data) return null;

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <Stat label="Evidence chunks" value={data.retrieved_chunk_ids.length} />
          <Stat label="Memory refs" value={data.memory_references.length} />
          <Stat label="Prompt tokens" value={data.prompt_tokens ?? "—"} />
          <Stat label="Latency" value={data.latency_ms ? `${data.latency_ms}ms` : "—"} />
        </div>
        <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 font-mono text-[11px] text-foreground">
          {JSON.stringify(data.explainability_payload, null, 2)}
        </pre>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-muted-foreground">{label}</p>
      <p className="font-mono font-medium text-foreground">{value}</p>
    </div>
  );
}
