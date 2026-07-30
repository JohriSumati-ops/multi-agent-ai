import { describe, it, expect } from "vitest";

import { cn } from "@/lib/utils";

describe("cn", () => {
  it("merges class names, dropping falsy values", () => {
    expect(cn("a", false, undefined, "b")).toBe("a b");
  });

  it("resolves conflicting Tailwind classes to the last one", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });

  it("merges conditional class objects", () => {
    expect(cn("base", { active: true, hidden: false })).toBe("base active");
  });
});
