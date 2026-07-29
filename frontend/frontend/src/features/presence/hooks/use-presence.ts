"use client";

import * as React from "react";

import { generatePresenceTick } from "@/features/presence/services/mock-presence";
import type { PresenceState } from "@/types/collaboration";

const TICK_INTERVAL_MS = 8_000;

export function usePresence() {
  const [presence, setPresence] = React.useState<PresenceState[]>(() => generatePresenceTick());

  React.useEffect(() => {
    const interval = setInterval(() => setPresence(generatePresenceTick()), TICK_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  return presence;
}