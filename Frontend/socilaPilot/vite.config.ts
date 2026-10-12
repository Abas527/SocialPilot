import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/projects': 'http://localhost:8000',
      '/social': 'http://localhost:8000',
      '/wallet': 'http://localhost:8000',
      '/tips': 'http://localhost:8000',
      '/marketplace': 'http://localhost:8000',
      '/export': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/jobs': 'http://localhost:8000',
      '/notifications': 'http://localhost:8000',
      '/ai': 'http://localhost:8000',
      '/config': 'http://localhost:8000',
      '/demo': 'http://localhost:8000',
      '/public': 'http://localhost:8000',
      '/publications': 'http://localhost:8000',
    },
  },
})
