import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forwarded as-is (no /api stripping) — the backend serves its API
      // under /api in both dev and production, so the same frontend build
      // works unmodified whether it's proxied by Vite or served by FastAPI
      // itself (see app/main.py's static-file mount).
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
