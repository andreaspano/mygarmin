// La barra in alto (todo 34), su due righe dal todo 55.
//
// Prima riga il **periodo** (Day, Week), seconda riga **cosa se ne guarda**:
// due assi veri, mentre prima Day, Week e Activities stavano in fila come se
// fossero la stessa cosa. Activities non e' un periodo e sta a destra,
// staccata, ancora disattivata.
//
// Le viste sono di ogni periodo e stanno in `VIEWS` (todo 59): Report e
// Trend sotto Day, Snap, Trend e Plan sotto Week. Qui ci sono solo i nomi
// con cui si scrivono, che la barra e' il posto dove si leggono.
//
// A destra sta anche **Plan**, per lo stesso motivo di Activities: un piano
// non e' un periodo. Non guarda indietro a un giorno o a una settimana,
// guarda avanti a una gara, e dura quanto dura il blocco. Di viste non ne
// ha, quindi apre la barra con una riga sola.
//
// Niente voci grigie nei due menu: Month e Year si aggiungono quando
// esistono, non prima. Resta disattivata solo Activities, che la forma della
// barra ce l'ha gia'.
import { VIEWS, defaultView, hrefFor, type Page, type View } from "../navigation";

const PERIODI: { page: Page; label: string }[] = [
  { page: "day", label: "Day" },
  { page: "week", label: "Week" },
];
const ETICHETTE: Record<View, string> = {
  report: "Report",
  snap: "Snap",
  trend: "Trend",
  plan: "Plan",
};

export function TopBar({
  current = "day",
  view = "report",
}: {
  current?: Page;
  view?: View;
}) {
  const viste = VIEWS[current];
  // La vista si porta dietro solo dove esiste: andando sulla Day, che lo
  // Snap non ce l'ha, il collegamento torna alla prima vista di quel
  // periodo invece di lasciare nell'URL una vista che quella pagina ignora.
  const vistaSu = (page: Page): View =>
    VIEWS[page].includes(view) ? view : defaultView(page);
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
                  key={v}
                  className={v === view ? "tab sub active" : "tab sub"}
                  href={hrefFor(current, v)}
                  aria-current={v === view ? "page" : undefined}
                >
                  {ETICHETTE[v]}
                </a>
              ))}
            </nav>
          )}
        </div>
        <nav aria-label="Other pages" className="topbar-aside">
          <a
            className={current === "plan" ? "tab active" : "tab"}
            href={hrefFor("plan")}
            aria-current={current === "plan" ? "page" : undefined}
          >
            Plan
          </a>
          <span className="tab disabled" aria-disabled="true" title="Coming soon">
            Activities
          </span>
        </nav>
      </div>
    </header>
  );
}
