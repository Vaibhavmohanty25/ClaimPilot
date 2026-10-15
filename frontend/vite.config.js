import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ command, mode }) => {
  if (command === "build") {
    const { VITE_API_BASE_URL: apiUrl } = loadEnv(mode, process.cwd(), "VITE_");
    let backend;
    try {
      backend = new URL(apiUrl);
    } catch {
      // Missing and relative URLs cannot identify the hosted backend.
    }
    const hostname = backend?.hostname.replace(/\.$/, "");
    const isLocal = hostname === "localhost" || hostname?.endsWith(".localhost") ||
      /^127\./.test(hostname || "") || hostname === "0.0.0.0" ||
      hostname === "[::1]" || hostname === "[::]" ||
      /^\[::ffff:7f/i.test(hostname || "");

    if (!backend || backend.protocol !== "https:" || isLocal) {
      throw new Error(
        "VITE_API_BASE_URL must be the HTTPS URL of your deployed backend " +
        "(for example https://api.your-domain.com), not localhost. " +
        "Set it in your frontend hosting environment and rebuild. " +
        "The backend must allow the frontend origin through CORS."
      );
    }
  }

  return { plugins: [react(), tailwindcss()] };
});
