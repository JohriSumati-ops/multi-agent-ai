import type { Collaborator } from "@/types/collaboration";

/**
 * Fixed seed collaborators for the mock workspace. Real-money question
 * this dodges: there's no backend team/org model, so these are stable,
 * clearly-fictional identities rather than anything derived from real
 * accounts.
 */
export const MOCK_COLLABORATORS: Collaborator[] = [
  { id: "collab_1", name: "Priya Nair", email: "priya@example.com", color: "var(--color-chart-1)", role: "owner" },
  { id: "collab_2", name: "Marcus Webb", email: "marcus@example.com", color: "var(--color-chart-2)", role: "editor" },
  { id: "collab_3", name: "Elena Popescu", email: "elena@example.com", color: "var(--color-chart-3)", role: "editor" },
  { id: "collab_4", name: "Sam Okafor", email: "sam@example.com", color: "var(--color-chart-4)", role: "viewer" },
];

export function getCollaborator(id: string): Collaborator | undefined {
  return MOCK_COLLABORATORS.find((c) => c.id === id);
}

export function initialsOf(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}