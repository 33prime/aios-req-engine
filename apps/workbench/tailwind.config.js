/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: '#044159',
          accent: '#88BABF',
          deepText: '#011F26',
          warmSand: '#F2E4BB',
          teal: '#3FAF7A',
          tealDark: '#25785A',
          green: '#3FAF7A',
          greenDark: '#25785A',
          greenLight: '#E8F5E9',
          navy: '#0A1E2F',
        },
        ui: {
          background: '#FAFAFA',
          cardBorder: '#E5E5E5',
          bodyText: '#4B4B4B',
          supportText: '#7B7B7B',
          headingDark: '#1D1D1F',
          buttonGray: '#F5F5F5',
          buttonGrayHover: '#E5E5E5',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'h1': ['26px', { lineHeight: '1.3', fontWeight: '600' }],
        'h2': ['20px', { lineHeight: '1.4', fontWeight: '500' }],
        'section': ['18px', { lineHeight: '1.4', fontWeight: '600' }],
        'body': ['16px', { lineHeight: '1.5', fontWeight: '400' }],
        'support': ['13px', { lineHeight: '1.5', fontWeight: '400' }],
        'badge': ['12px', { lineHeight: '1', fontWeight: '600', letterSpacing: '0.025em' }],
      },
      borderRadius: {
        'card': '8px',
      },
      boxShadow: {
        'card': '0 1px 2px rgba(0, 0, 0, 0.04)',
        'card-hover': '0 4px 6px rgba(0, 0, 0, 0.08)',
        'button-hover': '0 2px 4px rgba(0, 0, 0, 0.1)',
      },
      spacing: {
        'card': '16px',
      },
      keyframes: {
        'slide-in-right': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        typing: {
          '0%, 80%, 100%': { transform: 'translateY(0)' },
          '40%': { transform: 'translateY(-8px)' },
        },
      },
      animation: {
        'slide-in-right': 'slide-in-right 0.25s ease-out',
        typing: 'typing 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
