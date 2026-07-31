"use client";

import * as React from "react";

import {
  getSessions,
  getActiveSessionId,
  setActiveSessionId,
  createSession,
  addTurn,
  renameSession,
  togglePinSession,
  deleteSession,
  duplicateSession,
  subscribeToSessions,
  type WorkspaceSession,
  type ConversationTurn,
} from "@/features/workspace/session-store";

export function useWorkspaceSessions() {
  const [sessions, setSessions] = React.useState<WorkspaceSession[]>([]);
  const [activeId, setActiveIdState] = React.useState<string | null>(null);

  const refresh = React.useCallback(() => {
    setSessions(getSessions());
    setActiveIdState(getActiveSessionId());
  }, []);

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync from localStorage, an SSR-unavailable external source; can't be computed during render.
    refresh();
    return subscribeToSessions(refresh);
  }, [refresh]);

  const activeSession = React.useMemo(
    () => sessions.find((s) => s.id === activeId) ?? null,
    [sessions, activeId]
  );

  const newSession = React.useCallback((title?: string) => createSession(title), []);
  const selectSession = React.useCallback((id: string | null) => setActiveSessionId(id), []);
  const appendTurn = React.useCallback(
    (sessionId: string, turn: Omit<ConversationTurn, "id" | "timestamp">) => addTurn(sessionId, turn),
    []
  );

  return {
    sessions,
    activeId,
    activeSession,
    newSession,
    selectSession,
    appendTurn,
    rename: renameSession,
    togglePin: togglePinSession,
    remove: deleteSession,
    duplicate: duplicateSession,
  };
}
