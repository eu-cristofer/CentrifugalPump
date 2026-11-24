import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // "/" for local serving; the Pages workflow sets "/<repo>/app/"
  base: process.env.PUMPFLOW_BASE ?? "/",
  plugins: [react()],
  publicDir: "public",
  worker: { format: "es" },
  build: { target: "es2022" },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["src/test-setup.ts"],
  },
});
