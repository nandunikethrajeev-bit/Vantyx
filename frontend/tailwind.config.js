/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        vantyx: {
          bg: '#090909',
          surface: '#171717',
          surfaceElevated: '#1F1F1F',
          border: '#262626',
          borderSubtle: '#1C1C1C',
          accent: '#D49A45',
          accentHover: '#E5B064',
          accentDim: '#8B6226',
          textPrimary: '#EAE8E3',
          textSecondary: '#9E9C96',
          textMuted: '#666561',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'monospace',
        ],
      },
      letterSpacing: {
        widest: '.2em',
        tightest: '-.03em',
      },
    },
  },
  plugins: [],
}
