import { describe, it, expect } from "vitest";

import { unwrap } from "@/lib/api/client";
import { ApiError } from "@/types/api";

describe("unwrap", () => {
  it("returns data when the envelope reports success", () => {
    const result = unwrap({ data: { success: true, data: { id: "abc" }, error: null } });
    expect(result).toEqual({ id: "abc" });
  });

  it("throws ApiError when the envelope reports failure", () => {
    expect(() =>
      unwrap({
        data: {
          success: false,
          data: null,
          error: { code: "not_found", message: "Not found", details: {} },
        },
      })
    ).toThrow(ApiError);
  });

  it("throws ApiError when data is null despite success (defensive guard)", () => {
    expect(() => unwrap({ data: { success: true, data: null, error: null } })).toThrow(ApiError);
  });
});

describe("ApiError", () => {
  it("carries code, message, details, and status", () => {
    const err = new ApiError({ code: "conflict", message: "Already exists", details: { field: "email" } }, 409);
    expect(err.code).toBe("conflict");
    expect(err.message).toBe("Already exists");
    expect(err.details).toEqual({ field: "email" });
    expect(err.status).toBe(409);
    expect(err).toBeInstanceOf(Error);
  });
});
