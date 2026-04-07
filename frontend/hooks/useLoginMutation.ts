// hooks/useLoginMutation.ts
import { useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';

interface LoginRequest {
  email: string;
  password: string;
}

interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const useLoginMutation = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<LoginResponse | null>(null);
  const setAuth = useAuthStore((state) => state.setAuth);

  const mutate = async (credentials: LoginRequest) => {
    setIsLoading(true);
    setError(null);
    setData(null);
    try {
      const response = await api.post<LoginResponse>('/auth/login', credentials);
      setAuth(response.data.access_token, response.data.user);
      setData(response.data);
      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Erro ao fazer login. Verifique suas credenciais.';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return { mutate, isLoading, error, data };
};