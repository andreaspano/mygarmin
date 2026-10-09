// L'intestazione del giorno (todo 34): la data, le frecce, "Today" e la
// scelta della data. A destra, passata da `DayPage`, la striscia della
// settimana.
import type { ReactNode } from "react";

import { addDays, longDayLabel } from "../format";

export function DayHeader({
  day,
  maxDay,
  onChange,
  children,
}: {
  day: string;
  maxDay: string;
  onChange: (day: string) => void;
  children?: ReactNode;
}) {
  return (
    <section className="day-header">
      <div className="day-title">
        <h1>{longDayLabel(day)}</h1>
        <div className="day-nav">
          <button type="button" className="btn icon-btn" onClick={() => onChange(addDays(day, -1))} aria-label="Previous day">
            ‹
          </button>
          <button
            type="button"
            className="btn icon-btn"
            onClick={() => onChange(addDays(day, 1))}
            disabled={day >= maxDay}
            aria-label="Next day"
          >
            ›
          </button>
          <button type="button" className="btn" onClick={() => onChange(maxDay)} disabled={day === maxDay}>
            Today
          </button>
          <label className="btn date-pick">
            <svg aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">
              <rect x="1.5" y="3" width="13" height="11.5" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <path d="M1.5 7h13M5 1.5v3M11 1.5v3" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            Pick a date
            <input
              type="date"
              value={day}
              max={maxDay}
              onChange={(e) => e.target.value && e.target.value <= maxDay && onChange(e.target.value)}
              aria-label="Pick a date"
            />
          </label>
        </div>
      </div>
      {children}
    </section>
  );
}
