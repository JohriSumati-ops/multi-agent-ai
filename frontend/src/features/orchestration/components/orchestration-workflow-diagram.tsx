"use client";

import * as React from "react";
import { CheckCircle2, XCircle, Clock, GitBranch } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ExecuteGoalResponse, TaskTimelineEntryOut } from "@/types/orchestration";

const STATUS_BAR: Record<string, string> = {
  succeeded: "bg-success",
  completed: "bg-success",
  failed: "bg-destructive",
  running: "bg-info",
  pending: "bg-muted-foreground/40",
};

const STATUS_ICON: Record<string, React.ElementType> = {
  succeeded: CheckCircle2,
  completed: CheckCircle2,
  failed: XCircle,
  running: Clock,
  pending: Clock,
};

function timeBounds(timeline: TaskTimelineEntryOut[]): { start: number; end: number } {
  const starts = timeline
    .map((t) => (t.started_at ? new Date(t.started_at).getTime() : null))
    .filter((v): v is number => v !== null);
  const ends = timeline
    .map((t) => (t.completed_at ? new Date(t.completed_at).getTime() : t.started_at ? new Date(t.started_at).getTime() : null))
    .filter((v): v is number => v !== null);
  if (starts.length === 0) return { start: 0, end: 1 };
  const start = Math.min(...starts);
  const end = Math.max(...ends, start + 1);
  return { start, end };
}

/**
 * Real Gantt-style rendering of a single execution's task timeline — bar
 * position/width are computed directly from the trace's own
 * `started_at`/`completed_at`, not estimated.
 */
export function OrchestrationWorkflowDiagram({ result }: { result: ExecuteGoalResponse }) {
  const { trace } = result;
  const { start, end } = timeBounds(trace.timeline);
  const span = Math.max(end - start, 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <GitBranch className="h-3.5 w-3.5" /> Execution workflow
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        <div className="rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Supervisor</span> planned {trace.timeline.length} task
          {trace.timeline.length === 1 ? "" : "s"} for goal &ldquo;{trace.goal}&rdquo;. {trace.overall_reason}
        </div>

        <div className="space-y-2.5">
          {trace.timeline.map((task) => {
            const Icon = STATUS_ICON[task.status] ?? Clock;
            const startedAt = task.started_at ? new Date(task.started_at).getTime() : null;
            const leftPct = startedAt !== null ? ((startedAt - start) / span) * 100 : 0;
            const widthPct = task.duration_ms !== null ? Math.max((task.duration_ms / span) * 100, 1.5) : 1.5;
            const notSelectedReason = trace.agents_not_selected[task.capability];

            return (
              <div key={task.task_id} className="space-y-1">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="flex items-center gap-1.5 font-medium text-foreground">
                    <Icon
                      className={cn(
                        "h-3.5 w-3.5",
                        task.status === "failed"
                          ? "text-destructive"
                          : task.status === "succeeded" || task.status === "completed"
                            ? "text-success"
                            : "text-muted-foreground"
                      )}
                    />
                    {task.capability}
                    {task.agent_name && <span className="font-normal text-muted-foreground">({task.agent_name})</span>}
                  </span>
                  <span className="font-mono text-muted-foreground">
                    {task.duration_ms !== null ? `${task.duration_ms}ms` : "—"}
                  </span>
                </div>
                <div
                  className="relative h-2.5 w-full overflow-hidden rounded-full bg-muted"
                  role="img"
                  aria-label={`${task.capability}: ${task.status}`}
                >
                  <div
                    className={cn("absolute top-0 h-full rounded-full", STATUS_BAR[task.status] ?? "bg-muted-foreground/40")}
                    style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                  />
                </div>
                {trace.agent_selection_reasons[task.capability] && (
                  <p className="pl-5 text-[11px] text-muted-foreground">{trace.agent_selection_reasons[task.capability]}</p>
                )}
                {notSelectedReason && (
                  <p className="pl-5 text-[11px] text-muted-foreground">Not selected as fallback: {notSelectedReason}</p>
                )}
              </div>
            );
          })}
        </div>

        {Object.keys(trace.context_sources).length > 0 && (
          <div className="flex flex-wrap gap-1.5 border-t border-border pt-3">
            {Object.entries(trace.context_sources).map(([source, count]) => (
              <Badge key={source} variant="outline">
                {source}: {count}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
