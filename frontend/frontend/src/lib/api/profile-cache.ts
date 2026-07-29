import type { UserOut } from "@/types/auth";

const PROFILE_KEY_PREFIX = "maara_profile_";

export type CachedProfile = Pick<UserOut, "id" | "email" | "full_name">;

export function cacheProfile(profile: CachedProfile): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PROFILE_KEY_PREFIX + profile.id, JSON.stringify(profile));
}

export function getCachedProfile(userId: string): CachedProfile | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(PROFILE_KEY_PREFIX + userId);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CachedProfile;
  } catch {
    return null;
  }
}
