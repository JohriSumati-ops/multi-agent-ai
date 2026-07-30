"use client";

import * as React from "react";
import { Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import { useResearchQuery } from "@/features/research/hooks/use-research";
import { ApiError } from "@/types/api";
import type { ResearchAnswerOut } from "@/types/research";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function ResearchQueryForm({ onResult }: { onResult: (result: ResearchAnswerOut) => void }) {
  const [query, setQuery] = React.useState("");
  const [documentId, setDocumentId] = React.useState<string | undefined>(undefined);
  const { data: documents } = useDocuments();
  const { mutate: ask, isPending, error } = useResearchQuery();

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    ask({ query: query.trim(), document_id: documentId ?? null }, { onSuccess: onResult });
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="space-y-1.5">
        <Label htmlFor="research-query">Research question</Label>
        <Input
          id="research-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What does the source material say about…?"
        />
      </div>

      <div className="flex items-end gap-3">
        <div className="flex-1 space-y-1.5">
          <Label>Scope (optional)</Label>
          <Select value={documentId ?? "any"} onValueChange={(v) => setDocumentId(v === "any" ? undefined : v)}>
            <SelectTrigger>
              <SelectValue placeholder="All documents" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">All documents</SelectItem>
              {documents?.map((doc) => (
                <SelectItem key={doc.id} value={doc.id}>
                  {doc.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button type="submit" disabled={isPending || !query.trim()}>
          {isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
          Ask
        </Button>
      </div>

      {error && <ErrorBanner message={error instanceof ApiError ? error.message : "Query failed."} />}
    </form>
  );
}
