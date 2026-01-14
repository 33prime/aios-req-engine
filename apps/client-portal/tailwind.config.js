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
        // Primary teal
        primary: {
          DEFAULT: '#009b87',
          hover: '#007a6b',
          light: '#00b89c',
        },
        // Emerald accents (for auto-populated content)
        emerald: {
          50: '#ecfdf5',
          100: '#d1fae5',
        },
        // Gray scale
        gray: {
          50: '#FAFAFA',
          100: '#F5F5F5',
          200: '#E5E5E5',
          300: '#D4D4D4',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          900: '#171717',
        },
        // Status colors
        success: {
          text: '#065f46',
          bg: '#ecfdf5',
        },
        warning: {
          text: '#92400e',
          bg: '#fffbeb',
        },
        error: {
          text: '#991b1b',
          bg: '#fee2e2',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
