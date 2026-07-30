"use client";

import * as React from "react";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePreferences } from "@/context/preferences-context";

export function MemorySettings() {
  const { preferences, update } = usePreferences();
  const [keepTopN, setKeepTopN] = React.useState(preferences.memory.defaultPruneKeepTopN);

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync of the form's baseline once preferences hydrate from localStorage after mount.
    setKeepTopN(preferences.memory.defaultPruneKeepTopN);
  }, [preferences.memory.defaultPruneKeepTopN]);

  const dirty = keepTopN !== preferences.memory.defaultPruneKeepTopN;

  function save() {
    const clamped = Math.max(0, Math.round(keepTopN));
    update({ memory: { defaultPruneKeepTopN: clamped } });
    toast.success("Memory defaults saved");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Memory limits</CardTitle>
        <CardDescription>
          Default &quot;keep top N&quot; long-term memories used by the Prune action on the Memory page.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0 sm:max-w-xs">
        <div className="space-y-1.5">
          <Label htmlFor="settings-prune-keep">Keep top N long-term memories</Label>
          <Input
            id="settings-prune-keep"
            type="number"
            min={0}
            step={100}
            value={keepTopN}
            onChange={(e) => setKeepTopN(Number(e.target.value))}
          />
        </div>
      </CardContent>
      <CardFooter>
        <Button type="button" size="sm" disabled={!dirty} onClick={save}>
          Save default
        </Button>
      </CardFooter>
    </Card>
  );
}
