// La tabella dei giorni: una riga per attivita' e una riga vuota per ogni
// giorno senza (todo 30), dalla piu' recente. Si sceglie una riga con un
// click o con le frecce su e giu'.
import { useEffect, useRef } from "react";

import { iconUrl, type Activity } from "../api/client";
import { dayLabel, daysBetween, dayOf, fixed, timeOf } from "../format";

export type DayRow = {
  key: string;
  day: string;
  activity: Activity | null;
};

/** Le righe della tabella, con la regola di `with_empty_days`: le attivita'
 * piu' una riga vuota per ogni giorno che non ne ha, dal giorno piu' recente
 * e, nello stesso giorno, dall'ora piu' tarda. */
export function buildRows(activities: Activity[], start: string, end: string): DayRow[] {
  const byDay = new Map<string, Activity[]>();
  for (const activity of activities) {
    const day = dayOf(activity.start_time);
    byDay.set(day, [...(byDay.get(day) ?? []), activity]);
  }
  return daysBetween(start, end).flatMap((day): DayRow[] => {
    const list = byDay.get(day);
    if (!list) return [{ key: day, day, activity: null }];
    return [...list]
      .sort((a, b) => b.start_time.localeCompare(a.start_time))
      .map((activity) => ({ key: String(activity.activity_id), day, activity }));
  });
}

type Props = {
  rows: DayRow[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
  sportIcons: Map<string, string | null>;
  restIcon: string | null;
  // L'icona del riposo non va oggi (ci si puo' ancora allenare) e non con un
  // filtro per sport, dove una riga vuota vuol dire "niente di quello sport".
  showRest: (day: string) => boolean;
};

export function DayTable({ rows, selectedKey, onSelect, sportIcons, restIcon, showRest }: Props) {
  const selectedRef = useRef<HTMLTableRowElement>(null);

  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: "nearest" });
  }, [selectedKey]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const index = rows.findIndex((r) => r.key === selectedKey);
    const next = e.key === "ArrowDown" ? Math.min(rows.length - 1, index + 1) : Math.max(0, index - 1);
    if (rows[next]) onSelect(rows[next].key);
  };

  return (
    <div className="day-table" tabIndex={0} onKeyDown={onKeyDown} aria-label="Days and activities">
      <table>
        <thead>
          <tr>
            <th aria-label="Sport" />
            <th>Date</th>
            <th>Time</th>
            <th>Name</th>
            <th className="num" title="Distance.">
              km
            </th>
            <th className="num" title="Duration, in minutes.">
              Min
            </th>
            <th className="num" title="Elevation gain, in metres.">
              D+
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const a = row.activity;
            const icon = a ? sportIcons.get(a.sport ?? "") : showRest(row.day) ? restIcon : null;
            const selected = row.key === selectedKey;
            return (
              <tr
                key={row.key}
                ref={selected ? selectedRef : undefined}
                className={selected ? "selected" : undefined}
                aria-selected={selected}
                onClick={() => onSelect(row.key)}
              >
                <td className="icon">{icon && <img src={iconUrl(icon)} alt={a?.sport ?? "rest"} />}</td>
                <td>{dayLabel(row.day)}</td>
                <td>{a ? timeOf(a.start_time) : ""}</td>
                <td className="name">{a?.activity_name ?? ""}</td>
                <td className="num">{a ? fixed(a.total_distance_km, 1) : ""}</td>
                <td className="num">{a ? fixed(a.total_time_min, 0) : ""}</td>
                <td className="num">{a ? fixed(a.total_ascent_m, 0) : ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
