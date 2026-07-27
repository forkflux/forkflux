import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Expose FE_-prefixed env vars to client code via import.meta.env.
  // (Vite's default prefix is VITE_; we use FE_ for "frontend".)
  envPrefix: ['FE_'],
})
