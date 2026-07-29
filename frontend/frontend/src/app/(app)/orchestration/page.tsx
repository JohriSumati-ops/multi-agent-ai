"use client";

import * as React from "react";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CapabilitiesList } from "@/features/orchestration/components/capabilities-list";
import { GoalExecutionForm } from "@/features/orchestration/components/goal-execution-form";
import { ExecutionTrace } from "@/features/orchestration/components/execution-trace";
import type { ExecuteGoalResponse } from "@/types/orchestration";

export default function OrchestrationPage() {
  const [result, setResult] = React.useState<ExecuteGoalResponse | null>(null);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Agent orchestration</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Registered agents, capability-driven execution, and the decision trace behind every run.
        </p>
      </div>

      <Tabs defaultValue="execute">
        <TabsList>
          <TabsTrigger value="execute">Execute</TabsTrigger>
          <TabsTrigger value="agents">Registered agents</TabsTrigger>
        </TabsList>
        <TabsContent value="execute" className="space-y-6">
          <GoalExecutionForm onResult={setResult} />
          {result && <ExecutionTrace result={result} />}
        </TabsContent>
        <TabsContent value="agents">
          <CapabilitiesList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
