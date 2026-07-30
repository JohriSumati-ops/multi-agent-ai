"use client";

import * as React from "react";

import { getActivityLog, subscribeToActivityLog, type ActivityEntry } from "@/features/analytics/activity-log";

export function useActivityLog(): ActivityEntry[] {
  const [entries, setEntries] = React.useState<ActivityEntry[]>([]);

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync from localStorage, an SSR-unavailable external source; can't be computed during render.
    setEntries(getActivityLog());
    return subscribeToActivityLog(() => setEntries(getActivityLog()));
  }, []);

  return entries;
}
