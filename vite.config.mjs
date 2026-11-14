import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { singleFilePlugin } from "./scripts/single-file.mjs";

export default {
  base: "./",
  publicDir: false,
  plugins: [react(), tailwindcss(), singleFilePlugin()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { host: "127.0.0.1", strictPort: true, allowedHosts: [] },
  build: {
    cssCodeSplit: false,
    sourcemap: false,
    assetsInlineLimit: () => true,
    rolldownOptions: { output: { codeSplitting: false } },
  },
};
