"use client";

import * as React from "react";
import { Loader2, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useCapabilities, useExecuteGoal } from "@/features/orchestration/hooks/use-orchestration";
import { ApiError } from "@/types/api";
import type { ExecuteGoalResponse } from "@/types/orchestration";
import { cn } from "@/lib/utils";

export function GoalExecutionForm({ onResult }: { onResult: (result: ExecuteGoalResponse) => void }) {
  const { data: capabilities } = useCapabilities();
  const { mutate: execute, isPending, error } = useExecuteGoal();
  const [goal, setGoal] = React.useState("");
  const [selected, setSelected] = React.useState<Set<string>>(new Set());

  function toggle(capability: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(capability)) next.delete(capability);
      else next.add(capability);
      return next;
    });
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim() || selected.size === 0) return;
    execute(
      { goal: goal.trim(), capabilities: Array.from(selected) },
      { onSuccess: (result) => onResult(result) }
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="goal">Goal</Label>
        <Input
          id="goal"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g. Summarize the uploaded research paper and store key findings"
          maxLength={500}
        />
      </div>

      <div className="space-y-1.5">
        <Label>Capabilities</Label>
        <div className="flex flex-wrap gap-2">
          {capabilities?.map((cap) => {
            const active = selected.has(cap.capability);
            return (
              <button
                key={cap.capability}
                type="button"
                onClick={() => toggle(cap.capability)}
                className={cn(
                  "rounded-full border px-3 py-1 font-mono text-xs transition-colors",
                  active
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-input text-muted-foreground hover:border-accent hover:text-foreground"
                )}
              >
                {cap.capability}
              </button>
            );
          })}
        </div>
        {selected.size === 0 && (
          <p className="text-[11px] text-muted-foreground">Select at least one capability.</p>
        )}
      </div>

      {error && (
        <ErrorBanner message={error instanceof ApiError ? error.message : "Execution failed."} />
      )}

      <Button type="submit" disabled={isPending || !goal.trim() || selected.size === 0}>
        {isPending ? <Loader2 className="animate-spin" /> : <Play />}
        Execute goal
      </Button>
    </form>
  );
}
