"use client";

import Link from "next/link";
import { RotateCcw, UserCircle } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AppearanceSettings } from "@/features/settings/components/appearance-settings";
import { RetrievalSettings } from "@/features/settings/components/retrieval-settings";
import { MemorySettings } from "@/features/settings/components/memory-settings";
import { NotificationSettings } from "@/features/settings/components/notification-settings";
import { ApiSettings } from "@/features/settings/components/api-settings";
import { usePreferences } from "@/context/preferences-context";

export default function SettingsPage() {
  const { reset } = usePreferences();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Preferences for this browser — appearance, defaults, and notifications.
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            reset();
            toast.success("Settings reset to defaults");
          }}
        >
          <RotateCcw /> Reset all
        </Button>
      </div>

      <Card>
        <CardContent className="flex items-center justify-between gap-4 p-4">
          <div className="flex items-center gap-2.5 text-sm">
            <UserCircle className="h-4 w-4 text-muted-foreground" />
            <span className="text-foreground">Account details and sign-out live on your Profile page.</span>
          </div>
          <Link href="/profile" className="text-xs font-medium text-primary hover:underline">
            Go to Profile
          </Link>
        </CardContent>
      </Card>

      <AppearanceSettings />
      <RetrievalSettings />
      <MemorySettings />
      <NotificationSettings />
      <ApiSettings />

      <Card>
        <CardContent className="p-4 text-xs text-muted-foreground">
          There is no backend endpoint for user preferences today — everything on this page is stored only in this
          browser&apos;s <code className="font-mono">localStorage</code>, the same way theme already worked. It
          won&apos;t follow you to another device or browser.
        </CardContent>
      </Card>
    </div>
  );
}
