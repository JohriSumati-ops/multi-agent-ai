import { MOCK_COLLABORATORS } from "@/lib/mock/collaborators";
import type { PresenceState, PresenceStatus } from "@/types/collaboration";
import { NAV_ITEMS } from "@/config/nav";

const STATUSES: PresenceStatus[] = ["online", "online", "online", "idle", "offline"];

function randomOf<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Generates one simulated tick of presence data. Not backed by
 * mock-db/localStorage on purpose — presence is inherently ephemeral,
 * so persisting it across reloads would misrepresent what a real
 * presence channel behaves like.
 */
export function generatePresenceTick(): PresenceState[] {
  return MOCK_COLLABORATORS.map((collaborator) => {
    const status = randomOf(STATUSES);
    return {
      userId: collaborator.id,
      status,
      viewing: status === "offline" ? null : randomOf(NAV_ITEMS).href,
      typing: status === "online" && Math.random() < 0.15,
      lastActiveAt: new Date().toISOString(),
    };
  });
}