"use client";

import * as React from "react";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePreferences } from "@/context/preferences-context";

export function RetrievalSettings() {
  const { preferences, update } = usePreferences();
  const [topK, setTopK] = React.useState(preferences.retrieval.defaultTopK);
  const [threshold, setThreshold] = React.useState(preferences.retrieval.defaultSimilarityThreshold);

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync of the form's baseline once preferences hydrate from localStorage after mount.
    setTopK(preferences.retrieval.defaultTopK);
    setThreshold(preferences.retrieval.defaultSimilarityThreshold);
  }, [preferences.retrieval.defaultTopK, preferences.retrieval.defaultSimilarityThreshold]);

  const dirty =
    topK !== preferences.retrieval.defaultTopK || threshold !== preferences.retrieval.defaultSimilarityThreshold;

  function save() {
    const clampedTopK = Math.min(50, Math.max(1, Math.round(topK)));
    const clampedThreshold = Math.min(1, Math.max(0, threshold));
    update({ retrieval: { defaultTopK: clampedTopK, defaultSimilarityThreshold: clampedThreshold } });
    toast.success("Retrieval defaults saved");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Research &amp; retrieval defaults</CardTitle>
        <CardDescription>
          Pre-fills the Retrieval search form. Individual searches can still override these per query.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 pt-0 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="settings-top-k">Default results (top-K)</Label>
          <Input
            id="settings-top-k"
            type="number"
            min={1}
            max={50}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="settings-threshold">Default similarity threshold</Label>
          <Input
            id="settings-threshold"
            type="number"
            min={0}
            max={1}
            step={0.05}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          />
        </div>
      </CardContent>
      <CardFooter>
        <Button type="button" size="sm" disabled={!dirty} onClick={save}>
          Save defaults
        </Button>
      </CardFooter>
    </Card>
  );
}
