import { defineConfig } from "vite";

export default defineConfig({
  base: "./", // relative paths: works on Vercel, GitHub Pages sub-paths and file servers
  build: { chunkSizeWarningLimit: 1500 },
  test: { include: ["tests/**/*.test.ts"] },
});
