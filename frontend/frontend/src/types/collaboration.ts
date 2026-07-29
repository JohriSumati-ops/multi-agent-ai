/**
 * Mock collaborator profile. Distinct from `UserOut` (types/auth.ts,
 * real backend user) because the backend has no concept of teams or
 * other users at all — this models *other people in a workspace*,
 * which is entirely a Phase 9 mock concept until a real collaboration
 * backend exists.
 */
export interface Collaborator {
  id: string;
  name: string;
  email: string;
  /** Deterministic color used for avatar fallback + presence dot theming, drawn from chart token colors. */
  color: string;
  role: "owner" | "editor" | "viewer";
}

export type PresenceStatus = "online" | "idle" | "offline";

export interface PresenceState {
  userId: string;
  status: PresenceStatus;
  /** Route path the user is currently viewing, e.g. "/documents". */
  viewing: string | null;
  /** True if they're actively typing in a comment/annotation box right now. */
  typing: boolean;
  lastActiveAt: string;
}