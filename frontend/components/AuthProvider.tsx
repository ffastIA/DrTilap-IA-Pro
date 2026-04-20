'use client';
// CAMINHO: frontend/components/AuthProvider.tsx

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import LoadingSpinner from './LoadingSpinner';

interface AuthProviderProps {
  children: React.ReactNode;
}

const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const { isAuthenticated, isLoading, restoreAuth } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    restoreAuth();
  }, [restoreAuth]);

  useEffect(() => {
    if (isLoading) return;

    const publicRoutes = ['/', '/auth/login'];
    const protectedRoutes = ['/main'];
    const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));

    if (!isAuthenticated && isProtectedRoute) {
      router.push('/auth/login');
    }

    if (isAuthenticated && pathname === '/auth/login') {
      router.push('/main/hub');
    }
  }, [isAuthenticated, isLoading, pathname, router]);

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
