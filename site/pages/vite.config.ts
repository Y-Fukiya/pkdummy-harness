import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL("./", import.meta.url)),
  base: "/pkdummy-harness/parameters/",
  plugins: [react()],
  css: {
    postcss: fileURLToPath(new URL("../", import.meta.url)),
  },
  build: {
    outDir: fileURLToPath(new URL("../../docs/parameters/", import.meta.url)),
    emptyOutDir: false,
    assetsDir: "atlas-assets",
  },
});
