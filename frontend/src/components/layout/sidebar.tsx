"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/config/nav";

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();

  return (
    <aside className={cn("hidden w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex", className)}>
      <div className="flex h-14 items-center gap-2.5 px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
          R
        </div>
        <span className="font-mono text-sm font-medium tracking-wide text-sidebar-foreground">
          research-assistant
        </span>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-3">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-foreground"
                  : "text-sidebar-muted hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
              )}
            >
              {active && (
                <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-sidebar-primary" />
              )}
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border px-5 py-3">
        <p className="font-mono text-[11px] text-sidebar-muted">v0.1.0 · development</p>
      </div>
    </aside>
  );
}
