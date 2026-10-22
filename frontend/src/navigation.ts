// Dove si trova la pagina, nell'URL (todo 51).
//
// Niente router di libreria: la Day gestiva gia' il suo giorno con
// `URLSearchParams` e `history.pushState`, e per due pagine basta la stessa
// idea allargata. Lo stato sta nella stringa di ricerca — `?page=week` —
// e non nel percorso: i percorsi veri (`/week`) vorrebbero il fallback a
// `index.html` nel server di sviluppo e in quello dell'API, e non vale il
// prezzo.
//
// Senza `page` si apre la Day, cosi' i collegamenti di prima
// (`?day=2026-10-07`) continuano a funzionare.
export type Page = "day" | "week";

export function pageFromUrl(): Page {
  return new URLSearchParams(window.location.search).get("page") === "week" ? "week" : "day";
}

/** Il valore di un parametro dell'URL, o `null`. */
export function paramFromUrl(name: string): string | null {
  return new URLSearchParams(window.location.search).get(name);
}

/** Cambia l'URL senza ricaricare, e lascia una voce nella cronologia: il
 * tasto indietro del browser torna dov'eri. `null` toglie il parametro.
 *
 * Emette anche un `popstate` finto, che il browser manda solo su avanti e
 * indietro: cosi' chi segue l'URL (`App`, e le pagine per i loro parametri)
 * si aggiorna anche quando a muoversi e' un tasto della pagina, senza che
 * nessuno debba ricaricare. */
export function pushUrl(changes: Record<string, string | null>): void {
  const url = new URL(window.location.href);
  for (const [name, value] of Object.entries(changes)) {
    if (value === null) url.searchParams.delete(name);
    else url.searchParams.set(name, value);
  }
  window.history.pushState({}, "", url);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

/** L'indirizzo di una pagina, per gli `href` della barra in alto: un
 * collegamento vero, che si puo' aprire in una scheda nuova. */
export function hrefFor(page: Page): string {
  return page === "day" ? "?" : `?page=${page}`;
}
