"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/context/auth-context";
import { Loader2 } from "lucide-react";

export default function RootPage() {
  const { status } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  return (
    <div className="flex min-h-svh items-center justify-center bg-background">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );
}
