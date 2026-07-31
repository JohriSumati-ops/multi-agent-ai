"use client";

import { Sun, Moon, LogOut, User, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { MobileNav } from "@/components/layout/mobile-nav";
import { useAuth } from "@/context/auth-context";
import { useTheme } from "@/context/theme-provider";
import { useCommandPalette } from "@/context/command-palette-context";

export function Topbar({ className }: { className?: string }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { setOpen: openPalette } = useCommandPalette();

  const initials = (user?.full_name || user?.email || "?").trim().charAt(0).toUpperCase();
  const isMac = typeof navigator !== "undefined" && /Mac/.test(navigator.platform);

  return (
    <header
      className={cn(
        "flex h-14 shrink-0 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60 lg:px-6",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <MobileNav />
        <button
          onClick={() => openPalette(true)}
          className="hidden items-center gap-2 rounded-md border border-input bg-surface px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:border-accent hover:text-foreground sm:flex"
          aria-label="Open command palette"
        >
          <Search className="h-3.5 w-3.5" />
          Search or jump to…
          <kbd className="ml-4 rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            {isMac ? "⌘" : "Ctrl"}K
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="sm:hidden" onClick={() => openPalette(true)} aria-label="Search">
          <Search className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Account menu" className="rounded-full">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
                {initials}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel className="max-w-56 truncate">
              {user?.full_name || user?.email || "Account"}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <a href="/profile">
                <User /> Profile
              </a>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={logout} className="text-destructive focus:text-destructive">
              <LogOut /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}