import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Ajuste o base path para o deploy no GitHub Pages
  // Se o site estiver em username.github.io/repo-name/, use:
  // base: '/repo-name/apps/commodity-abm/'
  base: './',
  build: {
    outDir: 'dist',
    // Gera um único bundle inline (facilita embed)
    assetsInlineLimit: 100000,
  }
})
