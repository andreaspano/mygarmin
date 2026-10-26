// La barra in alto (todo 34), su due righe dal todo 55.
//
// Prima riga il **periodo** (Day, Week), seconda riga **cosa se ne guarda**
// (Report, Trend): due assi veri, mentre prima Day, Week e Activities
// stavano in fila come se fossero la stessa cosa. Activities non e' un
// periodo e sta a destra, staccata, ancora disattivata.
//
// Niente voci grigie nei due menu: Month e Year si aggiungono quando
// esistono, non prima. Resta disattivata solo Activities, che la forma della
// barra ce l'ha gia'.
import { hrefFor, type Page, type View } from "../navigation";

const PERIODI: { page: Page; label: string }[] = [
  { page: "day", label: "Day" },
  { page: "week", label: "Week" },
];
// Il Trend per ora c'e' solo sotto Day: la Week ha il suo Report e basta.
const VISTE: { view: View; label: string; only?: Page }[] = [
  { view: "report", label: "Report" },
  { view: "trend", label: "Trend", only: "day" },
];

export function TopBar({
  current = "day",
  view = "report",
}: {
  current?: Page;
  view?: View;
}) {
  const viste = VISTE.filter((v) => !v.only || v.only === current);
  // La vista si porta dietro solo dove esiste: andando sulla Week, che il
  // Trend non ce l'ha, il collegamento torna al Report invece di lasciare
  // nell'URL una vista che quella pagina ignora.
  const vistaSu = (page: Page): View =>
    VISTE.some((v) => v.view === view && (!v.only || v.only === page)) ? view : "report";
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="topbar-menus">
          <nav aria-label="Periods">
            {PERIODI.map(({ page, label }) => (
              <a
                key={page}
                className={page === current ? "tab active" : "tab"}
                href={hrefFor(page, vistaSu(page))}
                aria-current={page === current ? "page" : undefined}
              >
                {label}
              </a>
            ))}
          </nav>
          {viste.length > 1 && (
            <nav aria-label="Views" className="topbar-views">
              {viste.map((v) => (
                <a
                  key={v.view}
                  className={v.view === view ? "tab sub active" : "tab sub"}
                  href={hrefFor(current, v.view)}
                  aria-current={v.view === view ? "page" : undefined}
                >
                  {v.label}
                </a>
              ))}
            </nav>
          )}
        </div>
        <span className="tab disabled topbar-aside" aria-disabled="true" title="Coming soon">
          Activities
        </span>
      </div>
    </header>
  );
}
