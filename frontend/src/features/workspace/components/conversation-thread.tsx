"use client";

import * as React from "react";
import { toast } from "sonner";
import { Copy, Download, ListTree, AlertTriangle, MessageSquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/ui/empty-state";
import { MarkdownAnswer } from "@/features/workspace/components/markdown-answer";
import { CitationPanel } from "@/features/research/components/citation-panel";
import { ExplainabilityPanel } from "@/features/research/components/explainability-panel";
import { turnToMarkdown, turnToText, downloadTextFile } from "@/features/workspace/export";
import type { ConversationTurn } from "@/features/workspace/session-store";

interface ConversationThreadProps {
  turns: ConversationTurn[];
  isPending: boolean;
}

export function ConversationThread({ turns, isPending }: ConversationThreadProps) {
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, isPending]);

  if (turns.length === 0 && !isPending) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="Start a research conversation"
        description="Ask a question below — it runs against your embedded documents and memory in real time."
        className="h-full"
      />
    );
  }

  return (
    <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
      {turns.map((turn) => (
        <TurnBubbles key={turn.id} turn={turn} />
      ))}
      {isPending && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}

function TurnBubbles({ turn }: { turn: ConversationTurn }) {
  const [showTrace, setShowTrace] = React.useState(false);

  function copyAnswer() {
    navigator.clipboard.writeText(turn.result.answer ?? "");
    toast.success("Answer copied");
  }

  function exportTurn(format: "markdown" | "text" | "json") {
    if (format === "json") {
      downloadTextFile(JSON.stringify(turn, null, 2), "response.json", "application/json");
    } else if (format === "markdown") {
      downloadTextFile(turnToMarkdown(turn), "response.md", "text/markdown");
    } else {
      downloadTextFile(turnToText(turn), "response.txt", "text/plain");
    }
  }

  return (
    <div className="space-y-2">
      {/* User query bubble */}
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
          {turn.query}
        </div>
      </div>

      {/* Assistant answer bubble */}
      <div className="flex justify-start">
        <div className="w-full max-w-[85%] space-y-2 rounded-2xl rounded-bl-sm border border-border bg-surface px-4 py-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="text-[10px]">
              {turn.mode}
            </Badge>
            {turn.result.confidence !== null && (
              <Badge variant="outline" className="text-[10px]">
                {Math.round(turn.result.confidence * 100)}% confidence
              </Badge>
            )}
            {turn.result.is_grounded === false && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <AlertTriangle className="h-3 w-3" /> ungrounded
              </Badge>
            )}
            {!turn.result.used_llm && (
              <Badge variant="secondary" className="text-[10px]">
                retrieval-only
              </Badge>
            )}
          </div>

          {turn.result.answer ? (
            <MarkdownAnswer content={turn.result.answer} />
          ) : (
            <p className="text-sm text-muted-foreground">No answer was generated for this query.</p>
          )}

          <div className="flex items-center gap-1 border-t border-border pt-2">
            <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs" onClick={copyAnswer}>
              <Copy className="h-3 w-3" /> Copy
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
                  <Download className="h-3 w-3" /> Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onClick={() => exportTurn("markdown")}>As Markdown</DropdownMenuItem>
                <DropdownMenuItem onClick={() => exportTurn("text")}>As Text</DropdownMenuItem>
                <DropdownMenuItem onClick={() => exportTurn("json")}>As JSON</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            {turn.result.response_id && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 px-2 text-xs"
                onClick={() => setShowTrace((v) => !v)}
              >
                <ListTree className="h-3 w-3" /> {showTrace ? "Hide" : "Show"} reasoning
              </Button>
            )}
          </div>
        </div>
      </div>

      {turn.result.citations.length > 0 && (
        <div className="ml-0 max-w-[85%]">
          <CitationPanel citations={turn.result.citations} contextLabel={turn.query} />
        </div>
      )}

      {showTrace && turn.result.response_id && (
        <div className="max-w-[85%]">
          <ExplainabilityPanel responseId={turn.result.response_id} />
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm border border-border bg-surface px-4 py-3"
        role="status"
        aria-live="polite"
        aria-label="Thinking"
      >
        <span className="sr-only">Thinking…</span>
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
      </div>
    </div>
  );
}
