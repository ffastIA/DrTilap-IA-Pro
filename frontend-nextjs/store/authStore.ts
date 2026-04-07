import { create } from 'zustand';
import Cookies from 'js-cookie';

export interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';
}

export interface AuthStore {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;

  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
  restoreAuth: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,

  setAuth: (token: string, user: User) => {
    Cookies.set('accessToken', token, { expires: 7 });
    Cookies.set('user', JSON.stringify(user), { expires: 7 });

    set({
      token,
      user,
      isAuthenticated: true,
    });
  },

  clearAuth: () => {
    Cookies.remove('accessToken');
    Cookies.remove('user');
    set({
      token: null,
      user: null,
      isAuthenticated: false,
    });
  },

  restoreAuth: () => {
    const token = Cookies.get('accessToken');
    const userStr = Cookies.get('user');

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        set({
          token,
          user,
          isAuthenticated: true,
        });
      } catch {
        Cookies.remove('accessToken');
        Cookies.remove('user');
        set({
          token: null,
          user: null,
          isAuthenticated: false,
        });
      }
    }
  },
}));