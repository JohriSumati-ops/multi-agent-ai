"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { usePreferences } from "@/context/preferences-context";
import type { NotificationPreferences } from "@/lib/preferences";

const ROWS: { key: keyof NotificationPreferences; label: string; description: string }[] = [
  { key: "documents", label: "Documents", description: "Upload success/failure and delete confirmations." },
  { key: "memory", label: "Memory", description: "Store, prune, delete, and clear confirmations." },
  { key: "research", label: "Research", description: "Toasts when a research answer is ready or fails." },
  { key: "orchestration", label: "Orchestration", description: "Toasts when an agent goal execution finishes." },
];

export function NotificationSettings() {
  const { preferences, update } = usePreferences();

  function toggle(key: keyof NotificationPreferences, value: boolean) {
    update({ notifications: { ...preferences.notifications, [key]: value } });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notifications</CardTitle>
        <CardDescription>
          Controls the in-app toast confirmations shown after actions in this browser. The backend has no push or
          email notification system, so this only affects toasts you already see while using the app.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {ROWS.map((row) => (
          <div key={row.key} className="flex items-center justify-between gap-4 border-b border-border py-2 last:border-0">
            <div>
              <Label htmlFor={`notify-${row.key}`} className="text-sm font-medium text-foreground">
                {row.label}
              </Label>
              <p className="text-xs text-muted-foreground">{row.description}</p>
            </div>
            <Switch
              id={`notify-${row.key}`}
              checked={preferences.notifications[row.key]}
              onCheckedChange={(checked) => toggle(row.key, checked)}
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
