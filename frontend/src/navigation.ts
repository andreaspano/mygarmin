// Dove si trova la pagina, nell'URL (todo 51, allargato dal todo 55).
//
// Niente router di libreria: la Day gestiva gia' il suo giorno con
// `URLSearchParams` e `history.pushState`, e per due pagine basta la stessa
// idea allargata. Lo stato sta nella stringa di ricerca e non nel percorso:
// i percorsi veri (`/week`) vorrebbero il fallback a `index.html` nel server
// di sviluppo e in quello dell'API, e non vale il prezzo.
//
// Due assi, come il menu a due righe: `?period=` dice il periodo (day o
// week), `?view=` che cosa se ne guarda (report o trend).
//
// `?page=week` e' la forma vecchia e continua a valere: i link scritti prima
// del todo 55 aprono la Week col suo Report. Senza niente si apre
// Day/Report, cosi' anche `?day=2026-10-07` funziona come prima.
export type Page = "day" | "week";
export type View = "report" | "trend";

/** L'ampiezza della finestra del Trend: gli stessi estremi che l'API
 * accetta (`TREND_MIN_DAYS` e `TREND_MAX_DAYS` in `daily_data.py`), cosi' il
 * cursore non puo' chiedere una finestra che riceve un 422. */
export const MIN_DAYS = 5;
export const MAX_DAYS = 365;
export const DEFAULT_DAYS = 28;

function search(): URLSearchParams {
  return new URLSearchParams(window.location.search);
}

export function pageFromUrl(): Page {
  const params = search();
  // `page` e' la forma vecchia: si guarda solo se `period` non c'e'.
  const value = params.get("period") ?? params.get("page");
  return value === "week" ? "week" : "day";
}

export function viewFromUrl(): View {
  return search().get("view") === "trend" ? "trend" : "report";
}

/** I giorni del Trend, riportati fra gli estremi; `DEFAULT_DAYS` se manca o
 * non e' un numero. */
export function daysFromUrl(): number {
  // Senza il controllo sul nullo `Number(null)` sarebbe 0, che e' un numero
  // finito: il cursore partiva dal minimo invece che da 28.
  const text = search().get("days");
  const value = text === null ? NaN : Number(text);
  if (!Number.isFinite(value)) return DEFAULT_DAYS;
  return Math.min(MAX_DAYS, Math.max(MIN_DAYS, Math.round(value)));
}

/** Il valore di un parametro dell'URL, o `null`. */
export function paramFromUrl(name: string): string | null {
  return search().get(name);
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
 * collegamento vero, che si puo' aprire in una scheda nuova.
 *
 * Tiene il giorno, il lunedi' e l'ampiezza del Trend: passando da Report a
 * Trend si resta sul giorno che si stava guardando, che e' il motivo per cui
 * il menu e' annidato. E toglie sempre `page`, la forma vecchia, cosi' i due
 * modi di dire il periodo non finiscono insieme nello stesso URL. */
export function hrefFor(page: Page, view: View = "report"): string {
  const params = search();
  params.delete("page");
  if (page === "day") params.delete("period");
  else params.set("period", page);
  if (view === "report") params.delete("view");
  else params.set("view", view);
  const text = params.toString();
  return text ? `?${text}` : "?";
}
