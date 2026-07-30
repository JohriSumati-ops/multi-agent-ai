import type { Metadata } from "next";

import { AuthShell } from "@/features/auth/components/auth-shell";
import { RegisterForm } from "@/features/auth/components/register-form";

export const metadata: Metadata = { title: "Create account — Research Assistant Console" };

export default function RegisterPage() {
  return (
    <AuthShell title="Create your account" subtitle="Set up access to the research console.">
      <RegisterForm />
    </AuthShell>
  );
}
