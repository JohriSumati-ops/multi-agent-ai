import { apiClient, unwrap } from "@/lib/api/client";
import type { LoginRequest, RegisterRequest, TokenResponse, UserOut } from "@/types/auth";

export const authApi = {
  register: (payload: RegisterRequest) =>
    apiClient.post<{ success: boolean; data: UserOut; error: null }>("/auth/register", payload).then(unwrap),

  login: (payload: LoginRequest) =>
    apiClient
      .post<{ success: boolean; data: TokenResponse; error: null }>("/auth/login", payload)
      .then(unwrap),
};
