import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  // @yao/core is a workspace TS package — let Vite transpile it as source
  // rather than pre-bundling it as a dependency.
  optimizeDeps: { exclude: ['@yao/core'] },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:4711',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist', emptyOutDir: true },
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg'],
      manifest: {
        name: '空靈次元 Ethereal Dimension',
        short_name: '空靈次元',
        description: 'A self-evolving AI spirit pet.',
        lang: 'zh-Hant',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#06060d',
        theme_color: '#06060d',
        icons: [
          { src: 'icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
          { src: 'icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'maskable' },
        ],
      },
      workbox: {
        // App shell is precached; pet state always comes live from the backend.
        navigateFallbackDenylist: [/^\/api/],
      },
    }),
  ],
});
