import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API_TARGET = process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    // Proxied so the dashboard uses same-origin URLs in dev and in production,
    // where FastAPI serves the built assets itself.
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true, ws: true },
    },
  },
});
