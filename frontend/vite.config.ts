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
});
