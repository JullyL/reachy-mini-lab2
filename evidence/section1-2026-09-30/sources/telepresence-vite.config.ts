/**
 * Vite config for the Telepresence app. See
 * `reachy_mini_emotions/vite.config.ts` for the shared rationale.
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
    dedupe: [
      "react",
      "react-dom",
      "react/jsx-runtime",
      "@emotion/react",
      "@emotion/styled",
      "@mui/material",
      "@mui/icons-material",
    ],
  },
  optimizeDeps: {
    include: [
      "@pollen-robotics/reachy-mini-sdk",
      "@pollen-robotics/reachy-mini-sdk/host",
      "@pollen-robotics/reachy-mini-sdk/host/auto",
      "@pollen-robotics/reachy-mini-sdk/host/embed",
    ],
  },
  server: {
    port: 5183, // reserved dev port (unique per project)
    host: true,
  },
  preview: {
    port: 8080,
    host: true,
  },
});
