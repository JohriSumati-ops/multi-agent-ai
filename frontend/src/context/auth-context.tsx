"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { authApi } from "@/lib/api/auth-api";
import { getToken, setToken, clearToken } from "@/lib/api/token";
import { decodeJwt, isTokenExpired } from "@/lib/api/jwt";
import { cacheProfile, getCachedProfile, type CachedProfile } from "@/lib/api/profile-cache";
import { ApiError } from "@/types/api";
import type { LoginRequest, RegisterRequest } from "@/types/auth";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: CachedProfile | null;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = React.useState<AuthStatus>("loading");
  const [user, setUser] = React.useState<CachedProfile | null>(null);

  const hydrateFromToken = React.useCallback((token: string) => {
    const payload = decodeJwt(token);
    if (!payload) return null;
    const cached = getCachedProfile(payload.sub);
    const profile: CachedProfile = cached ?? { id: payload.sub, email: "", full_name: null };
    setUser(profile);
    return profile;
  }, []);

  React.useEffect(() => {
    const token = getToken();
    if (!token || isTokenExpired(token)) {
      clearToken();
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync from localStorage, an SSR-unavailable external source; can't be computed during render.
      setStatus("unauthenticated");
      return;
    }
    hydrateFromToken(token);
    setStatus("authenticated");
  }, [hydrateFromToken]);

  const login = React.useCallback(
    async (payload: LoginRequest) => {
      const { access_token } = await authApi.login(payload);
      setToken(access_token);
      const decoded = decodeJwt(access_token);
      if (decoded) {
        // The login response carries no profile — only the JWT subject.
        // Fall back to the email the user just typed, and to any
        // previously cached full_name for this user id.
        const cached = getCachedProfile(decoded.sub);
        const profile: CachedProfile = {
          id: decoded.sub,
          email: payload.email,
          full_name: cached?.full_name ?? null,
        };
        cacheProfile(profile);
        setUser(profile);
      }
      setStatus("authenticated");
      router.push("/dashboard");
    },
    [router]
  );

  const register = React.useCallback(
    async (payload: RegisterRequest) => {
      const created = await authApi.register(payload);
      cacheProfile({ id: created.id, email: created.email, full_name: created.full_name });
      // Registration doesn't return a token — log in immediately after
      // for a seamless "sign up and land in the app" flow.
      await login({ email: payload.email, password: payload.password });
    },
    [login]
  );

  const logout = React.useCallback(() => {
    clearToken();
    setUser(null);
    setStatus("unauthenticated");
    router.push("/login");
  }, [router]);

  const value = React.useMemo(
    () => ({ status, user, login, register, logout }),
    [status, user, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

export { ApiError };
