// CAMINHO: frontend/middleware.ts
//
// Middleware do Next.js — executado no servidor antes de cada request.
// Protege rotas sem depender de JavaScript no cliente.
//
// Regras:
//  1. /main/*  sem cookie de token   → redireciona para /auth/login
//  2. /auth/*  com cookie de token   → redireciona para /main/hub (já logado)
//  3. /main/admin  sem role=admin    → redireciona para /main/hub

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const token      = request.cookies.get('accessToken')?.value;
  const userCookie = request.cookies.get('user')?.value;

  const isProtected = pathname.startsWith('/main');
  const isAuthPage  = pathname.startsWith('/auth');

  // ── Regra 1: rota protegida sem token → login ──────────────────────────────
  if (isProtected && !token) {
    const loginUrl = new URL('/auth/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);   // preserva destino original
    return NextResponse.redirect(loginUrl);
  }

  // ── Regra 2: já autenticado tentando acessar login → hub ──────────────────
  if (isAuthPage && token) {
    return NextResponse.redirect(new URL('/main/hub', request.url));
  }

  // ── Regra 3: /main/admin sem role=admin → hub ─────────────────────────────
  if (pathname.startsWith('/main/admin') && token) {
    try {
      const user = JSON.parse(userCookie ?? '{}') as { role?: string };
      if (user?.role !== 'admin') {
        return NextResponse.redirect(new URL('/main/hub', request.url));
      }
    } catch {
      // Cookie corrompido — redireciona para hub por segurança
      return NextResponse.redirect(new URL('/main/hub', request.url));
    }
  }

  return NextResponse.next();
}

// Aplica apenas nas rotas relevantes — evita rodar em assets, _next, api, etc.
export const config = {
  matcher: ['/main/:path*', '/auth/:path*'],
};
