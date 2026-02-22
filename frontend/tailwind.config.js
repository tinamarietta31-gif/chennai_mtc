/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        background: '#0f172a',
        surface: 'rgba(30, 41, 59, 0.7)',
        surfaceHover: 'rgba(51, 65, 85, 0.8)',
        primary: {
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
        },
        accent: {
          neon: '#06b6d4',
          purple: '#a855f7',
          pink: '#ec4899',
        },
        mtc: {
          red: '#f43f5e',
          blue: '#3b82f6',
          green: '#10b981',
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
        md: '8px',
        lg: '16px',
        xl: '24px',
      },
      boxShadow: {
        'glass': '0 4px 30px rgba(0, 0, 0, 0.1)',
        'neon': '0 0 15px rgba(6, 182, 212, 0.5)',
      }
    },
  },
  plugins: [],
}
