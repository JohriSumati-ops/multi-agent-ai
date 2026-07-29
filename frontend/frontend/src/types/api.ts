/**
 * Mirrors backend/schemas/base.py.
 *
 * Every endpoint returns this envelope — success responses carry `data`,
 * failures carry `error`. Never both, and `error.code` maps 1:1 to the
 * `error_code` class attributes in backend/core/exceptions.py.
 */
export interface ErrorDetail {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: ErrorDetail | null;
}

/**
 * Thrown by the axios client whenever `success: false` comes back, or the
 * transport itself failed. Components/hooks catch this type specifically
 * rather than raw AxiosError so error-code branching (e.g. "unauthorized"
 * vs "not_found") is consistent everywhere.
 */
export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  status: number | null;

  constructor(error: ErrorDetail, status: number | null) {
    super(error.message);
    this.name = "ApiError";
    this.code = error.code;
    this.details = error.details;
    this.status = status;
  }
}

export interface HealthStatus {
  status: string;
  database: boolean;
  environment: string;
}

export interface VersionInfo {
  app_name: string;
  version: string;
  environment: string;
}
