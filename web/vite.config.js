import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      // '@' 指向 src，这样 import 不用写一串 ../
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    port: 5173,

    // ========================================================================
    // 开发代理 —— 前端调后端的关键配置
    // ========================================================================
    // 前端里写 axios.get('/api/...')，Vite 会把这个请求转发到 8080 的 Java。
    //
    // 【为什么要代理，而不是直接写 http://localhost:8080】
    // 浏览器有同源策略：5173 调 8080 算跨域。虽然 Java 那边配了 CORS，
    // 但开发时用代理更好，理由有两个：
    //   1. 前端代码里写相对路径 '/api/...'，上线后前后端同域部署，一个字不用改
    //   2. 不用处理预检请求（OPTIONS）和 cookie 的种种跨域限制
    //
    // Java 那边的 CORS 配置仍然保留 —— 那是给"绕过浏览器直接调接口"
    // 的场景（Postman、小程序、第三方）兜底的，不是给这个前端用的。
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
