export interface ExecuteGoalRequest {
  goal: string;
  capabilities: string[];
  payload?: Record<string, unknown>;
  request_text?: string | null;
}

export interface TaskTimelineEntryOut {
  task_id: string;
  capability: string;
  agent_name: string | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  confidence: number | null;
}

export interface ExecutionPlanOut {
  plan_id: string;
  goal: string;
  task_count: number;
  succeeded: number;
  failed: number;
}

export interface DecisionTraceOut {
  plan_id: string;
  goal: string;
  timeline: TaskTimelineEntryOut[];
  agent_selection_reasons: Record<string, string>;
  agents_not_selected: Record<string, string>;
  context_sources: Record<string, number>;
  overall_reason: string;
  overall_confidence: number | null;
}

export interface ExecuteGoalResponse {
  plan: ExecutionPlanOut;
  trace: DecisionTraceOut;
}

export interface CapabilityOut {
  capability: string;
  agent_name: string;
  depends_on: string[];
  description: string;
}

export interface HealthCheckOut {
  capability: string;
  healthy: boolean;
  detail: string;
}
