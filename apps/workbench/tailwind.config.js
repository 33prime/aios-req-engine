/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          primary: '#3FAF7A',
          'primary-hover': '#33a06d',
          'primary-active': '#2a8f5f',
          'primary-light': 'rgba(63, 175, 122, 0.08)',
          'primary-ring': 'rgba(63, 175, 122, 0.25)',
        },
        accent: {
          DEFAULT: '#044159',
          hover: '#033344',
          light: 'rgba(4, 65, 89, 0.06)',
        },
        surface: {
          page: '#FAFAFA',
          card: '#FFFFFF',
          subtle: '#F5F5F5',
          muted: '#F9F9F9',
        },
        border: {
          DEFAULT: '#E5E5E5',
          strong: '#D4D4D4',
        },
        text: {
          primary: '#1D1D1F',
          body: '#333333',
          secondary: '#4B4B4B',
          muted: '#7B7B7B',
          placeholder: '#999999',
        },
        status: {
          'success-bg': '#D1FAE5',
          'success-text': '#047857',
          'warning-bg': '#FEF3C7',
          'warning-text': '#B45309',
          'error-bg': '#FEE2E2',
          'error-text': '#991B1B',
          'info-bg': '#DBEAFE',
          'info-text': '#1D4ED8',
        },
      },
      borderRadius: {
        sm: '4px',
        md: '8px',
        lg: '12px',
        full: '9999px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(0,0,0,0.04)',
        md: '0 4px 6px rgba(0,0,0,0.08)',
        lg: '0 8px 16px rgba(0,0,0,0.12)',
      },
      keyframes: {
        'slide-in-right': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        typing: {
          '0%, 80%, 100%': { transform: 'translateY(0)' },
          '40%': { transform: 'translateY(-4px)' },
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
