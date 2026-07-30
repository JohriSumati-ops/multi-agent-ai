"use client";

import { getCollaborator, initialsOf } from "@/lib/mock/collaborators";
import { usePresence } from "@/features/presence/hooks/use-presence";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { NAV_ITEMS } from "@/config/nav";
import { cn } from "@/lib/utils";
import type { PresenceStatus } from "@/types/collaboration";

const STATUS_RING: Record<PresenceStatus, string> = {
  online: "ring-success",
  idle: "ring-warning",
  offline: "ring-border",
};

const STATUS_DOT: Record<PresenceStatus, string> = {
  online: "bg-success",
  idle: "bg-warning",
  offline: "bg-muted-foreground",
};

export function PresenceAvatarStack({ max = 4 }: { max?: number }) {
  const presence = usePresence();
  const visible = presence.slice(0, max);

  if (visible.length === 0) return null;

  return (
    <div className="flex items-center -space-x-2" aria-label="Team presence">
      {visible.map((p) => {
        const collaborator = getCollaborator(p.userId);
        if (!collaborator) return null;
        const pageLabel = NAV_ITEMS.find((n) => n.href === p.viewing)?.label;

        return (
          <Tooltip key={p.userId}>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  "relative flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-semibold text-white ring-2 ring-offset-1 ring-offset-background transition-transform hover:z-10 hover:scale-110",
                  STATUS_RING[p.status]
                )}
                style={{ background: collaborator.color }}
              >
                {initialsOf(collaborator.name)}
                <span
                  className={cn(
                    "absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-background",
                    STATUS_DOT[p.status]
                  )}
                  aria-hidden="true"
                />
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p className="font-medium">{collaborator.name}</p>
              <p className="text-muted-foreground">
                {p.status === "offline" ? "Offline" : p.typing ? "Typing…" : pageLabel ? `Viewing ${pageLabel}` : "Online"}
              </p>
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}