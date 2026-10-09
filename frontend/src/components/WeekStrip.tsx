// La striscia della settimana (todo 34): otto giorni, ognuno con le icone
// delle attivita' e i km (o i minuti, per chi non ha distanza), il riposo
// con la sua icona. Il giorno scelto e' in un riquadro, oggi tratteggiato.
import { useEffect, useRef } from "react";

import { iconUrl, type Activity } from "../api/client";
import { dayNumber, dayOf, daysBetween, durationLabel, weekdayShort } from "../format";

/** "8.1 + 3.5 km": l'unita' una volta sola se sono tutte distanze;
 * altrimenti ognuna con la sua ("8.1 km + 1h10"). */
function amount(activities: Activity[]): string {
  if (activities.every((a) => a.total_distance_km)) {
    return `${activities.map((a) => a.total_distance_km!.toFixed(1)).join(" + ")} km`;
  }
  return activities
    .map((a) => (a.total_distance_km ? `${a.total_distance_km.toFixed(1)} km` : durationLabel(a.total_time_min)))
    .join(" + ");
}

export function WeekStrip({
  start,
  end,
  selected,
  today,
  activities,
  sportIcons,
  restIcon,
  onSelect,
}: {
  start: string;
  end: string;
  selected: string;
  today: string;
  activities: Activity[];
  sportIcons: Map<string, string | null>;
  restIcon: string | null;
  onSelect: (day: string) => void;
}) {
  const days = daysBetween(start, end).reverse();
  const strip = useRef<HTMLElement>(null);
  // Sul telefono la striscia scorre: il giorno scelto si porta in vista,
  // muovendo solo la striscia e non la pagina.
  useEffect(() => {
    const box = strip.current;
    const chosen = box?.querySelector<HTMLElement>(".strip-day.selected");
    if (!box || !chosen) return;
    const left = chosen.offsetLeft - box.offsetLeft;
    if (left < box.scrollLeft || left + chosen.offsetWidth > box.scrollLeft + box.clientWidth) {
      box.scrollLeft = left + chosen.offsetWidth - box.clientWidth;
    }
  }, [selected, start, end]);
  return (
    <nav className="week-strip" aria-label="Days" ref={strip}>
      {days.map((day) => {
        const done = activities
          .filter((a) => dayOf(a.start_time) === day)
          .sort((a, b) => a.start_time.localeCompare(b.start_time));
        const isToday = day === today;
        const classes = ["strip-day", day === selected ? "selected" : "", isToday ? "today" : ""].join(" ");
        return (
          <button
            type="button"
            key={day}
            className={classes}
            onClick={() => onSelect(day)}
            aria-current={day === selected ? "date" : undefined}
          >
            <span className="strip-weekday">{weekdayShort(day)}</span>
            <span className="strip-number">{dayNumber(day)}</span>
            <span className="strip-icons">
              {done.length > 0
                ? done.map((a) => {
                    const icon = sportIcons.get(a.sport ?? "");
                    return icon ? <img key={a.activity_id} src={iconUrl(icon)} alt={a.sport ?? ""} /> : null;
                  })
                : !isToday && restIcon && <img src={iconUrl(restIcon)} alt="rest" />}
            </span>
            <span className="strip-amount">{done.length > 0 ? amount(done) : isToday ? "today" : "rest"}</span>
          </button>
        );
      })}
    </nav>
  );
}
