// types/auth.ts
export interface LoginRequest {
  email: string;
  password: string;
}

export interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}