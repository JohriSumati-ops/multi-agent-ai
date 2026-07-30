import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LoginForm } from "@/features/auth/components/login-form";

const loginMock = vi.fn();

vi.mock("@/context/auth-context", () => ({
  useAuth: () => ({ login: loginMock, register: vi.fn(), logout: vi.fn(), status: "unauthenticated", user: null }),
}));

vi.mock("next/link", () => ({
  default: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}));

describe("LoginForm", () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  it("shows validation errors and does not call login for invalid input", async () => {
    render(<LoginForm />);
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Email is required")).toBeInTheDocument();
    expect(loginMock).not.toHaveBeenCalled();
  });

  it("calls login with the entered credentials on valid submit", async () => {
    loginMock.mockResolvedValueOnce(undefined);
    render(<LoginForm />);

    await userEvent.type(screen.getByLabelText("Email"), "user@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "hunter2");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() =>
      expect(loginMock).toHaveBeenCalledWith({ email: "user@example.com", password: "hunter2" })
    );
  });

  it("surfaces an unauthorized error from the API as a friendly message", async () => {
    const { ApiError } = await import("@/types/api");
    loginMock.mockRejectedValueOnce(new ApiError({ code: "unauthorized", message: "bad", details: {} }, 401));
    render(<LoginForm />);

    await userEvent.type(screen.getByLabelText("Email"), "user@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrongpass");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(
      await screen.findByText("That email or password isn't right. Double-check and try again.")
    ).toBeInTheDocument();
  });
});
