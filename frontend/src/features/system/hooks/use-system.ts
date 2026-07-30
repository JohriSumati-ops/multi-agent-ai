"use client";

import { useQuery } from "@tanstack/react-query";

import { systemApi } from "@/lib/api/system-api";
import { queryKeys } from "@/lib/api/query-keys";

export function useSystemHealth() {
  return useQuery({
    queryKey: queryKeys.system.health(),
    queryFn: systemApi.health,
    refetchInterval: 15_000,
  });
}

export function useSystemVersion() {
  return useQuery({
    queryKey: queryKeys.system.version(),
    queryFn: systemApi.version,
  });
}
