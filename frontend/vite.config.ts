import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  // amazon-cognito-identity-js assumes a Node-style `global` object, which
  // browsers (and Vite) don't provide on their own.
  define: {
    global: 'globalThis',
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Axiom',
        short_name: 'Axiom',
        description: 'A first-principles Junior Cycle Higher Level Maths companion.',
        theme_color: '#3454d1',
        background_color: '#f3f6fb',
        display: 'standalone',
        // Icons land in the Milestone 10 visual design pass, alongside the
        // rest of the app's look — placeholder-free is better than wrong.
        icons: [],
      },
    }),
  ],
})
