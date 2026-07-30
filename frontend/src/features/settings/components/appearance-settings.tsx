"use client";

import { Moon, Sun } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/context/theme-provider";

export function AppearanceSettings() {
  const { theme, setTheme } = useTheme();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>Theme for this browser. Stored locally, not tied to your account.</CardDescription>
      </CardHeader>
      <CardContent className="flex gap-2 pt-0">
        <Button
          type="button"
          variant={theme === "dark" ? "default" : "outline"}
          size="sm"
          onClick={() => setTheme("dark")}
          aria-pressed={theme === "dark"}
        >
          <Moon /> Dark
        </Button>
        <Button
          type="button"
          variant={theme === "light" ? "default" : "outline"}
          size="sm"
          onClick={() => setTheme("light")}
          aria-pressed={theme === "light"}
        >
          <Sun /> Light
        </Button>
      </CardContent>
    </Card>
  );
}
