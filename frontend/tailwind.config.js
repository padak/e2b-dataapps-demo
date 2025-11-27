/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Light mode colors
        light: {
          bg: '#f8fafc',
          surface: '#ffffff',
          border: '#e2e8f0',
          muted: '#94a3b8',
          text: '#334155',
          bright: '#0f172a',
        },
        // Dark mode colors (terminal theme)
        dark: {
          bg: '#0a0e14',
          surface: '#0d1117',
          border: '#1c2128',
          muted: '#484f58',
          text: '#c9d1d9',
          bright: '#f0f6fc',
        },
        // Accent colors (same for both modes)
        accent: {
          green: '#3fb950',
          cyan: '#39c5cf',
          orange: '#d29922',
          red: '#f85149',
          purple: '#a371f7',
          blue: '#58a6ff',
        },
        // Legacy terminal colors for backward compatibility
        terminal: {
          bg: '#0a0e14',
          surface: '#0d1117',
          border: '#1c2128',
          muted: '#484f58',
          text: '#c9d1d9',
          bright: '#f0f6fc',
          green: '#3fb950',
          cyan: '#39c5cf',
          orange: '#d29922',
          red: '#f85149',
          purple: '#a371f7',
          blue: '#58a6ff',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'Consolas', 'monospace'],
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
      },
      animation: {
        'glow': 'glow 2s ease-in-out infinite alternate',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'typing': 'typing 0.5s steps(1) infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'fade-in': 'fadeIn 0.5s ease-out',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(57, 197, 207, 0.3), 0 0 10px rgba(57, 197, 207, 0.2)' },
          '100%': { boxShadow: '0 0 10px rgba(57, 197, 207, 0.5), 0 0 20px rgba(57, 197, 207, 0.3)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        typing: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(57, 197, 207, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(57, 197, 207, 0.03) 1px, transparent 1px)',
        'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
}
