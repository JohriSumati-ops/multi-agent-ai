export interface JwtPayload {
  sub: string;
  exp: number;
}

/**
 * Decodes (does not verify — verification is the backend's job) a JWT's
 * payload so the UI can read `sub` (user id) and `exp` for client-side
 * expiry checks. Never trust this for authorization decisions; it's
 * display/UX only.
 */
export function decodeJwt(token: string): JwtPayload | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(normalized)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    );
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJwt(token);
  if (!payload) return true;
  return Date.now() >= payload.exp * 1000;
}
