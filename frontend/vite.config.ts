// vitest/config re-exports Vite's defineConfig with the `test` key typed.
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // T008: Proxy /api requests to FastAPI backend in development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // T001: Output to backend/static so FastAPI can serve it
    outDir: '../backend/static',
    emptyOutDir: true,
  },
  test: {
    // T007: Vitest configuration
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    // T093: Vitest owns src/ only. The specs under e2e/ are Playwright's and
    // throw at collection under Vitest, which would fail `npm test` outright.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      // Application source only: e2e/ is Playwright's source, not code under test.
      include: ['src/**/*.{ts,tsx}'],
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 90,
        statements: 90,
      },
    },
  },
})
