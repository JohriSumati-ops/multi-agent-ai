"use client";

import { CheckCircle2, XCircle, Clock, HelpCircle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ExecuteGoalResponse, TaskTimelineEntryOut } from "@/types/orchestration";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<string, { dot: string; badge: "success" | "destructive" | "info" | "muted" }> = {
  succeeded: { dot: "bg-success", badge: "success" },
  completed: { dot: "bg-success", badge: "success" },
  failed: { dot: "bg-destructive", badge: "destructive" },
  running: { dot: "bg-info animate-pulse", badge: "info" },
  pending: { dot: "bg-muted-foreground", badge: "muted" },
};

export function ExecutionTrace({ result }: { result: ExecuteGoalResponse }) {
  const { plan, trace } = result;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap items-center gap-4 p-4">
          <div>
            <p className="text-xs text-muted-foreground">Plan</p>
            <p className="font-mono text-sm text-foreground">{plan.plan_id}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Tasks</p>
            <p className="text-sm text-foreground">
              {plan.succeeded} succeeded, {plan.failed} failed, of {plan.task_count}
            </p>
          </div>
          {trace.overall_confidence !== null && (
            <div>
              <p className="text-xs text-muted-foreground">Confidence</p>
              <p className="text-sm text-foreground">{(trace.overall_confidence * 100).toFixed(0)}%</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Execution trace</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <ol className="relative space-y-5 pl-5">
            <span
              className="absolute bottom-2 left-[5px] top-2 w-px border-l border-dashed border-border"
              aria-hidden="true"
            />
            {trace.timeline.map((entry) => (
              <TimelineNode key={entry.task_id} entry={entry} />
            ))}
          </ol>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Agent selection</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            {Object.entries(trace.agent_selection_reasons).map(([capability, reason]) => (
              <div key={capability} className="text-xs">
                <span className="font-mono font-medium text-foreground">{capability}</span>
                <p className="text-muted-foreground">{reason}</p>
              </div>
            ))}
            {Object.entries(trace.agents_not_selected).map(([agent, reason]) => (
              <div key={agent} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <HelpCircle className="mt-0.5 h-3 w-3 shrink-0" />
                <span>
                  <span className="font-mono">{agent}</span> not selected — {reason}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Explanation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <p className="text-sm text-foreground">{trace.overall_reason}</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(trace.context_sources).map(([source, count]) => (
                <Badge key={source} variant="outline" className="font-mono">
                  {source}: {count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function TimelineNode({ entry }: { entry: TaskTimelineEntryOut }) {
  const style = STATUS_STYLE[entry.status] ?? STATUS_STYLE.pending;
  return (
    <li className="relative">
      <span
        className={cn("absolute -left-5 top-1 h-2.5 w-2.5 rounded-full ring-4 ring-background", style.dot)}
        aria-hidden="true"
      />
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm font-medium text-foreground">{entry.capability}</span>
        <Badge variant={style.badge}>{entry.status}</Badge>
        {entry.agent_name && (
          <span className="text-xs text-muted-foreground">via {entry.agent_name}</span>
        )}
      </div>
      <div className="mt-0.5 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
        {entry.duration_ms !== null && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" /> {entry.duration_ms}ms
          </span>
        )}
        {entry.confidence !== null && <span>confidence {entry.confidence.toFixed(2)}</span>}
        {entry.status === "failed" ? (
          <XCircle className="h-3 w-3 text-destructive" />
        ) : (
          entry.completed_at && <CheckCircle2 className="h-3 w-3 text-success" />
        )}
      </div>
    </li>
  );
}
