"use client";

import * as React from "react";
import { toast } from "sonner";
import { FileText, ChevronDown, ChevronUp, Copy, ArrowUpDown } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { splitForHighlight } from "@/features/retrieval/highlight";
import type { RankedResultOut, SearchResponse } from "@/types/retrieval";

type SortKey = "rank" | "score" | "document";

const CHUNK_PREVIEW_LENGTH = 220;

export function SourceExplorerResults({ data }: { data: SearchResponse }) {
  const [documentFilter, setDocumentFilter] = React.useState<string>("all");
  const [minConfidence, setMinConfidence] = React.useState(0);
  const [sortKey, setSortKey] = React.useState<SortKey>("rank");

  const documents = React.useMemo(
    () => Array.from(new Set(data.results.map((r) => r.document_title))).sort(),
    [data.results]
  );

  const filtered = React.useMemo(() => {
    const rows = data.results.filter(
      (r) => (documentFilter === "all" || r.document_title === documentFilter) && r.similarity_score >= minConfidence
    );
    const sorted = [...rows];
    if (sortKey === "score") sorted.sort((a, b) => b.similarity_score - a.similarity_score);
    else if (sortKey === "document") sorted.sort((a, b) => a.document_title.localeCompare(b.document_title));
    else sorted.sort((a, b) => a.rank - b.rank);
    return sorted;
  }, [data.results, documentFilter, minConfidence, sortKey]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-4 rounded-md border border-border bg-muted/30 p-3">
        <div className="space-y-1">
          <Label className="text-[11px] font-normal text-muted-foreground">Document</Label>
          <Select value={documentFilter} onValueChange={setDocumentFilter}>
            <SelectTrigger className="h-8 w-48 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All documents ({data.results.length})</SelectItem>
              {documents.map((title) => (
                <SelectItem key={title} value={title}>
                  {title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label htmlFor="min-confidence" className="text-[11px] font-normal text-muted-foreground">
            Min. confidence (this view)
          </Label>
          <div className="flex items-center gap-2">
            <input
              id="min-confidence"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="h-8 accent-primary"
            />
            <span className="font-mono text-xs text-muted-foreground">{minConfidence.toFixed(2)}</span>
          </div>
        </div>

        <div className="space-y-1">
          <Label className="flex items-center gap-1 text-[11px] font-normal text-muted-foreground">
            <ArrowUpDown className="h-3 w-3" /> Sort by
          </Label>
          <Select value={sortKey} onValueChange={(v) => setSortKey(v as SortKey)}>
            <SelectTrigger className="h-8 w-36 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="rank">Original rank</SelectItem>
              <SelectItem value="score">Similarity score</SelectItem>
              <SelectItem value="document">Document title</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <p className="ml-auto text-xs text-muted-foreground">
          Showing {filtered.length} of {data.results.length}
        </p>
      </div>

      {filtered.map((r) => (
        <ResultCard key={r.chunk_id} result={r} query={data.query} />
      ))}
      {filtered.length === 0 && (
        <p className="rounded-lg border border-dashed border-border py-8 text-center text-sm text-muted-foreground">
          {data.results.length === 0
            ? "No chunks passed the similarity threshold. Try lowering it in the search bar above."
            : "No chunks match these filters. Try widening them."}
        </p>
      )}
    </div>
  );
}

function HighlightedText({ text, query }: { text: string; query: string }) {
  const segments = splitForHighlight(text, query);
  return (
    <>
      {segments.map((seg, i) =>
        seg.match ? (
          <mark key={i} className="rounded-sm bg-warning/30 px-0.5 text-foreground">
            {seg.text}
          </mark>
        ) : (
          <React.Fragment key={i}>{seg.text}</React.Fragment>
        )
      )}
    </>
  );
}

function ResultCard({ result, query }: { result: RankedResultOut; query: string }) {
  const [expanded, setExpanded] = React.useState(false);
  const pct = Math.round(Math.max(0, Math.min(1, result.similarity_score)) * 100);
  const isLong = result.chunk_text.length > CHUNK_PREVIEW_LENGTH;
  const displayText = expanded || !isLong ? result.chunk_text : `${result.chunk_text.slice(0, CHUNK_PREVIEW_LENGTH)}…`;

  function copyAsCitation() {
    const page = result.page_number !== null ? `, p.${result.page_number}` : "";
    navigator.clipboard.writeText(`"${result.chunk_text}" — ${result.document_title}${page}`);
    toast.success("Citation copied");
  }

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

        <p className="text-sm leading-relaxed text-foreground">
          <HighlightedText text={displayText} query={query} />
        </p>
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-1 flex items-center gap-1 text-[11px] font-medium text-primary hover:underline"
          >
            {expanded ? (
              <>
                <ChevronUp className="h-3 w-3" /> Show less
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" /> Show full chunk
              </>
            )}
          </button>
        )}

        <div className="mt-3 space-y-1.5">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} aria-hidden="true" />
          </div>
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] text-muted-foreground">{result.reason}</p>
            <Button variant="ghost" size="sm" className="h-6 gap-1 px-1.5 text-[11px]" onClick={copyAsCitation}>
              <Copy className="h-3 w-3" /> Copy as citation
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
