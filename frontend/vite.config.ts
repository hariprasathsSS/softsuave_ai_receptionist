import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/calls": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/dashboard": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/voice": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
