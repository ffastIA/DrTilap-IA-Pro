// hooks/useAuth.ts
import { useAuthStore } from '@/store/authStore';

export const useAuth = () => {
  const { user, token, isAuthenticated, isLoading, login, logout, updateUser } = useAuthStore(
    (state) => ({
      user: state.user,
      token: state.token,
      isAuthenticated: state.isAuthenticated,
      isLoading: state.isLoading,
      login: state.login,
      logout: state.logout,
      updateUser: state.updateUser,
    })
  );

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    logout,
    updateUser,
  };
};

export default useAuth;