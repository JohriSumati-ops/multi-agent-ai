"use client";

import * as React from "react";

import { getAgentStats, subscribeToAgentStats, type AgentStats } from "@/features/orchestration/agent-stats";

export function useAgentStats(): Record<string, AgentStats> {
  const [stats, setStats] = React.useState<Record<string, AgentStats>>({});

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync from localStorage, an SSR-unavailable external source; can't be computed during render.
    setStats(getAgentStats());
    return subscribeToAgentStats(() => setStats(getAgentStats()));
  }, []);

  return stats;
}
