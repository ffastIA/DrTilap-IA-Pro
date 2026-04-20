// CAMINHO: frontend/hooks/useLoginMutation.ts
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
  token_type?: string;
  user?: User;
}

function normalizeErrorMessage(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'object' && item && 'msg' in item && typeof item.msg === 'string') {
          return item.msg;
        }
        return JSON.stringify(item);
      })
      .join('; ');
  }
  if (typeof value === 'object' && value !== null) {
    if ('msg' in value && typeof value.msg === 'string') {
      return value.msg;
    }
    if ('detail' in value) {
      return normalizeErrorMessage((value as any).detail);
    }
  }
  return 'Erro ao fazer login. Verifique suas credenciais.';
}

export const useLoginMutation = () => {
  const [isPending, setIsPending] = useState(false);
  const [isError, setIsError] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [data, setData] = useState<LoginResponse | null>(null);

  const { setAuth } = useAuthStore();

  const mutate = async (credentials: LoginRequest) => {
    setIsPending(true);
    setIsError(false);
    setIsSuccess(false);
    setError(null);
    setData(null);

    try {
      const response = await api.post<LoginResponse>('/auth/login', credentials);
      let user = response.data.user;
      if (!user) {
        user = { id: '', email: credentials.email, role: 'user' };
      }
      setAuth(response.data.access_token, user);
      setData(response.data);
      setIsSuccess(true);
    } catch (err: any) {
      const normalizedError = new Error(normalizeErrorMessage(err.response?.data ?? err));
      setError(normalizedError);
      setIsError(true);
      throw normalizedError;
    } finally {
      setIsPending(false);
    }
  };

  return { mutate, isPending, isError, isSuccess, error, data };
};
