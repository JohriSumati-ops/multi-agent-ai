"use client";

import * as React from "react";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePreferences } from "@/context/preferences-context";
import { API_BASE_URL } from "@/lib/api/client";

export function ApiSettings() {
  const { preferences, update } = usePreferences();
  const [override, setOverride] = React.useState(preferences.apiBaseUrlOverride ?? "");

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync of the form's baseline once preferences hydrate from localStorage after mount.
    setOverride(preferences.apiBaseUrlOverride ?? "");
  }, [preferences.apiBaseUrlOverride]);

  const effective = preferences.apiBaseUrlOverride?.trim() || API_BASE_URL;
  const dirty = (override.trim() || null) !== preferences.apiBaseUrlOverride;

  function save() {
    const trimmed = override.trim();
    update({ apiBaseUrlOverride: trimmed.length > 0 ? trimmed : null });
    toast.success(trimmed ? "API base URL override saved" : "API base URL override cleared");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>API configuration</CardTitle>
        <CardDescription>
          Built with <code className="font-mono">NEXT_PUBLIC_API_BASE_URL={API_BASE_URL}</code>. The override below
          only changes which backend *this browser* talks to — useful for pointing at a local or staging instance —
          and is stored in <code className="font-mono">localStorage</code>, not on the server.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        <div className="rounded-md border border-border bg-muted/40 p-3 text-xs">
          <span className="text-muted-foreground">Currently in effect: </span>
          <span className="font-mono text-foreground">{effective}</span>
        </div>
        <div className="space-y-1.5 sm:max-w-md">
          <Label htmlFor="settings-api-base-url">Override base URL (optional)</Label>
          <Input
            id="settings-api-base-url"
            placeholder="http://localhost:8000/api/v1"
            value={override}
            onChange={(e) => setOverride(e.target.value)}
          />
        </div>
      </CardContent>
      <CardFooter className="gap-2">
        <Button type="button" size="sm" disabled={!dirty} onClick={save}>
          Save
        </Button>
        {preferences.apiBaseUrlOverride && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              setOverride("");
              update({ apiBaseUrlOverride: null });
              toast.success("API base URL override cleared");
            }}
          >
            Clear override
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
