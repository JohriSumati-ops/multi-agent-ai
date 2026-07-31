"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { FileText, LogOut, Moon, Sun, MessageSquarePlus, UploadCloud, BrainCircuit, Workflow, Keyboard } from "lucide-react";

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
import { createSession } from "@/features/workspace/session-store";
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

        <CommandGroup heading="Quick actions">
          <CommandItem
            value="new research session start research"
            onSelect={() => {
              createSession();
              go("/research");
            }}
          >
            <MessageSquarePlus />
            Start a new research session
          </CommandItem>
          <CommandItem value="upload document" onSelect={() => go("/documents#document-uploader")}>
            <UploadCloud />
            Upload a document
          </CommandItem>
          <CommandItem value="search memory" onSelect={() => go("/memory")}>
            <BrainCircuit />
            Search memory
          </CommandItem>
          <CommandItem value="execute agent goal orchestration" onSelect={() => go("/orchestration")}>
            <Workflow />
            Execute an agent goal
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />
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
          <CommandItem
            value="keyboard shortcuts help"
            onSelect={() => {
              setOpen(false);
              toast.message("Keyboard shortcuts", {
                description: "⌘/Ctrl + K — command palette · ⌘/Ctrl + Enter — send in Research Workspace",
              });
            }}
          >
            <Keyboard />
            Keyboard shortcuts
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