"use client";

import * as React from "react";
import { Search, Loader2, FileText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useSemanticSearch } from "@/features/retrieval/hooks/use-retrieval";
import { usePreferences } from "@/context/preferences-context";
import { useLocalHistory } from "@/hooks/use-local-history";
import { ApiError } from "@/types/api";
import type { RankedResultOut } from "@/types/retrieval";

interface SearchHistoryEntry {
  query: string;
  topK: number;
  threshold: number;
}

export function RetrievalSearch() {
  const { preferences } = usePreferences();
  const [query, setQuery] = React.useState("");
  const [topK, setTopK] = React.useState(preferences.retrieval.defaultTopK);
  const [threshold, setThreshold] = React.useState(preferences.retrieval.defaultSimilarityThreshold);
  const history = useLocalHistory<SearchHistoryEntry>("maara_search_history", 8, (item) => item.query);
  const hydratedRef = React.useRef(false);
  React.useEffect(() => {
    // Preferences load from localStorage a tick after mount (SSR-safe
    // hydration, see PreferencesProvider); sync the form's initial values
    // once that completes, without overwriting the user's own edits.
    if (!hydratedRef.current) {
      setTopK(preferences.retrieval.defaultTopK);
      setThreshold(preferences.retrieval.defaultSimilarityThreshold);
      hydratedRef.current = true;
    }
  }, [preferences]);
  const { mutate: search, data, isPending, error } = useSemanticSearch();

  function runSearch(entry: SearchHistoryEntry) {
    search({ query: entry.query, top_k: entry.topK, similarity_threshold: entry.threshold });
    history.add(entry);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    runSearch({ query: trimmed, topK, threshold });
  }

  function onSelectHistory(entry: SearchHistoryEntry) {
    setQuery(entry.query);
    setTopK(entry.topK);
    setThreshold(entry.threshold);
    runSearch(entry);
  }

  return (
    <div className="space-y-5">
      <form onSubmit={onSubmit} className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search across your embedded documents…"
            className="h-11 pl-9 pr-28 text-sm"
            list="retrieval-search-suggestions"
          />
          <datalist id="retrieval-search-suggestions">
            {history.items.map((entry) => (
              <option key={entry.query} value={entry.query} />
            ))}
          </datalist>
          <Button type="submit" size="sm" className="absolute right-1.5 top-1.5" disabled={isPending}>
            {isPending && <Loader2 className="animate-spin" />}
            Search
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-6 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Label htmlFor="top-k" className="text-xs font-normal">
              Results
            </Label>
            <Input
              id="top-k"
              type="number"
              min={1}
              max={50}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="h-7 w-16 text-xs"
            />
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="threshold" className="text-xs font-normal">
              Min. similarity
            </Label>
            <input
              id="threshold"
              type="range"
              min={-1}
              max={1}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="accent-primary"
            />
            <span className="font-mono">{threshold.toFixed(2)}</span>
          </div>
        </div>
      </form>

      {history.hydrated && history.items.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">Recent:</span>
          {history.items.map((entry) => (
            <button
              key={entry.query}
              type="button"
              onClick={() => onSelectHistory(entry)}
              className="rounded-full border border-border bg-muted/50 px-2.5 py-1 text-xs text-foreground transition-colors hover:bg-muted"
            >
              {entry.query}
            </button>
          ))}
          <button
            type="button"
            onClick={history.clear}
            className="text-xs text-muted-foreground underline-offset-2 hover:underline"
          >
            Clear
          </button>
        </div>
      )}

      {error && (
        <ErrorBanner
          message={error instanceof ApiError ? error.message : "Search failed. Try again."}
        />
      )}

      {data && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {data.result_count} result{data.result_count === 1 ? "" : "s"} for{" "}
            <span className="font-medium text-foreground">&ldquo;{data.query}&rdquo;</span>
          </p>
          {data.results.map((r) => (
            <ResultCard key={r.chunk_id} result={r} />
          ))}
          {data.results.length === 0 && (
            <p className="rounded-lg border border-dashed border-border py-8 text-center text-sm text-muted-foreground">
              No chunks passed the similarity threshold. Try lowering it.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ResultCard({ result }: { result: RankedResultOut }) {
  const pct = Math.round(Math.max(0, Math.min(1, result.similarity_score)) * 100);
  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-2 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">#{result.rank}</Badge>
            <FileText className="h-3.5 w-3.5" />
            <span className="font-medium text-foreground">{result.document_title}</span>
            {result.page_number !== null && <span>· page {result.page_number}</span>}
          </div>
          <span className="whitespace-nowrap font-mono text-xs text-muted-foreground">
            {result.similarity_score.toFixed(3)}
          </span>
        </div>

        <p className="text-sm leading-relaxed text-foreground">{result.chunk_text}</p>

        <div className="mt-3 space-y-1.5">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-accent"
              style={{ width: `${pct}%` }}
              aria-hidden="true"
            />
          </div>
          <p className="text-[11px] text-muted-foreground">{result.reason}</p>
        </div>
      </CardContent>
    </Card>
  );
}
