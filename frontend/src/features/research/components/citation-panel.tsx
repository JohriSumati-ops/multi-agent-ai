"use client";

import * as React from "react";
import { toast } from "sonner";
import { Quote, Copy, Download, BookOpen, BrainCircuit } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { downloadTextFile } from "@/features/workspace/export";
import type { CitationOut } from "@/types/research";

interface CitationPanelProps {
  citations: CitationOut[];
  /** Used as the export filename stem and shown in the export payload. */
  contextLabel?: string;
}

function groupKey(c: CitationOut): string {
  return c.is_memory ? "__memory__" : (c.document_title ?? "Unknown source");
}

export function CitationPanel({ citations, contextLabel = "citations" }: CitationPanelProps) {
  const groups = React.useMemo(() => {
    const map = new Map<string, CitationOut[]>();
    for (const c of citations) {
      const key = groupKey(c);
      map.set(key, [...(map.get(key) ?? []), c]);
    }
    return Array.from(map.entries());
  }, [citations]);

  if (citations.length === 0) return null;

  function copyCitation(c: CitationOut) {
    const src = c.is_memory ? "memory" : (c.document_title ?? "unknown source");
    const page = c.page_number !== null ? `, p.${c.page_number}` : "";
    navigator.clipboard.writeText(`${c.citation_text} (${src}${page})`);
    toast.success("Citation copied");
  }

  function exportCitations(format: "markdown" | "json") {
    const slug = contextLabel.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "citations";
    if (format === "json") {
      downloadTextFile(JSON.stringify(citations, null, 2), `${slug}-citations.json`, "application/json");
      return;
    }
    const lines = citations.map((c) => {
      const src = c.is_memory ? "memory" : (c.document_title ?? "unknown source");
      const page = c.page_number !== null ? `, p.${c.page_number}` : "";
      return `- ${c.citation_text} (${src}${page})`;
    });
    downloadTextFile(`# Citations — ${contextLabel}\n\n${lines.join("\n")}\n`, `${slug}-citations.md`, "text/markdown");
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-1.5">
          <Quote className="h-3.5 w-3.5" /> Citations
          <span className="font-mono text-xs font-normal text-muted-foreground">({citations.length})</span>
        </CardTitle>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <Download /> Export
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => exportCitations("markdown")}>As Markdown</DropdownMenuItem>
            <DropdownMenuItem onClick={() => exportCitations("json")}>As JSON</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        {groups.map(([key, items]) => (
          <div key={key} className="space-y-1.5">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              {key === "__memory__" ? (
                <>
                  <BrainCircuit className="h-3 w-3" /> Memory
                </>
              ) : (
                <>
                  <BookOpen className="h-3 w-3" /> {key}
                </>
              )}
            </p>
            {items.map((c, i) => (
              <div
                key={`${c.chunk_id}-${i}`}
                className="group flex items-start justify-between gap-2 rounded-md bg-muted/50 p-2.5 text-xs"
              >
                <div>
                  <p className="text-foreground">{c.citation_text}</p>
                  {c.page_number !== null && <p className="mt-0.5 text-muted-foreground">page {c.page_number}</p>}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
                  onClick={() => copyCitation(c)}
                  aria-label="Copy citation"
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
