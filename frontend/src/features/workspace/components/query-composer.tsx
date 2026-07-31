"use client";

import * as React from "react";
import { Send, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import type { ResearchMode } from "@/features/research/hooks/use-research";

const MODE_OPTIONS: { value: ResearchMode; label: string; hint: string }[] = [
  { value: "query", label: "Research (with reasoning)", hint: "Full pipeline: retrieval, memory, grounded synthesis." },
  { value: "answer", label: "Direct answer", hint: "Faster, more literal answer to the question." },
  { value: "summarize", label: "Summarize", hint: "Summarizes what's retrieved rather than answering a question." },
];

interface QueryComposerProps {
  onSubmit: (query: string, mode: ResearchMode, documentId: string | null) => void;
  isPending: boolean;
}

export function QueryComposer({ onSubmit, isPending }: QueryComposerProps) {
  const [value, setValue] = React.useState("");
  const [mode, setMode] = React.useState<ResearchMode>("query");
  const [documentId, setDocumentId] = React.useState<string>("all");
  const { data: documents } = useDocuments();
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || isPending) return;
    onSubmit(trimmed, mode, documentId === "all" ? null : documentId);
    setValue("");
    requestAnimationFrame(() => textareaRef.current?.focus());
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="space-y-2 border-t border-border bg-background p-3">
      <div className="flex items-end gap-2">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask a question about your documents… (⌘/Ctrl + Enter to send)"
          className="min-h-[52px] resize-none text-sm"
          rows={2}
        />
        <Button type="button" onClick={submit} disabled={isPending || !value.trim()} className="h-[52px] shrink-0">
          {isPending ? <Loader2 className="animate-spin" /> : <Send />}
          <span className="hidden sm:inline">Send</span>
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Select value={mode} onValueChange={(v) => setMode(v as ResearchMode)}>
          <SelectTrigger className="h-7 w-auto gap-1.5 border-none bg-transparent px-0 text-xs text-muted-foreground shadow-none hover:text-foreground">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MODE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                <div>
                  <p>{opt.label}</p>
                  <p className="text-[11px] text-muted-foreground">{opt.hint}</p>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-muted-foreground/40">·</span>
        <Select value={documentId} onValueChange={setDocumentId}>
          <SelectTrigger className="h-7 w-auto max-w-[220px] gap-1.5 border-none bg-transparent px-0 text-xs text-muted-foreground shadow-none hover:text-foreground">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All documents</SelectItem>
            {documents?.map((doc) => (
              <SelectItem key={doc.id} value={doc.id}>
                {doc.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
