// Il selettore di settimane della pagina Week (todo 53): sei bottoni, uno
// per settimana, ognuno con il numero ISO e le date del lunedi' e della
// domenica.
//
// Non e' `WeekStrip` con una bandierina: quella mostra giorni, questa
// settimane, e mescolarle complicherebbe tutte e due. La Day tiene la sua.
import { useEffect, useRef } from "react";

import { addDays, isoWeek, shortDayLabel } from "../format";

// Sei settimane: un mese e mezzo, che si guarda tutto in un colpo senza
// che la striscia diventi un muro di riquadri. Per una settimana vecchia
// la striscia finisce due settimane dopo di lei, cosi' si vede anche cosa
// e' venuto dopo.
const WEEKS = 6;
const AFTER = 2;

/** Le otto settimane da mostrare, dalla piu' vecchia, quando si guarda
 * `monday` e la settimana corrente e' `current`. */
export function weeksAround(monday: string, current: string): string[] {
  const oldest = addDays(current, -7 * (WEEKS - 1));
  const end = monday >= oldest ? current : minWeek(addDays(monday, 7 * AFTER), current);
  const weeks: string[] = [];
  for (let k = WEEKS - 1; k >= 0; k -= 1) weeks.push(addDays(end, -7 * k));
  return weeks;
}

const minWeek = (a: string, b: string) => (a < b ? a : b);

export function WeekPicker({
  monday,
  current,
  onSelect,
}: {
  monday: string;
  current: string;
  onSelect: (monday: string) => void;
}) {
  const strip = useRef<HTMLElement>(null);
  // Sul telefono la striscia scorre: la settimana scelta si porta in vista,
  // muovendo solo la striscia e non la pagina.
  useEffect(() => {
    const chosen = strip.current?.querySelector<HTMLElement>(".strip-week.selected");
    if (chosen) strip.current?.scrollTo({ left: chosen.offsetLeft - 8 });
  }, [monday, current]);

  return (
    <nav className="week-strip" aria-label="Weeks" ref={strip}>
      {weeksAround(monday, current).map((week) => {
        const chosen = week === monday;
        const classes = ["strip-week", chosen ? "selected" : "", week === current ? "today" : ""]
          .filter(Boolean)
          .join(" ");
        return (
          <button
            type="button"
            key={week}
            className={classes}
            onClick={() => onSelect(week)}
            aria-current={chosen ? "page" : undefined}
          >
            <span className="strip-number">W{String(isoWeek(week)).padStart(2, "0")}</span>
            <span className="strip-dates">
              {shortDayLabel(week)}
              <br />
              {shortDayLabel(addDays(week, 6))}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
