import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";
import { RODDY_THEME_IDS, RODDY_THEME_STORAGE_KEY } from "./src/theme-data.js";
import { bootstrapTheme } from "./src/theme-bootstrap.js";

export default defineConfig(({ mode }) => {
  const privateAdmin = mode === "private-admin";
  return {
    base: privateAdmin ? "/control/" : "/",
    publicDir: privateAdmin ? false : "public",
    plugins: [
      vue(),
      tailwindcss(),
      {
        name: "roddy-theme-bootstrap",
        transformIndexHtml() {
          return [{
            tag: "script",
            attrs: { "data-roddy-theme-bootstrap": "" },
            children: `(${bootstrapTheme.toString()})(${JSON.stringify(RODDY_THEME_IDS)}, ${JSON.stringify(RODDY_THEME_STORAGE_KEY)});`,
            injectTo: "head-prepend",
          }];
        },
      },
    ],
    build: {
      outDir: privateAdmin ? "dist-admin" : "dist",
      rollupOptions: {
        input: privateAdmin ? { admin: resolve(__dirname, "admin.html") } : {
          main: resolve(__dirname, "index.html"),
          order: resolve(__dirname, "order.html"),
        },
      },
    },
  };
});
