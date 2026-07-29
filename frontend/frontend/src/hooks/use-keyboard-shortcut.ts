"use client";

import * as React from "react";

interface ShortcutOptions {
  /** Require Cmd (macOS) or Ctrl (others). */
  meta?: boolean;
  /** Prevent the browser's default handling (e.g. Ctrl+K bookmark search). */
  preventDefault?: boolean;
  /** Disable the listener without unmounting the hook. */
  enabled?: boolean;
}

/**
 * Registers a single global key combo. Ignores keystrokes while the user
 * is typing in an input/textarea/contenteditable, except when `meta` is
 * required (so Cmd/Ctrl+K still opens the palette from inside a search
 * box, but plain "n" doesn't trigger while typing a title).
 */
export function useKeyboardShortcut(key: string, callback: () => void, options: ShortcutOptions = {}) {
  const { meta = false, preventDefault = true, enabled = true } = options;
  const callbackRef = React.useRef(callback);

  React.useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  React.useEffect(() => {
    if (!enabled) return;

    function handler(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const isEditable =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;

      if (isEditable && !meta) return;
      if (event.key.toLowerCase() !== key.toLowerCase()) return;
      if (meta && !(event.metaKey || event.ctrlKey)) return;
      if (!meta && (event.metaKey || event.ctrlKey)) return;

      if (preventDefault) event.preventDefault();
      callbackRef.current();
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [key, meta, preventDefault, enabled]);
}