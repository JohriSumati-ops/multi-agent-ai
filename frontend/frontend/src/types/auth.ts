export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserOut {
  id: string;
  created_at: string;
  updated_at: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}
