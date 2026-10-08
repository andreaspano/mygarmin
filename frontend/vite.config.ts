// Vite per la pagina Day in React (todo 33). In sviluppo `/api` e `/icons`
// passano all'API (`make api`, 127.0.0.1:8000): il frontend usa solo
// percorsi relativi, e cosi' non serve CORS.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    // Vega (il grafico) da solo pesa piu' di un megabyte minificato: sta in
    // un pezzo a parte, caricato quando serve (`RunChart`), e il limite
    // dell'avviso si alza per lui.
    chunkSizeWarningLimit: 1500,
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": API,
      "/icons": API,
    },
  },
});
