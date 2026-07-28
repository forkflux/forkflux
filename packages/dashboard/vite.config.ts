import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'FE_')
  const serviceEntry = env.FE_USE_MOCKS === 'true'
    ? './src/services/jobService.mock.ts'
    : './src/services/jobService.api.ts'

  return {
    plugins: [react()],
    // Expose FE_-prefixed env vars to client code via import.meta.env.
    // (Vite's default prefix is VITE_; we use FE_ for "frontend".)
    envPrefix: ['FE_'],
    resolve: {
      alias: {
        '@job-service': resolve(process.cwd(), serviceEntry),
      },
    },
  }
})
