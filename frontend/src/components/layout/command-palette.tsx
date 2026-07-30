"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { FileText, LogOut, Moon, Sun } from "lucide-react";

import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from "@/components/ui/command";
import { useKeyboardShortcut } from "@/hooks/use-keyboard-shortcut";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import { useAuth } from "@/context/auth-context";
import { useTheme } from "@/context/theme-provider";
import { useCommandPalette } from "@/context/command-palette-context";
import { NAV_ITEMS } from "@/config/nav";

export function CommandPalette() {
  const { open, setOpen } = useCommandPalette();
  const router = useRouter();
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { data: documents } = useDocuments();

  useKeyboardShortcut("k", () => setOpen(!open), { meta: true });

  function go(href: string) {
    setOpen(false);
    router.push(href);
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Jump to a module, document, or action…" />
      <CommandList>
        <CommandEmpty>No matches.</CommandEmpty>

        <CommandGroup heading="Modules">
          {NAV_ITEMS.map((item) => (
            <CommandItem key={item.href} value={item.label} onSelect={() => go(item.href)}>
              <item.icon />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>

        {documents && documents.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Documents">
              {documents.slice(0, 8).map((doc) => (
                <CommandItem
                  key={doc.id}
                  value={doc.title}
                  onSelect={() => go(`/documents?highlight=${doc.id}`)}
                >
                  <FileText />
                  {doc.title}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        <CommandSeparator />
        <CommandGroup heading="Actions">
          <CommandItem value="toggle theme" onSelect={() => { toggleTheme(); setOpen(false); }}>
            {theme === "dark" ? <Sun /> : <Moon />}
            Switch to {theme === "dark" ? "light" : "dark"} mode
          </CommandItem>
          <CommandItem value="sign out" onSelect={() => { setOpen(false); logout(); }}>
            <LogOut />
            Sign out
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}