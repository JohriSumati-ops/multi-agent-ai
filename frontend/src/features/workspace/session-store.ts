/**
 * Research workspace sessions.
 *
 * The backend's `/research/*` endpoints are stateless single-shot
 * request/response — there is no conversation, session, or history
 * concept server-side (confirmed against `backend/api/routes/research.py`
 * and `schemas/research.py`: no `session_id` anywhere). "Saved
 * conversations" and "session switching" are therefore implemented
 * entirely client-side, in `localStorage`, the same honest pattern used
 * for Settings and search history. Each *turn* within a session still
 * hits the real backend — nothing about the Q&A itself is fabricated,
 * only the grouping/persistence of turns into a named conversation.
 */

import type { ResearchAnswerOut } from "@/types/research";
import type { ResearchMode } from "@/features/research/hooks/use-research";

export interface ConversationTurn {
  id: string;
  mode: ResearchMode;
  query: string;
  documentId: string | null;
  result: ResearchAnswerOut;
  timestamp: string;
}

export interface WorkspaceSession {
  id: string;
  title: string;
  pinned: boolean;
  createdAt: string;
  updatedAt: string;
  turns: ConversationTurn[];
}

const SESSIONS_KEY = "maara_workspace_sessions";
const ACTIVE_SESSION_KEY = "maara_workspace_active_session";
const SESSIONS_EVENT = "maara-workspace-sessions-updated";
const MAX_SESSIONS = 50;

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function genId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function titleFromQuery(query: string): string {
  const trimmed = query.trim().replace(/\s+/g, " ");
  return trimmed.length > 60 ? `${trimmed.slice(0, 57)}…` : trimmed || "Untitled session";
}

export function getSessions(): WorkspaceSession[] {
  if (!isBrowser()) return [];
  try {
    const raw = window.localStorage.getItem(SESSIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as WorkspaceSession[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveSessions(sessions: WorkspaceSession[]): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(0, MAX_SESSIONS)));
  window.dispatchEvent(new Event(SESSIONS_EVENT));
}

export function getActiveSessionId(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACTIVE_SESSION_KEY);
}

export function setActiveSessionId(id: string | null): void {
  if (!isBrowser()) return;
  if (id) window.localStorage.setItem(ACTIVE_SESSION_KEY, id);
  else window.localStorage.removeItem(ACTIVE_SESSION_KEY);
  window.dispatchEvent(new Event(SESSIONS_EVENT));
}

export function createSession(initialTitle?: string): WorkspaceSession {
  const now = new Date().toISOString();
  const session: WorkspaceSession = {
    id: genId(),
    title: initialTitle?.trim() || "New session",
    pinned: false,
    createdAt: now,
    updatedAt: now,
    turns: [],
  };
  saveSessions([session, ...getSessions()]);
  setActiveSessionId(session.id);
  return session;
}

export function addTurn(
  sessionId: string,
  turn: Omit<ConversationTurn, "id" | "timestamp">
): WorkspaceSession | null {
  const sessions = getSessions();
  const idx = sessions.findIndex((s) => s.id === sessionId);
  if (idx === -1) return null;

  const fullTurn: ConversationTurn = { ...turn, id: genId(), timestamp: new Date().toISOString() };
  const session = sessions[idx];
  const wasUntitled = session.turns.length === 0 && session.title === "New session";
  const updated: WorkspaceSession = {
    ...session,
    title: wasUntitled ? titleFromQuery(turn.query) : session.title,
    updatedAt: fullTurn.timestamp,
    turns: [...session.turns, fullTurn],
  };
  const next = [...sessions];
  next[idx] = updated;
  saveSessions(next);
  return updated;
}

export function renameSession(sessionId: string, title: string): void {
  const sessions = getSessions();
  const next = sessions.map((s) => (s.id === sessionId ? { ...s, title: title.trim() || s.title } : s));
  saveSessions(next);
}

export function togglePinSession(sessionId: string): void {
  const sessions = getSessions();
  const next = sessions.map((s) => (s.id === sessionId ? { ...s, pinned: !s.pinned } : s));
  saveSessions(next);
}

export function deleteSession(sessionId: string): void {
  const sessions = getSessions().filter((s) => s.id !== sessionId);
  saveSessions(sessions);
  if (getActiveSessionId() === sessionId) {
    setActiveSessionId(sessions[0]?.id ?? null);
  }
}

export function duplicateSession(sessionId: string): WorkspaceSession | null {
  const sessions = getSessions();
  const source = sessions.find((s) => s.id === sessionId);
  if (!source) return null;
  const now = new Date().toISOString();
  const copy: WorkspaceSession = {
    ...source,
    id: genId(),
    title: `${source.title} (copy)`,
    pinned: false,
    createdAt: now,
    updatedAt: now,
    turns: source.turns.map((t) => ({ ...t, id: genId() })),
  };
  saveSessions([copy, ...sessions]);
  return copy;
}

/** Serializes a session to JSON for download/export. */
export function exportSessionJson(session: WorkspaceSession): string {
  return JSON.stringify(session, null, 2);
}

/** Parses and imports a previously exported session JSON blob, assigning it a fresh id. */
export function importSessionJson(json: string): WorkspaceSession {
  const parsed = JSON.parse(json) as WorkspaceSession;
  if (!parsed || !Array.isArray(parsed.turns)) {
    throw new Error("That file doesn't look like an exported research session.");
  }
  const now = new Date().toISOString();
  const imported: WorkspaceSession = {
    id: genId(),
    title: parsed.title ? `${parsed.title} (imported)` : "Imported session",
    pinned: false,
    createdAt: now,
    updatedAt: now,
    turns: parsed.turns.map((t) => ({ ...t, id: genId() })),
  };
  saveSessions([imported, ...getSessions()]);
  return imported;
}

export function subscribeToSessions(callback: () => void): () => void {
  if (!isBrowser()) return () => {};
  window.addEventListener(SESSIONS_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(SESSIONS_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}
