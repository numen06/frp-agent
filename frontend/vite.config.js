import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    target: "es2022", // noVNC 1.7 probes browser codec support with top-level await.
    outDir: '../dist',
    emptyOutDir: true
  },
  server: {
    port: 5173,
    proxy: {
      '^/api/.*': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: false // Preserve Host for WebSocket same-origin validation.
      }
    }
  }
})
