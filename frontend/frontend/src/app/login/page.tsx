import type { Metadata } from "next";

import { AuthShell } from "@/features/auth/components/auth-shell";
import { LoginForm } from "@/features/auth/components/login-form";

export const metadata: Metadata = { title: "Sign in — Research Assistant Console" };

export default function LoginPage() {
  return (
    <AuthShell title="Sign in" subtitle="Welcome back — pick up where you left off.">
      <LoginForm />
    </AuthShell>
  );
}
