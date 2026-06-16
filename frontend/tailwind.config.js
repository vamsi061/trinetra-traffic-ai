/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        trinetra: {
          bg: '#0a0e17',
          card: '#13182a',
          card2: '#1a2040',
          accent: '#ef4444',
          accent2: '#22c55e',
          text: '#e2e8f0',
          muted: '#8892b0',
          border: '#1e2a4a',
        },
      },
    },
  },
  plugins: [],
}
