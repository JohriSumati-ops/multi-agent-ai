"use client";

import * as React from "react";
import { ShieldCheck, ShieldAlert, Quote, BookOpen, Info } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExplainabilityPanel } from "@/features/research/components/explainability-panel";
import type { ResearchAnswerOut } from "@/types/research";

export function ResearchAnswer({ result }: { result: ResearchAnswerOut }) {
  const [explaining, setExplaining] = React.useState(false);
  const confidencePct = result.confidence !== null ? Math.round(result.confidence * 100) : null;

  return (
    <div className="space-y-4">
      {!result.used_llm && result.fallback_reason && (
        <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>Fell back to retrieval-only mode: {result.fallback_reason}</span>
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Answer</CardTitle>
            <div className="flex items-center gap-2">
              {result.is_grounded !== null && (
                <Badge variant={result.is_grounded ? "success" : "warning"} className="gap-1">
                  {result.is_grounded ? <ShieldCheck className="h-3 w-3" /> : <ShieldAlert className="h-3 w-3" />}
                  {result.is_grounded ? "grounded" : "ungrounded"}
                </Badge>
              )}
              {confidencePct !== null && <Badge variant="outline">{confidencePct}% confidence</Badge>}
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="whitespace-pre-line text-sm leading-relaxed text-foreground">
            {result.answer ?? "No answer was generated."}
          </p>
          {result.reasoning_summary && (
            <p className="mt-3 border-t border-border pt-3 text-xs text-muted-foreground">
              {result.reasoning_summary}
            </p>
          )}
        </CardContent>
      </Card>

      {result.citations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5">
              <Quote className="h-3.5 w-3.5" /> Citations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            {result.citations.map((c, i) => (
              <div key={i} className="rounded-md bg-muted/50 p-2.5 text-xs">
                <p className="text-foreground">{c.citation_text}</p>
                <p className="mt-1 text-muted-foreground">
                  {c.is_memory ? "from memory" : c.document_title}
                  {c.page_number !== null && ` · page ${c.page_number}`}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {result.sources_used.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5" /> Sources used
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2 pt-0">
            {result.sources_used.map((s, i) => (
              <Badge key={i} variant="outline">
                {s.document_title} · {s.relevance}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {result.latency_ms}ms
          {result.prompt_tokens !== null && ` · ${result.prompt_tokens} prompt tokens`}
          {result.completion_tokens !== null && ` · ${result.completion_tokens} completion tokens`}
        </span>
        {result.response_id && (
          <Button variant="link" size="sm" className="h-auto p-0" onClick={() => setExplaining((v) => !v)}>
            {explaining ? "Hide" : "Show"} full explainability trace
          </Button>
        )}
      </div>

      {explaining && result.response_id && <ExplainabilityPanel responseId={result.response_id} />}
    </div>
  );
}
