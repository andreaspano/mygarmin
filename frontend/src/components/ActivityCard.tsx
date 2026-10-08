// La scheda dell'attivita' scelta, come `activity_detail.show_activity_detail`:
// titolo con icona, poi righe da tre metriche. I testi di aiuto sono gli
// stessi della Streamlit e si leggono al passaggio sul "?".
import { iconUrl, type ActivityDetail } from "../api/client";
import { dateTimeLabel, fixed, hm } from "../format";

type Metric = { label: string; value: string; help: string };

const TE_HELP = {
  aerobic:
    "Garmin's aerobic Training Effect for the session, from 0 to 5: how much the activity improved your aerobic fitness.",
  anaerobic:
    "Garmin's anaerobic Training Effect for the session, from 0 to 5: how much the activity improved your capacity for high-intensity efforts.",
};

function baseRows(a: ActivityDetail): Metric[][] {
  return [
    [
      { label: "Distance", value: fixed(a.total_distance_km, 1, " km"), help: "Total distance recorded by the watch, in km." },
      {
        label: "Duration",
        value: hm(a.total_time_min),
        help: "Elapsed time from start to finish, in hh:mm, pauses and stops included.",
      },
      {
        label: "Elevation",
        value:
          a.total_ascent_m != null
            ? `+${a.total_ascent_m.toFixed(0)} / -${fixed(a.total_descent_m, 0)} m`
            : "-",
        help: "Total ascent and descent recorded by the watch, in metres. Empty when the watch stored no altitude.",
      },
    ],
    [
      {
        label: "Avg speed",
        value: fixed(a.avg_speed_kmh, 1, " km/h"),
        help: "Average speed, over moving time (the duration above is elapsed time, stops included).",
      },
      {
        label: "Avg HR",
        value: fixed(a.avg_heart_rate, 0, " bpm"),
        help: "Average heart rate over the activity, in beats per minute. Empty when no heart rate was recorded.",
      },
      {
        label: "VO2Max",
        value: fixed(a.vo2max, 1),
        help:
          "The watch's VO2max estimate at the end of the activity, in ml/kg/min. Runs update it; other " +
          "activities carry the last value. Empty when the watch stored none.",
      },
    ],
  ];
}

/** Le righe degli effetti, come `activity_detail._effect_rows`: i minuti
 * stimati sui battiti e i due Training Effect di Garmin. Quello che manca
 * non si mostra, e una riga vuota sparisce. */
function effectRows(a: ActivityDetail): Metric[][] {
  const rows: Metric[][] = [];
  const seconds = a.effect_seconds;
  if (seconds && a.hr_zone_bounds && a.threshold_hr != null) {
    const z3Top = a.hr_zone_bounds[2];
    const threshold = a.threshold_hr;
    const estimated = (name: string, value: number, range: string): Metric => ({
      label: `${name} (est.)`,
      value: hm(value / 60),
      help:
        `Time (hh:mm) with ${range}. Estimated from heart rate: Garmin computes its own Training Effect, ` +
        "and the file only keeps the session totals.",
    });
    rows.push([
      estimated("Low aerobic", seconds.low_aerobic_s, `heart rate at or below the top of Z3 (${z3Top} bpm)`),
      estimated(
        "High aerobic",
        seconds.high_aerobic_s,
        `heart rate between the top of Z3 and the anaerobic threshold (${z3Top + 1}-${threshold} bpm)`,
      ),
      estimated("Anaerobic", seconds.anaerobic_s, `heart rate above the anaerobic threshold (${threshold} bpm)`),
    ]);
  }
  const garmin: Metric[] = [];
  if (a.aerobic_te != null) garmin.push({ label: "Aerobic TE", value: a.aerobic_te.toFixed(1), help: TE_HELP.aerobic });
  if (a.anaerobic_te != null)
    garmin.push({ label: "Anaerobic TE", value: a.anaerobic_te.toFixed(1), help: TE_HELP.anaerobic });
  if (garmin.length) rows.push(garmin);
  return rows;
}

export function ActivityCard({
  activity,
  sportLabel,
  sportIcon,
}: {
  activity: ActivityDetail;
  sportLabel: string;
  sportIcon: string | null;
}) {
  const rows = [...baseRows(activity), ...effectRows(activity)];
  return (
    <section className="card" aria-label="Activity details">
      <div className="card-head">
        {sportIcon && <img src={iconUrl(sportIcon)} alt="" width={40} height={40} />}
        <span>
          <strong>{sportLabel}</strong> — {dateTimeLabel(activity.start_time)}
        </span>
      </div>
      {rows.map((row, i) => (
        <div className="metric-row" key={i}>
          {row.map((m) => (
            <div className="metric" key={m.label}>
              <div className="metric-label">
                {m.label}
                <span className="help" title={m.help} aria-label={m.help} tabIndex={0}>
                  ?
                </span>
              </div>
              <div className="metric-value">{m.value}</div>
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}
