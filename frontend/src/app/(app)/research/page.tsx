"use client";

import * as React from "react";

import { ResearchQueryForm } from "@/features/research/components/research-query-form";
import { ResearchAnswer } from "@/features/research/components/research-answer";
import type { ResearchAnswerOut } from "@/types/research";

export default function ResearchPage() {
  const [result, setResult] = React.useState<ResearchAnswerOut | null>(null);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Research</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask a question grounded in your documents and memory — with citations and a full reasoning trace.
        </p>
      </div>
      <ResearchQueryForm onResult={setResult} />
      {result && <ResearchAnswer result={result} />}
    </div>
  );
}
