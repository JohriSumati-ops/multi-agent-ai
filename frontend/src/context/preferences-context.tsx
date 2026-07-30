"use client";

import * as React from "react";

import {
  DEFAULT_PREFERENCES,
  getPreferences,
  setPreferences as persistPreferences,
  resetPreferences as persistReset,
  subscribeToPreferences,
  type Preferences,
} from "@/lib/preferences";

interface PreferencesContextValue {
  preferences: Preferences;
  update: (patch: Partial<Preferences>) => void;
  reset: () => void;
}

const PreferencesContext = React.createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [preferences, setPreferencesState] = React.useState<Preferences>(DEFAULT_PREFERENCES);

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync from localStorage, an SSR-unavailable external source; can't be computed during render.
    setPreferencesState(getPreferences());
    return subscribeToPreferences(() => setPreferencesState(getPreferences()));
  }, []);

  const update = React.useCallback((patch: Partial<Preferences>) => {
    const next: Preferences = {
      ...getPreferences(),
      ...patch,
      retrieval: { ...getPreferences().retrieval, ...patch.retrieval },
      memory: { ...getPreferences().memory, ...patch.memory },
      notifications: { ...getPreferences().notifications, ...patch.notifications },
    };
    persistPreferences(next);
    setPreferencesState(next);
  }, []);

  const reset = React.useCallback(() => {
    persistReset();
    setPreferencesState(DEFAULT_PREFERENCES);
  }, []);

  const value = React.useMemo(() => ({ preferences, update, reset }), [preferences, update, reset]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const ctx = React.useContext(PreferencesContext);
  if (!ctx) throw new Error("usePreferences must be used within a PreferencesProvider");
  return ctx;
}
