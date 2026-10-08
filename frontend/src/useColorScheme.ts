// Il tema del sistema (chiaro o scuro), aggiornato quando cambia. Lo usa il
// grafico, che ha due palette (`run_chart._PALETTES`); il resto della pagina
// segue il tema con le variabili CSS.
import { useEffect, useState } from "react";

const QUERY = "(prefers-color-scheme: dark)";

export type ColorScheme = "light" | "dark";

export function useColorScheme(): ColorScheme {
  const [scheme, setScheme] = useState<ColorScheme>(() =>
    window.matchMedia(QUERY).matches ? "dark" : "light",
  );
  useEffect(() => {
    const media = window.matchMedia(QUERY);
    const update = () => setScheme(media.matches ? "dark" : "light");
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return scheme;
}
