import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api is forwarded to the FastAPI server, just like the
// Kubernetes ingress does in production, so the front end code is identical in both.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
