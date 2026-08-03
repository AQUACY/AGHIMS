/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: ['class', '.body--dark'],
  theme: {
    extend: {
      colors: {
        hms: {
          bg: {
            primary: 'var(--hms-bg-primary)',
            secondary: 'var(--hms-bg-secondary)',
            elevated: 'var(--hms-bg-elevated)',
          },
          surface: 'var(--hms-surface)',
          border: 'var(--hms-border)',
          accent: {
            DEFAULT: 'var(--hms-accent)',
            hover: 'var(--hms-accent-hover)',
            muted: 'var(--hms-accent-muted)',
          },
          healthcare: {
            DEFAULT: 'var(--hms-healthcare)',
            muted: 'var(--hms-healthcare-muted)',
          },
          success: 'var(--hms-success)',
          warning: 'var(--hms-warning)',
          critical: 'var(--hms-critical)',
          info: 'var(--hms-info)',
          text: {
            primary: 'var(--hms-text-primary)',
            secondary: 'var(--hms-text-secondary)',
            muted: 'var(--hms-text-muted)',
          },
        },
      },
      fontFamily: {
        sans: ['Manrope', 'Geist', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'Geist', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'SF Mono', 'Menlo', 'monospace'],
      },
      fontSize: {
        'hms-xs': ['var(--hms-text-xs)', { lineHeight: 'var(--hms-leading-normal)' }],
        'hms-sm': ['var(--hms-text-sm)', { lineHeight: 'var(--hms-leading-normal)' }],
        'hms-base': ['var(--hms-text-base)', { lineHeight: 'var(--hms-leading-normal)' }],
        'hms-lg': ['var(--hms-text-lg)', { lineHeight: 'var(--hms-leading-snug)' }],
        'hms-xl': ['var(--hms-text-xl)', { lineHeight: 'var(--hms-leading-snug)' }],
        'hms-2xl': ['var(--hms-text-2xl)', { lineHeight: 'var(--hms-leading-tight)' }],
        'hms-3xl': ['var(--hms-text-3xl)', { lineHeight: 'var(--hms-leading-tight)' }],
        'hms-4xl': ['var(--hms-text-4xl)', { lineHeight: 'var(--hms-leading-tight)' }],
      },
      borderRadius: {
        'hms-sm': 'var(--hms-radius-sm)',
        'hms-md': 'var(--hms-radius-md)',
        'hms-lg': 'var(--hms-radius-lg)',
        'hms-xl': 'var(--hms-radius-xl)',
        'hms-2xl': 'var(--hms-radius-2xl)',
      },
      boxShadow: {
        'hms-sm': 'var(--hms-shadow-sm)',
        'hms-md': 'var(--hms-shadow-md)',
        'hms-lg': 'var(--hms-shadow-lg)',
        'hms-glow': 'var(--hms-shadow-glow-accent)',
      },
      transitionTimingFunction: {
        'hms-out': 'var(--hms-ease-out)',
        'hms-inout': 'var(--hms-ease-in-out)',
      },
      transitionDuration: {
        'hms-fast': 'var(--hms-duration-fast)',
        'hms-normal': 'var(--hms-duration-normal)',
        'hms-slow': 'var(--hms-duration-slow)',
      },
      spacing: {
        'header': 'var(--hms-header-height)',
        'sidebar': 'var(--hms-sidebar-width)',
        'sidebar-collapsed': 'var(--hms-sidebar-collapsed)',
      },
    },
  },
  plugins: [],
  corePlugins: {
    // Quasar already resets; avoid double-preflight conflicts where possible
    preflight: false,
  },
};
