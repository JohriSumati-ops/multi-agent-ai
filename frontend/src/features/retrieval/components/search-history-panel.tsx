"use client";

import * as React from "react";
import { Pin, PinOff, X, History, ArrowUpDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { useLocalHistory } from "@/hooks/use-local-history";

export interface SearchHistoryEntry {
  query: string;
  topK: number;
  threshold: number;
  pinned?: boolean;
}

type SortMode = "recent" | "alpha";

interface SearchHistoryPanelProps {
  history: ReturnType<typeof useLocalHistory<SearchHistoryEntry>>;
  onSelect: (entry: SearchHistoryEntry) => void;
}

export function SearchHistoryPanel({ history, onSelect }: SearchHistoryPanelProps) {
  const [sort, setSort] = React.useState<SortMode>("recent");

  if (!history.hydrated || history.items.length === 0) return null;

  const sorted = [...history.items].sort((a, b) => {
    if (Boolean(b.pinned) !== Boolean(a.pinned)) return Number(b.pinned) - Number(a.pinned);
    return sort === "alpha" ? a.query.localeCompare(b.query) : 0; // "recent" relies on existing storage order
  });

  return (
    <div className="space-y-1.5 rounded-md border border-border bg-muted/20 p-2.5">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
          <History className="h-3 w-3" /> Search history
        </p>
        <div className="flex items-center gap-1.5">
          <Select value={sort} onValueChange={(v) => setSort(v as SortMode)}>
            <SelectTrigger className="h-6 w-auto gap-1 border-none bg-transparent px-1 text-[11px] text-muted-foreground shadow-none">
              <ArrowUpDown className="h-3 w-3" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Most recent</SelectItem>
              <SelectItem value="alpha">A–Z</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="ghost" size="sm" className="h-6 px-1.5 text-[11px]" onClick={history.clear}>
            Clear all
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {sorted.map((entry) => (
          <div
            key={entry.query}
            className="group flex items-center gap-1 rounded-full border border-border bg-surface px-2 py-1 text-xs"
          >
            <button type="button" onClick={() => onSelect(entry)} className="text-foreground hover:underline">
              {entry.query}
            </button>
            <button
              type="button"
              onClick={() => history.update(entry.query, { pinned: !entry.pinned })}
              aria-label={entry.pinned ? "Unpin search" : "Pin search"}
              className="text-muted-foreground hover:text-primary"
            >
              {entry.pinned ? <PinOff className="h-3 w-3" /> : <Pin className="h-3 w-3" />}
            </button>
            <button
              type="button"
              onClick={() => history.remove(entry.query)}
              aria-label="Delete from history"
              className="text-muted-foreground opacity-0 hover:text-destructive group-hover:opacity-100"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
