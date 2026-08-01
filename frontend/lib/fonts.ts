// lib/fonts.ts
import { Inter, Poppins, Barlow, Barlow_Condensed } from 'next/font/google';

// Configuração da fonte Inter
// Usada para textos de corpo e interfaces mais neutras
export const inter = Inter({
  subsets: ['latin'], // Carrega apenas os caracteres latinos<br/>
  variable: '--font-inter', // Define uma variável CSS para fácil acesso<br/>
  display: 'swap', // Garante que o texto seja visível durante o carregamento da fonte
});

// Configuração da fonte Poppins
// Usada para títulos e elementos de destaque, com diferentes pesos
export const poppins = Poppins({
  subsets: ['latin'], // Carrega apenas os caracteres latinos<br/>
  variable: '--font-poppins', // Define uma variável CSS para fácil acesso<br/>
  weight: ['300', '400', '500', '600', '700'], // Pesos de fonte disponíveis<br/>
  display: 'swap', // Garante que o texto seja visível durante o carregamento da fonte
});

// Configuração da fonte Barlow
// Usada no visual "Dr. Tilap-IA" (home e login) como fonte de corpo
export const barlow = Barlow({
  subsets: ['latin'],
  variable: '--font-barlow',
  weight: ['400', '500', '700'],
  display: 'swap',
});

// Configuração da fonte Barlow Condensed
// Usada no visual "Dr. Tilap-IA" (home e login) como fonte de títulos
export const barlowCondensed = Barlow_Condensed({
  subsets: ['latin'],
  variable: '--font-barlow-condensed',
  weight: ['400', '600'],
  display: 'swap',
});