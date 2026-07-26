// CAMINHO: frontend/middleware.ts
//
// Middleware do Next.js — executado no servidor antes de cada request.
// Protege rotas sem depender de JavaScript no cliente.
//
// Regras:
//  1. /main/*  sem cookie de token   → redireciona para /auth/login
//  2. /auth/*  com cookie de token   → redireciona para /main/hub (já logado)
//  3. /main/admin  sem role=admin    → redireciona para /main/hub
//     (o papel é verificado contra a API REST do Supabase usando o próprio
//     access token do usuário — nunca a partir do cookie `user`, que é
//     gravável pelo próprio navegador e não prova nada por si só. A policy
//     de RLS `users_select_own` garante que a consulta só retorna a linha
//     do usuário autenticado pelo token.)

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

async function isAdminToken(token: string): Promise<boolean> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    // Configuração ausente — nega por padrão em vez de abrir uma falha de segurança silenciosa.
    return false;
  }
  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/users?select=role`, {
      headers: {
        Authorization: `Bearer ${token}`,
        apikey: SUPABASE_ANON_KEY,
      },
      cache: 'no-store',
    });
    if (!response.ok) {
      return false;
    }
    const rows = (await response.json()) as { role?: string }[];
    return Array.isArray(rows) && rows.length === 1 && rows[0]?.role === 'admin';
  } catch {
    // Rede indisponível/erro de parsing — falha fechada (nega acesso).
    return false;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const token = request.cookies.get('accessToken')?.value;

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

  // ── Regra 3: /main/admin sem role=admin (verificado via API) → hub ────────
  if (pathname.startsWith('/main/admin') && token) {
    const isAdmin = await isAdminToken(token);
    if (!isAdmin) {
      return NextResponse.redirect(new URL('/main/hub', request.url));
    }
  }

  return NextResponse.next();
}

// Aplica apenas nas rotas relevantes — evita rodar em assets, _next, api, etc.
export const config = {
  matcher: ['/main/:path*', '/auth/:path*'],
};
