"use client";

import type { ElementType } from "react";
import { CheckCircle2, XCircle, Bot, Zap, Clock, Percent, History } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { useOrchestrationHealth } from "@/features/orchestration/hooks/use-orchestration";
import { useAgentStats } from "@/features/orchestration/hooks/use-agent-stats";
import type { CapabilityOut } from "@/types/orchestration";

interface AgentInspectorDialogProps {
  capability: CapabilityOut | null;
  onOpenChange: (open: boolean) => void;
}

export function AgentInspectorDialog({ capability, onOpenChange }: AgentInspectorDialogProps) {
  const { data: health } = useOrchestrationHealth();
  const stats = useAgentStats();

  if (!capability) return null;

  const h = health?.find((entry) => entry.capability === capability.capability);
  const s = stats[capability.capability];
  const successRate = s && s.executionCount > 0 ? Math.round((s.successCount / s.executionCount) * 100) : null;
  const avgLatency = s && s.executionCount > 0 ? Math.round(s.totalDurationMs / s.executionCount) : null;

  return (
    <Dialog open={!!capability} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-mono">
            <Bot className="h-4 w-4" /> {capability.capability}
          </DialogTitle>
          <DialogDescription>{capability.description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">agent: {capability.agent_name}</Badge>
            {h && (
              <Badge variant={h.healthy ? "success" : "destructive"} className="gap-1">
                {h.healthy ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                {h.healthy ? "healthy" : "down"}
              </Badge>
            )}
          </div>

          {h && !h.healthy && (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
              {h.detail}
            </p>
          )}

          {capability.depends_on.length > 0 && (
            <div>
              <p className="text-xs font-medium text-foreground">Dependencies</p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">{capability.depends_on.join(", ")}</p>
            </div>
          )}

          <div>
            <p className="text-xs font-medium text-foreground">Session stats</p>
            <p className="mb-2 text-[11px] text-muted-foreground">
              From goal executions run in this browser — the backend keeps no execution history to draw on.
            </p>
            {!s ? (
              <p className="text-xs text-muted-foreground">Not yet used in this browser session.</p>
            ) : (
              <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                <Stat icon={Zap} label="Executions" value={s.executionCount} />
                <Stat icon={Percent} label="Success rate" value={successRate !== null ? `${successRate}%` : "—"} />
                <Stat icon={Clock} label="Avg latency" value={avgLatency !== null ? `${avgLatency}ms` : "—"} />
                <Stat
                  icon={History}
                  label="Last run"
                  value={s.lastExecutedAt ? new Date(s.lastExecutedAt).toLocaleTimeString() : "—"}
                />
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Stat({ icon: Icon, label, value }: { icon: ElementType; label: string; value: string | number }) {
  return (
    <div className="space-y-0.5">
      <p className="flex items-center gap-1 text-muted-foreground">
        <Icon className="h-3 w-3" /> {label}
      </p>
      <p className="font-mono font-medium text-foreground">{value}</p>
    </div>
  );
}
