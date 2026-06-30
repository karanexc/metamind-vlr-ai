/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Hybrid palette: Linear's warmth + Vercel's restraint
        bg: '#08080A',           // page background
        surface: {
          DEFAULT: '#0F0F12',     // cards
          hover: '#161619',
          high: '#1A1A1E',
        },
        border: {
          DEFAULT: '#1F1F24',
          strong: '#2A2A30',
          accent: '#FA4454',
        },
        ink: {
          DEFAULT: '#F5F5F7',    // primary text
          soft: '#A1A1AA',       // secondary text
          dim: '#6B6B72',        // tertiary
        },
        accent: {
          DEFAULT: '#FA4454',
          hover: '#FF5C6B',
          dim: '#7A2730',
        },
        success: '#22C55E',
        warning: '#F59E0B',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'monospace'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // Vercel-style hero scale
        'hero': ['clamp(2.5rem, 7vw, 5.5rem)', { lineHeight: '1', letterSpacing: '-0.04em' }],
        'display': ['clamp(2rem, 4vw, 3.5rem)', { lineHeight: '1.05', letterSpacing: '-0.03em' }],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'fade-up': 'fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scaleIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'shimmer': 'shimmer 2s linear infinite',
        'glow-pulse': 'glowPulse 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        glowPulse: {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '0.8' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-hero': 'radial-gradient(ellipse at top, rgba(250, 68, 84, 0.08), transparent 50%)',
        'gradient-card': 'linear-gradient(180deg, #0F0F12 0%, #131316 100%)',
      },
    },
  },
  plugins: [],
};
