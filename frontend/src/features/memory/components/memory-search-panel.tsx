"use client";

import * as React from "react";
import { Search, Loader2 } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useMemorySearch } from "@/features/memory/hooks/use-memory";
import { ApiError } from "@/types/api";

export function MemorySearchPanel() {
  const [query, setQuery] = React.useState("");
  const { mutate: search, data, isPending, error } = useMemorySearch();

  return (
    <div className="space-y-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim()) search({ query: query.trim() });
        }}
        className="relative"
      >
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search stored memories by meaning…"
          className="h-10 pl-9 pr-24"
        />
        <Button type="submit" size="sm" className="absolute right-1.5 top-1.5" disabled={isPending}>
          {isPending && <Loader2 className="animate-spin" />}
          Search
        </Button>
      </form>

      {error && <ErrorBanner message={error instanceof ApiError ? error.message : "Search failed."} />}

      {data && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">{data.result_count} results</p>
          {data.results.map((r) => (
            <Card key={r.memory_id}>
              <CardContent className="p-3">
                <div className="mb-1 flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>#{r.rank} · confidence {r.confidence.toFixed(2)}</span>
                  <span className="font-mono">{r.similarity_score.toFixed(3)}</span>
                </div>
                <p className="text-sm text-foreground">{r.content}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">{r.reason}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
