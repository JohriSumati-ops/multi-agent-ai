"use client";

import * as React from "react";
import { Search, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useSemanticSearch } from "@/features/retrieval/hooks/use-retrieval";
import { usePreferences } from "@/context/preferences-context";
import { useLocalHistory } from "@/hooks/use-local-history";
import { SourceExplorerResults } from "@/features/retrieval/components/source-explorer-results";
import { SearchHistoryPanel, type SearchHistoryEntry } from "@/features/retrieval/components/search-history-panel";
import { ApiError } from "@/types/api";

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

      <SearchHistoryPanel history={history} onSelect={onSelectHistory} />

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
          <SourceExplorerResults data={data} />
        </div>
      )}
    </div>
  );
}
