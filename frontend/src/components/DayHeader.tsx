// L'intestazione del giorno (todo 34): la data, le frecce, "Today", la
// scelta della data e il tasto Refresh (todo 41). A destra, passata da
// `DayPage`, la striscia della settimana.
import { useEffect, useState, type ReactNode } from "react";

import { addDays, longDayLabel } from "../format";

/** Il tempo da `started` (ora locale dell'API, sulla stessa macchina), "m:ss". */
function elapsed(started: string, now: number): string {
  const seconds = Math.max(0, Math.floor((now - new Date(started).getTime()) / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/** Il tasto Refresh: mentre il lavoro gira dice da quanto, e non si clicca. */
function RefreshButton({ running, onRefresh }: { running: string | null; onRefresh: () => void }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [running]);
  return (
    <button
      type="button"
      className="btn refresh-btn"
      onClick={onRefresh}
      disabled={running !== null}
      aria-busy={running !== null}
      title="Download new data from Garmin and rewrite this day's report (a few minutes)"
    >
      <svg aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">
        <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M12.5 1.5v3h-3" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {running ? `Refreshing… ${elapsed(running, now)}` : "Refresh"}
    </button>
  );
}

export function DayHeader({
  day,
  maxDay,
  onChange,
  refreshing,
  onRefresh,
  children,
}: {
  day: string;
  maxDay: string;
  onChange: (day: string) => void;
  // L'ora di inizio del lavoro di Refresh in corso, `null` se non ce n'e'.
  refreshing: string | null;
  onRefresh: () => void;
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
          <RefreshButton running={refreshing} onRefresh={onRefresh} />
        </div>
      </div>
      {children}
    </section>
  );
}
