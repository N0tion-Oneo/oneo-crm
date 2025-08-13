import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ["class"],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/features/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      // Reduced font sizes (75% of Tailwind defaults) for more compact UI
      fontSize: {
        'xs': ['0.5625rem', { lineHeight: '0.75rem' }],     // 9px instead of 12px
        'sm': ['0.6875rem', { lineHeight: '1rem' }],        // 11px instead of 14px
        'base': ['0.75rem', { lineHeight: '1.125rem' }],    // 12px instead of 16px
        'lg': ['1.125rem', { lineHeight: '1.5rem' }],       // 18px instead of 24px
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],       // 20px instead of 24px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],          // 24px instead of 32px
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],     // 30px instead of 40px
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],       // 36px instead of 48px
        '5xl': ['3rem', { lineHeight: '1' }],               // 48px instead of 64px
        '6xl': ['3.75rem', { lineHeight: '1' }],            // 60px instead of 80px
      },
      // Reduced spacing scale (75% of Tailwind defaults) for more compact layout
      spacing: {
        'px': '1px',
        '0': '0px',
        '0.5': '0.125rem',    // 2px instead of 2px (unchanged)
        '1': '0.1875rem',     // 3px instead of 4px
        '1.5': '0.28125rem',  // 4.5px instead of 6px
        '2': '0.375rem',      // 6px instead of 8px
        '2.5': '0.46875rem',  // 7.5px instead of 10px
        '3': '0.5625rem',     // 9px instead of 12px
        '3.5': '0.65625rem',  // 10.5px instead of 14px
        '4': '0.75rem',       // 12px instead of 16px
        '5': '0.9375rem',     // 15px instead of 20px
        '6': '1.125rem',      // 18px instead of 24px
        '7': '1.3125rem',     // 21px instead of 28px
        '8': '1.5rem',        // 24px instead of 32px
        '9': '1.6875rem',     // 27px instead of 36px
        '10': '1.875rem',     // 30px instead of 40px
        '11': '2.0625rem',    // 33px instead of 44px
        '12': '2.25rem',      // 36px instead of 48px
        '14': '2.625rem',     // 42px instead of 56px
        '16': '3rem',         // 48px instead of 64px
        '20': '3.75rem',      // 60px instead of 80px
        '24': '4.5rem',       // 72px instead of 96px
        '28': '5.25rem',      // 84px instead of 112px
        '32': '6rem',         // 96px instead of 128px
        '36': '6.75rem',      // 108px instead of 144px
        '40': '7.5rem',       // 120px instead of 160px
        '44': '8.25rem',      // 132px instead of 176px
        '48': '9rem',         // 144px instead of 192px
        '52': '9.75rem',      // 156px instead of 208px
        '56': '10.5rem',      // 168px instead of 224px
        '60': '11.25rem',     // 180px instead of 240px
        '64': '12rem',        // 192px instead of 256px
        '72': '13.5rem',      // 216px instead of 288px
        '80': '15rem',        // 240px instead of 320px
        '96': '18rem',        // 288px instead of 384px
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
export default config