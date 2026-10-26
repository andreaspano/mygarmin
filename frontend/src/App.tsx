// Quale pagina mostrare (todo 51). Legge `?period=` e `?view=` dall'URL e
// segue il tasto indietro del browser; la pagina sceglie da sola il resto
// dei suoi parametri (il giorno, il lunedi', i giorni del Trend).
import { useEffect, useState } from "react";

import { DayPage } from "./components/DayPage";
import { PlanPage } from "./components/PlanPage";
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

  // Il Trend per ora e' solo della Day: sulla Week e sulla Plan `view` si
  // ignora.
  if (page === "week") return <WeekPage />;
  if (page === "plan") return <PlanPage />;
  return <DayPage view={view} />;
}
