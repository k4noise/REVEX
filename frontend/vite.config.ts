/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import dotenv from "dotenv";

dotenv.config({
  path: path.resolve(__dirname, ".env"),
});


export default defineConfig({
  plugins: [
    tanstackRouter({ target: "react", autoCodeSplitting: true }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    globals: true,
    setupFiles: ["./test-setup.ts"],
    environment: "jsdom",
  },
  server: {
    strictPort: true,
    port: 3000,
    proxy: {
      "/api": {
        target: process.env.BACKEND_URL,
        changeOrigin: true,
        rewrite: (path) => path,
      },
      "/images": {
        target: process.env.BACKEND_URL,
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
});
