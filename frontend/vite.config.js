import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    // 构建输出目录：输出到项目根目录的 dist 目录
    // 这样 Docker 构建时可以从 /app/dist 复制文件
    outDir: '../dist',
    emptyOutDir: true
  },
  server: {
    port: 5173,
    proxy: {
      '^/api/.*': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
