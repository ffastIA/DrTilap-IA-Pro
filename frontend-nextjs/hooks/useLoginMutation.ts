import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

interface LoginPayload {
  email: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    role: 'admin' | 'user';
  };
}

export const useLoginMutation = () => {
  const router = useRouter();
  const { setAuth } = useAuthStore();

  return useMutation({
    mutationFn: (payload: LoginPayload) =>
      authApi.login(payload.email, payload.password),
    onSuccess: (response: LoginResponse) => {
      setAuth(response.access_token, response.user);
      router.push('/main/hub');
    },
    onError: (error: any) => {
      console.error(
        'Login error:',
        error.response?.data?.detail || error.message || 'Erro ao fazer login'
      );
    },
  });
};