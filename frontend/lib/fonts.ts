// lib/fonts.ts
import { Inter, Poppins } from 'next/font/google';

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