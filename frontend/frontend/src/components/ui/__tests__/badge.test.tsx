import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
  it("renders its label", () => {
    render(<Badge>ready</Badge>);
    expect(screen.getByText("ready")).toBeInTheDocument();
  });

  it("applies the success variant's classes", () => {
    render(<Badge variant="success">ready</Badge>);
    expect(screen.getByText("ready").className).toContain("text-success");
  });

  it("applies the destructive variant's classes", () => {
    render(<Badge variant="destructive">failed</Badge>);
    expect(screen.getByText("failed").className).toContain("text-destructive");
  });

  it("defaults to the default variant when none is given", () => {
    render(<Badge>default</Badge>);
    expect(screen.getByText("default").className).toContain("text-primary");
  });
});
