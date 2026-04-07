// components/AuthProvider.tsx
'use client';

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import LoadingSpinner from './LoadingSpinner';

interface AuthProviderProps {
  children: React.ReactNode;
}

const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const publicRoutes = ['/', '/auth/login'];
  const protectedRoutes = ['/main'];

  useEffect(() => {
    // Se ainda está carregando, não faz nada
    if (isLoading) {
      return;
    }

    const isPublicRoute = publicRoutes.includes(pathname);
    const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));

    // Se não autenticado e tenta acessar rota protegida, vai para login
    if (!isAuthenticated && isProtectedRoute) {
      router.push('/auth/login');
    }
    // Se autenticado e tenta acessar login, vai para hub
    else if (isAuthenticated && pathname === '/auth/login') {
      router.push('/main/hub');
    }
  }, [isAuthenticated, isLoading, pathname, router]);

  // Se ainda carregando, mostra spinner
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <LoadingSpinner size="w-12 h-12" color="text-primary" />
      </div>
    );
  }

  return <>{children}</>;
};

export default AuthProvider;