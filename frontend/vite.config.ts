/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev server only: forwards /api to a locally running backend, mirroring what nginx does in
// the container (ADR-0002). Never part of the built bundle. Exempt from the localhost check
// by name (FR-FE-016).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      include: ["src/**"],
      exclude: ["src/api/types.ts", "src/main.tsx"],
      thresholds: { statements: 50, branches: 50, functions: 50, lines: 50 }, // M8 test-frontend
    },
  },
});
