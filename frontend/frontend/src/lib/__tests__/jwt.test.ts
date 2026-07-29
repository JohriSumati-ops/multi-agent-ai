import { describe, it, expect } from "vitest";

import { decodeJwt, isTokenExpired } from "@/lib/api/jwt";

function makeToken(payload: object): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

describe("decodeJwt", () => {
  it("decodes a well-formed token payload", () => {
    const token = makeToken({ sub: "user-123", exp: 9999999999 });
    expect(decodeJwt(token)).toEqual({ sub: "user-123", exp: 9999999999 });
  });

  it("returns null for a malformed token", () => {
    expect(decodeJwt("not-a-jwt")).toBeNull();
  });
});

describe("isTokenExpired", () => {
  it("returns true for a token with a past exp", () => {
    const token = makeToken({ sub: "user-123", exp: Math.floor(Date.now() / 1000) - 60 });
    expect(isTokenExpired(token)).toBe(true);
  });

  it("returns false for a token with a future exp", () => {
    const token = makeToken({ sub: "user-123", exp: Math.floor(Date.now() / 1000) + 3600 });
    expect(isTokenExpired(token)).toBe(false);
  });

  it("treats an undecodable token as expired", () => {
    expect(isTokenExpired("garbage")).toBe(true);
  });
});
