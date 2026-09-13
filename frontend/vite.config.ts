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
        start_url: '/',
        // Rasterised from public/favicon.svg (the real Axiom mark — NOT
        // public/icons.svg, which is an unrelated sprite sheet of social
        // icons left over from the Vite template, despite looking like an
        // obvious source at a glance). "any" icons keep the logo on a
        // transparent background; "maskable" fills the whole canvas with
        // the theme colour and keeps the logo well inside the safe zone so
        // OS-applied masks (circle, squircle, …) never clip it.
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
})
