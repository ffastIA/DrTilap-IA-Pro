// CAMINHO: frontend/store/authStore.ts

import { create } from 'zustand';
import Cookies from 'js-cookie';

interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';
}

interface AuthStore {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
  restoreAuth: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setAuth: (token, user) => {
    Cookies.set('accessToken', token, { path: '/', sameSite: 'Lax' });
    Cookies.set('user', JSON.stringify(user), { path: '/', sameSite: 'Lax' });
    set({ token, user, isAuthenticated: true, isLoading: false });
  },
  clearAuth: () => {
    Cookies.remove('accessToken', { path: '/' });
    Cookies.remove('user', { path: '/' });
    set({ token: null, user: null, isAuthenticated: false, isLoading: false });
  },
  restoreAuth: () => {
    const token = Cookies.get('accessToken');
    const userCookie = Cookies.get('user');
    if (token && userCookie) {
      try {
        const user = JSON.parse(userCookie);
        set({ token, user, isAuthenticated: true, isLoading: false });
      } catch {
        // JSON inválido, limpar cookies
        Cookies.remove('accessToken', { path: '/' });
        Cookies.remove('user', { path: '/' });
        set({ token: null, user: null, isAuthenticated: false, isLoading: false });
      }
    } else {
      // Cookies não existem
      set({ token: null, user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
