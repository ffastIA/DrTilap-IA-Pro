// CAMINHO: frontend/app/auth/login/page.tsx

'use client';

// CAMINHO: frontend/app/auth/login/page.tsx

import { useState } from 'react';

import Link from 'next/link';

import { useLoginMutation } from '@/hooks/useLoginMutation';

export default function LoginPage() {

  const loginMutation = useLoginMutation();

  const [email, setEmail] = useState('');

  const [password, setPassword] = useState('');

  const [validationError, setValidationError] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {

    e.preventDefault();

    setValidationError('');

    setIsSubmitting(true);

    if (!email.trim()) {

      setValidationError('Email é obrigatório');

      setIsSubmitting(false);

      return;

    }

    if (!password) {

      setValidationError('Senha é obrigatória');

      setIsSubmitting(false);

      return;

    }

    if (email.length < 5 || !email.includes('@')) {

      setValidationError('Email inválido');

      setIsSubmitting(false);

      return;

    }

    if (password.length < 6) {

      setValidationError('Senha deve ter pelo menos 6 caracteres');

      setIsSubmitting(false);

      return;

    }

    try {

      await loginMutation.mutate({ email, password });

    } catch {

      // O hook já normaliza e expõe o erro

    } finally {

      setIsSubmitting(false);

    }

  };

  const handleInputChange = () => {

    setValidationError('');

  };

  return (

    <div className="w-full max-w-md">

      <div className="glass p-8 space-y-6 backdrop-blur-md">

        <div className="text-center">

          <h1 className="text-4xl font-bold text-white mb-2">

            🐟 Dr. Tilápia

          </h1>

          <p className="text-slate-300 text-lg">

            Autenticação Segura

          </p>

        </div>

        <form onSubmit={handleSubmit} className="space-y-4">

          <div>

            <label htmlFor="email" className="block text-sm font-medium text-slate-200 mb-2">

              Email

            </label>

            <input

              id="email"

              type="email"

              placeholder="seu@email.com"

              value={email}

              onChange={(e) => {

                setEmail(e.target.value);

                handleInputChange();

              }}

              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500 transition duration-200"

              disabled={loginMutation.isPending || isSubmitting}

            />

          </div>

          <div>

            <label htmlFor="password" className="block text-sm font-medium text-slate-200 mb-2">

              Senha

            </label>

            <input

              id="password"

              type="password"

              placeholder="••••••••"

              value={password}

              onChange={(e) => {

                setPassword(e.target.value);

                handleInputChange();

              }}

              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500 transition duration-200"

              disabled={loginMutation.isPending || isSubmitting}

            />

          </div>

          {validationError && (

            <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg animate-pulse">

              <p className="text-red-200 text-sm font-medium">

                ⚠️ {validationError}

              </p>

            </div>

          )}

          {loginMutation.isError && (

            <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg">

              <p className="text-red-200 text-sm font-medium">

                ❌{' '}

                {loginMutation.error?.message || 'Erro ao fazer login. Verifique suas credenciais.'}

              </p>

            </div>

          )}

          {loginMutation.isSuccess && (

            <div className="p-4 bg-green-500/20 border border-green-500/50 rounded-lg">

              <p className="text-green-200 text-sm font-medium">

                ✅ Login realizado com sucesso! Redirecionando...

              </p>

            </div>

          )}

          <button

            type="submit"

            disabled={loginMutation.isPending || isSubmitting}

            className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 disabled:from-slate-600 disabled:to-slate-600 text-white font-semibold rounded-lg transition-all duration-300 transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"

          >

            {loginMutation.isPending || isSubmitting ? (

              <span className="flex items-center justify-center gap-2">

                <svg

                  className="animate-spin h-5 w-5"

                  xmlns="http://www.w3.org/2000/svg"

                  fill="none"

                  viewBox="0 0 24 24"

                >

                  <circle

                    className="opacity-25"

                    cx="12"

                    cy="12"

                    r="10"

                    stroke="currentColor"

                    strokeWidth="4"

                  />

                  <path

                    className="opacity-75"

                    fill="currentColor"

                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"

                  />

                </svg>

                Entrando...

              </span>

            ) : (

              'Entrar no Sistema'

            )}

          </button>

        </form>

        <div className="relative">

          <div className="absolute inset-0 flex items-center">

            <div className="w-full border-t border-slate-600/50" />

          </div>

          <div className="relative flex justify-center text-sm">

            <span className="px-2 bg-slate-900 text-slate-400">Ambiente de Testes</span>

          </div>

        </div>

        <div className="bg-slate-700/30 border border-slate-600/50 rounded-lg p-4">

          <p className="text-xs text-slate-400 mb-2 font-medium">📝 Credenciais de Teste:</p>

          <div className="space-y-1 text-xs text-slate-300">

            <p>

              <span className="font-mono bg-slate-800 px-2 py-1 rounded">

                admin@drtilapia.com

              </span>

            </p>

            <p>

              <span className="font-mono bg-slate-800 px-2 py-1 rounded">

                teste123

              </span>

            </p>

          </div>

        </div>

        <div className="text-center text-sm text-slate-400 space-y-2">

          <p>Ou retorne para a página inicial</p>

          <Link

            href="/"

            className="inline-block text-cyan-400 hover:text-cyan-300 font-medium transition duration-200"

          >

            ← Voltar ao Início

          </Link>

        </div>

        <div className="pt-4 border-t border-slate-600/30">

          <p className="text-xs text-slate-500 text-center leading-relaxed">

            Este é um sistema seguro de consultoria IA. Seus dados são criptografados

            e armazenados com segurança no Supabase.

          </p>

        </div>

      </div>

    </div>

  );

}
