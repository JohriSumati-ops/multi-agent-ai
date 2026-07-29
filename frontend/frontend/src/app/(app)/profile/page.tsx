"use client";

import { LogOut } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth-context";

export default function ProfilePage() {
  const { user, logout } = useAuth();

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Profile</h1>
        <p className="mt-1 text-sm text-muted-foreground">Your account details.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-0 text-sm">
          <Row label="Name" value={user?.full_name || "—"} />
          <Row label="Email" value={user?.email || "—"} />
          <Row label="User ID" value={user?.id ?? "—"} mono />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 text-xs text-muted-foreground">
          The backend doesn&apos;t expose a profile endpoint yet (no{" "}
          <code className="font-mono">GET /auth/me</code>), so these details are read from what was
          returned at registration/login rather than fetched fresh each time.
        </CardContent>
      </Card>

      <Button variant="outline" onClick={logout} className="text-destructive hover:text-destructive">
        <LogOut /> Sign out
      </Button>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-border py-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono text-xs text-foreground" : "text-foreground"}>{value}</span>
    </div>
  );
}
