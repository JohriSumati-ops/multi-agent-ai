"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Search, XCircle } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { memoryApi } from "@/lib/api/memory-api";
import { queryKeys } from "@/lib/api/query-keys";
import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/types/api";
import { toast } from "sonner";

export function SessionLookupPanel() {
  const [sessionId, setSessionId] = React.useState("");
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isFetching, error } = useQuery({
    queryKey: queryKeys.memory.session(activeId ?? ""),
    queryFn: () => memoryApi.session(activeId as string),
    enabled: !!activeId,
  });

  async function endSession() {
    if (!activeId) return;
    try {
      await memoryApi.endSession(activeId);
      toast.success(`Session "${activeId}" ended`);
      queryClient.removeQueries({ queryKey: queryKeys.memory.session(activeId) });
      setActiveId(null);
    } catch (err) {
      toast.error("Couldn't end session", {
        description: err instanceof ApiError ? err.message : "Try again.",
      });
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Working memory is per-session and not enumerable — look one up by its session ID (e.g. the ID
        used when calling <code className="font-mono">/orchestration/execute</code>).
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (sessionId.trim()) setActiveId(sessionId.trim());
        }}
        className="relative max-w-md"
      >
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
          placeholder="Session ID…"
          className="h-10 pl-9 pr-24 font-mono text-sm"
        />
        <Button type="submit" size="sm" className="absolute right-1.5 top-1.5" disabled={isFetching}>
          {isFetching && <Loader2 className="animate-spin" />}
          Look up
        </Button>
      </form>

      {error && (
        <ErrorBanner
          message={
            error instanceof ApiError && error.code === "session_not_found"
              ? "No session found with that ID."
              : error instanceof ApiError
                ? error.message
                : "Lookup failed."
          }
        />
      )}

      {data && (
        <Card>
          <CardContent className="space-y-3 p-4">
            <div className="flex items-center justify-between">
              <p className="font-mono text-sm text-foreground">{data.session_id}</p>
              <Button variant="ghost" size="sm" onClick={endSession} className="text-destructive hover:text-destructive">
                <XCircle className="h-3.5 w-3.5" /> End session
              </Button>
            </div>
            <pre className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs text-foreground">
              {JSON.stringify(data.state, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
