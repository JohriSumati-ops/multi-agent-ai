"use client";

import * as React from "react";
import {
  MessageSquareText,
  Database,
  BrainCircuit,
  FileCode2,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  Quote,
  CheckCircle2,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { parseExplainabilityPayload } from "@/features/research/reasoning-payload";
import type { ExplainResponse } from "@/types/research";

interface Stage {
  icon: LucideIcon;
  title: string;
  detail: React.ReactNode;
  tone: "neutral" | "success" | "warning";
}

export function ReasoningPipeline({ data }: { data: ExplainResponse }) {
  const payload = parseExplainabilityPayload(data.explainability_payload);
  const isGrounded = payload.grounding?.is_grounded ?? null;

  const stages: Stage[] = [
    {
      icon: MessageSquareText,
      title: "Query",
      detail: <p className="text-foreground">&ldquo;{data.query_text}&rdquo;</p>,
      tone: "neutral",
    },
    {
      icon: Database,
      title: "Retrieved context",
      detail: (
        <p>
          {data.retrieved_chunk_ids.length} chunk{data.retrieved_chunk_ids.length === 1 ? "" : "s"} retrieved
          {payload.excluded_count > 0 && (
            <>
              {" "}
              · {payload.excluded_count} excluded (
              {Object.entries(payload.excluded_reasons)
                .slice(0, 2)
                .map(([, reason]) => reason)
                .join(", ") || "below threshold"}
              )
            </>
          )}
        </p>
      ),
      tone: "neutral",
    },
    {
      icon: BrainCircuit,
      title: "Memory context",
      detail: <p>{data.memory_references.length} memory reference{data.memory_references.length === 1 ? "" : "s"} included</p>,
      tone: "neutral",
    },
    {
      icon: FileCode2,
      title: "Prompt construction",
      detail: <p>{data.prompt_tokens !== null ? `${data.prompt_tokens} prompt tokens` : "Token count unavailable"}</p>,
      tone: "neutral",
    },
    {
      icon: Sparkles,
      title: "LLM reasoning",
      detail: (
        <p>
          {data.completion_tokens !== null ? `${data.completion_tokens} completion tokens` : "Generated a response"}
          {" · "}
          {Math.round(data.confidence * 100)}% confidence
        </p>
      ),
      tone: "neutral",
    },
    {
      icon: payload.synthesis && payload.synthesis.conflicts.length > 0 ? ShieldAlert : ShieldCheck,
      title: "Validation & grounding",
      detail: (
        <div className="space-y-1">
          {isGrounded !== null && (
            <p>
              {isGrounded
                ? "Every cited source was verified against the retrieved context."
                : `${payload.grounding?.fabricated_chunk_ids.length ?? 0} citation(s) could not be verified.`}
            </p>
          )}
          {payload.synthesis && (
            <p className="text-muted-foreground">
              {payload.synthesis.evidence_count} evidence item{payload.synthesis.evidence_count === 1 ? "" : "s"} synthesized
              {payload.synthesis.conflicts.length > 0 && `, ${payload.synthesis.conflicts.length} potential conflict(s)`}
            </p>
          )}
        </div>
      ),
      tone: isGrounded === false ? "warning" : "success",
    },
    {
      icon: Quote,
      title: "Citation injection",
      detail: <p>{payload.citations.length} citation{payload.citations.length === 1 ? "" : "s"} attached to the answer</p>,
      tone: "neutral",
    },
    {
      icon: CheckCircle2,
      title: "Final response",
      detail: <p>{Math.round(data.confidence * 100)}% overall confidence · {data.latency_ms ?? "?"}ms</p>,
      tone: "success",
    },
  ];

  return (
    <div className="space-y-0">
      {stages.map((stage, i) => (
        <div key={stage.title} className="relative flex gap-3 pb-5 last:pb-0">
          {i < stages.length - 1 && (
            <span className="absolute left-[15px] top-8 h-[calc(100%-1.5rem)] w-px bg-border" aria-hidden="true" />
          )}
          <div
            className={cn(
              "z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
              stage.tone === "success" && "border-success/40 bg-success/10 text-success",
              stage.tone === "warning" && "border-warning/40 bg-warning/10 text-warning",
              stage.tone === "neutral" && "border-border bg-muted text-muted-foreground"
            )}
          >
            <stage.icon className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1 pt-1">
            <div className="flex items-center gap-2">
              <p className="text-xs font-semibold text-foreground">{stage.title}</p>
              {stage.title === "Validation & grounding" && isGrounded !== null && (
                <Badge variant={isGrounded ? "success" : "warning"}>{isGrounded ? "grounded" : "check"}</Badge>
              )}
            </div>
            <div className="mt-0.5 text-xs text-muted-foreground">{stage.detail}</div>
          </div>
        </div>
      ))}

      {payload.synthesis && payload.synthesis.conflicts.length > 0 && (
        <div className="mt-2 space-y-1.5 rounded-md border border-warning/30 bg-warning/10 p-3">
          <p className="text-xs font-semibold text-warning">Potential conflicts detected</p>
          {payload.synthesis.conflicts.map((c, i) => (
            <p key={i} className="text-xs text-warning/90">
              {c.note} <span className="text-muted-foreground">({c.shared_terms.join(", ")})</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
