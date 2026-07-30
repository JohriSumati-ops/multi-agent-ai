import axios, { AxiosError, type AxiosRequestConfig } from "axios";

import { ApiError, type APIResponse } from "@/types/api";
import { getToken, clearToken } from "@/lib/api/token";
import { resolveApiBaseUrl } from "@/lib/preferences";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/**
 * A request-scoped flag: transient errors (network failure, 502/503/504)
 * are retried automatically. 4xx and validated 5xx application errors
 * (which always arrive in the APIResponse envelope) are not retried,
 * since retrying "not found" or "validation failed" wastes a round trip.
 */
const RETRYABLE_STATUS = new Set([502, 503, 504]);
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 400;

declare module "axios" {
  export interface InternalAxiosRequestConfig {
    _retryCount?: number;
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60_000,
});

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  // Settings → API configuration lets a user point this browser at a
  // different backend instance without a rebuild. Resolved per-request
  // (rather than baked into the axios instance at module load) so a
  // change on the Settings page takes effect on the very next call.
  config.baseURL = resolveApiBaseUrl(API_BASE_URL);
  return config;
});

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<APIResponse<unknown>>) => {
    const config = error.config;
    const status = error.response?.status ?? null;

    // Transient failure — retry with backoff before giving up.
    if (config && status !== null && RETRYABLE_STATUS.has(status)) {
      config._retryCount = (config._retryCount ?? 0) + 1;
      if (config._retryCount <= MAX_RETRIES) {
        await wait(RETRY_DELAY_MS * config._retryCount);
        return apiClient(config as AxiosRequestConfig);
      }
    }

    // Session expired or invalid — clear it so ProtectedRoute redirects
    // to /login rather than looping on repeated 401s.
    if (status === 401) {
      clearToken();
    }

    const envelope = error.response?.data;
    if (envelope?.error) {
      throw new ApiError(envelope.error, status);
    }

    throw new ApiError(
      {
        code: error.code === "ECONNABORTED" ? "timeout" : "network_error",
        message:
          error.message || "Could not reach the server. Check your connection and try again.",
        details: {},
      },
      status
    );
  }
);

/**
 * Unwraps `APIResponse<T>.data`, throwing ApiError if the envelope reports
 * failure even on an HTTP 2xx (shouldn't happen per backend contract, but
 * guards against it rather than silently returning null).
 */
export function unwrap<T>(response: { data: APIResponse<T> }): T {
  const envelope = response.data;
  if (!envelope.success || envelope.data === null) {
    throw new ApiError(
      envelope.error ?? { code: "internal_error", message: "Unexpected empty response", details: {} },
      null
    );
  }
  return envelope.data;
}
