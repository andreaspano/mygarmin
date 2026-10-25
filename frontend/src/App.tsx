// Quale pagina mostrare (todo 51). Legge `?period=` e `?view=` dall'URL e
// segue il tasto indietro del browser; la pagina sceglie da sola il resto
// dei suoi parametri (il giorno, il lunedi', i giorni del Trend).
import { useEffect, useState } from "react";

import { DayPage } from "./components/DayPage";
import { WeekPage } from "./components/WeekPage";
import { pageFromUrl, viewFromUrl, type Page, type View } from "./navigation";

export function App() {
  const [page, setPage] = useState<Page>(() => pageFromUrl());
  const [view, setView] = useState<View>(() => viewFromUrl());

  useEffect(() => {
    const onPop = () => {
      setPage(pageFromUrl());
      setView(viewFromUrl());
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // Il Trend per ora e' solo della Day: sulla Week `view` si ignora.
  return page === "week" ? <WeekPage /> : <DayPage view={view} />;
}
