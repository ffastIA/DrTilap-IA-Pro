import type { Config } from 'tailwindcss';
import { poppins } from './lib/fonts';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        poppins: ['var(--font-poppins)', 'sans-serif'],
      },
      colors: {
        primary: '#00C853',
        secondary: '#2196F3',
        accent: '#FFC107',
        background: '#1A1A1A',
        surface: '#2C2C2C',
        text: '#E0E0E0',
        textSecondary: '#B0B0B0',
        error: '#D32F2F',
        success: '#388E3C',
        warning: '#FBC02D',
        info: '#0288D1',
      },
    },
  },
  plugins: [],
};

export default config;