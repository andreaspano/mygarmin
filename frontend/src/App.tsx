// Quale pagina mostrare (todo 51). Legge `?page=` dall'URL e segue il tasto
// indietro del browser; la pagina sceglie da sola il resto dei suoi
// parametri (il giorno, il lunedi).
import { useEffect, useState } from "react";

import { DayPage } from "./components/DayPage";
import { WeekPage } from "./components/WeekPage";
import { pageFromUrl, type Page } from "./navigation";

export function App() {
  const [page, setPage] = useState<Page>(() => pageFromUrl());

  useEffect(() => {
    const onPop = () => setPage(pageFromUrl());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  return page === "week" ? <WeekPage /> : <DayPage />;
}
