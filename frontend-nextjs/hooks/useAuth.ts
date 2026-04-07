import { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';

export const useAuth = () => {
  const { token, user, isAuthenticated, restoreAuth } = useAuthStore();

  useEffect(() => {
    restoreAuth();
  }, [restoreAuth]);

  return {
    token,
    user,
    isAuthenticated,
  };
};