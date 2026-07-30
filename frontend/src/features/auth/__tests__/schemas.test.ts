import { describe, it, expect } from "vitest";

import { loginSchema, registerSchema } from "@/features/auth/schemas";

describe("loginSchema", () => {
  it("accepts a valid email/password pair", () => {
    expect(loginSchema.safeParse({ email: "a@b.com", password: "secret" }).success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = loginSchema.safeParse({ email: "not-an-email", password: "secret" });
    expect(result.success).toBe(false);
  });

  it("rejects an empty password", () => {
    const result = loginSchema.safeParse({ email: "a@b.com", password: "" });
    expect(result.success).toBe(false);
  });
});

describe("registerSchema", () => {
  it("accepts a valid registration payload", () => {
    expect(
      registerSchema.safeParse({ email: "a@b.com", password: "longenough", full_name: "Ada" }).success
    ).toBe(true);
  });

  it("rejects a password under 8 characters (matches backend UserCreate constraint)", () => {
    const result = registerSchema.safeParse({ email: "a@b.com", password: "short" });
    expect(result.success).toBe(false);
  });

  it("allows full_name to be omitted", () => {
    expect(registerSchema.safeParse({ email: "a@b.com", password: "longenough" }).success).toBe(true);
  });
});
