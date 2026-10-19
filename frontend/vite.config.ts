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
    // Vite ascolta solo su 127.0.0.1, anche su mutolo. Dalle altre macchine
    // della tailnet si arriva con `tailscale serve`, che ascolta
    // sull'indirizzo Tailscale e gira le richieste qui:
    //   sudo tailscale serve --bg --http=5173 http://127.0.0.1:5173
    // L'host che arriva e' allora `mutolo` (MagicDNS, con la porta che Vite
    // non guarda), oppure `mutolo.<tailnet>.ts.net` se nella tailnet si
    // accendono i certificati HTTPS e si serve in https. Vite rifiuta i nomi
    // che non conosce, e li' servono entrambi.
    allowedHosts: [".ts.net", "mutolo"],
    proxy: {
      "/api": API,
      "/icons": API,
    },
  },
});
