// "Training" (todo 34): le attivita' del giorno. Con piu' attivita' una riga
// di linguette (icona e ora) sceglie quella da mostrare. La scheda: titolo,
// metriche, la barra dei minuti per effetto, a destra il commento (la sezione
// Training del report) e i due Training Effect; sotto il grafico a tre fasce
// e, a richiesta, la mappa. Giorno senza attivita': "Rest day".
import { useEffect, useState } from "react";

import { api, iconUrl, type Activity, type ActivityDetail, type DailyData } from "../api/client";
import { durationLabel, effectMinutesLabel, fixed, timeOf } from "../format";
import { markdown } from "../markdown";
import type { ColorScheme } from "../useColorScheme";
import { RouteMap } from "./RouteMap";
import { RunChart } from "./RunChart";

const TE_HELP = {
  aerobic:
    "Garmin's aerobic Training Effect for the session, from 0 to 5: how much the activity improved your aerobic fitness.",
  anaerobic:
    "Garmin's anaerobic Training Effect for the session, from 0 to 5: how much the activity improved your capacity for high-intensity efforts.",
};

const EFFECT_HELP =
  "Estimated from heart rate: low aerobic up to the top of Z3, high aerobic up to the anaerobic " +
  "threshold, anaerobic above it. Garmin computes its own Training Effect, and the file only keeps the session totals.";

type Sport = { label: (sport: string | null | undefined) => string; icon: (sport: string | null | undefined) => string | null };

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

/** "after 2 rest days" o "3rd training day in a row": dai conteggi dell'API,
 * che contano i giorni prima di quello scelto. */
function context(data: DailyData | null): string | null {
  if (!data) return null;
  const rest = data.recent.consecutive_rest_days_before_today;
  const training = data.recent.consecutive_training_days_before_today;
  if (rest > 0) return `after ${rest} rest day${rest === 1 ? "" : "s"}`;
  if (training > 0) return `after ${training} training day${training === 1 ? "" : "s"} in a row`;
  return null;
}

function Metric({ label, value, sub, help }: { label: string; value: string; sub?: string; help: string }) {
  return (
    <div className="stat" title={help}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function EffectsBar({ detail }: { detail: ActivityDetail }) {
  const s = detail.effect_seconds;
  if (!s) return null;
  const total = s.low_aerobic_s + s.high_aerobic_s + s.anaerobic_s;
  if (total <= 0) return null;
  const parts = [
    { tone: "low", label: "low aerobic", seconds: s.low_aerobic_s },
    { tone: "high", label: "high aerobic", seconds: s.high_aerobic_s },
    { tone: "anaerobic", label: "anaerobic", seconds: s.anaerobic_s },
  ];
  return (
    <div className="effects" title={EFFECT_HELP}>
      <div className="stat-label">
        Where the {durationLabel(detail.total_time_min)} went, estimated from heart rate
      </div>
      <div className="effects-bar" aria-hidden="true">
        {parts.map(
          (p) => p.seconds > 0 && <div key={p.tone} className={`fill ${p.tone}`} style={{ flexGrow: p.seconds }} />,
        )}
      </div>
      <ul className="effects-legend">
        {parts.map((p) => (
          <li key={p.tone}>
            <span className={`swatch ${p.tone}`} />
            <strong>{effectMinutesLabel(p.seconds)}</strong> {p.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TrainingEffect({ label, value, help, tone }: { label: string; value: number | null; help: string; tone: string }) {
  if (value == null) return null;
  return (
    <div className="te" title={help}>
      <div className="te-row">
        <span>{label}</span>
        <strong>{value.toFixed(1)}</strong>
      </div>
      <div className="te-bar" aria-hidden="true">
        <div className={`fill ${tone}`} style={{ width: `${(value / 5) * 100}%` }} />
      </div>
    </div>
  );
}

function ActivityView({
  activity,
  data,
  first,
  comment,
  sport,
  theme,
}: {
  activity: Activity;
  data: DailyData | null;
  first: boolean;
  comment: string | null;
  sport: Sport;
  theme: ColorScheme;
}) {
  const id = activity.activity_id;
  const [detail, setDetail] = useState<ActivityDetail | null>(null);
  const [points, setPoints] = useState<[number, number][]>([]);
  const [showMap, setShowMap] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setDetail(null);
    setPoints([]);
    setShowMap(false);
    api.activity(id, controller.signal).then(setDetail).catch((e: unknown) => !isAbort(e) && console.error(e));
    api
      .route(id, controller.signal)
      .then((r) => setPoints(r.points))
      .catch((e: unknown) => !isAbort(e) && console.error(e));
    return () => controller.abort();
  }, [id]);

  const icon = sport.icon(activity.sport);
  const after = first ? context(data) : null;
  const a = detail ?? activity;
  return (
    <>
      <div className="training-grid">
        <div>
          <div className="training-head">
            {icon && <img src={iconUrl(icon)} alt="" width={44} height={44} />}
            <div>
              <h2>{activity.activity_name ?? sport.label(activity.sport)}</h2>
              <div className="muted">
                {sport.label(activity.sport)} · started {timeOf(activity.start_time)}
                {after && ` · ${after}`}
              </div>
            </div>
          </div>
          <div className="stats five">
            <Metric
              label="Distance"
              value={fixed(a.total_distance_km, 1, " km")}
              help="Total distance recorded by the watch, in km."
            />
            <Metric
              label="Duration"
              value={durationLabel(a.total_time_min)}
              help="Elapsed time from start to finish, pauses and stops included."
            />
            <Metric
              label="Elevation"
              value={a.total_ascent_m != null ? `+${a.total_ascent_m.toFixed(0)} / -${fixed(a.total_descent_m, 0)} m` : "-"}
              help="Total ascent and descent recorded by the watch, in metres."
            />
            <Metric
              label="Average speed"
              value={fixed(a.avg_speed_kmh, 1, " km/h")}
              help="Average speed, over moving time (the duration is elapsed time, stops included)."
            />
            <Metric
              label="Average heart rate"
              value={fixed(a.avg_heart_rate, 0, " bpm")}
              sub={a.max_heart_rate != null ? `Max ${a.max_heart_rate}` : undefined}
              help="Average and maximum heart rate over the activity, in beats per minute."
            />
          </div>
          {detail && <EffectsBar detail={detail} />}
        </div>
        <aside className="training-side">
          {comment && <div className="prose">{markdown(comment)}</div>}
          {(a.aerobic_te != null || a.anaerobic_te != null) && (
            <div className="te-box">
              <div className="stat-label">Garmin Training Effect, 0 to 5</div>
              <TrainingEffect label="Aerobic" value={a.aerobic_te} help={TE_HELP.aerobic} tone="high" />
              <TrainingEffect label="Anaerobic" value={a.anaerobic_te} help={TE_HELP.anaerobic} tone="anaerobic" />
            </div>
          )}
          {points.length > 0 && (
            <button type="button" className="link-btn" onClick={() => setShowMap((v) => !v)} aria-expanded={showMap}>
              {showMap ? "Hide the route map" : "Open the route map"}
            </button>
          )}
        </aside>
      </div>
      <RunChart activityId={id} theme={theme} />
      {showMap && points.length > 0 && <RouteMap activityId={id} points={points} />}
    </>
  );
}

export function TrainingCard({
  activities,
  data,
  comment,
  icon,
  restIcon,
  sport,
  theme,
}: {
  activities: Activity[];
  data: DailyData | null;
  comment: string | null;
  icon: string | null;
  restIcon: string | null;
  sport: Sport;
  theme: ColorScheme;
}) {
  const [selectedId, setSelectedId] = useState<number | null>(activities[0]?.activity_id ?? null);
  useEffect(() => setSelectedId(activities[0]?.activity_id ?? null), [activities]);
  const selected = activities.find((a) => a.activity_id === selectedId) ?? activities[0] ?? null;

  return (
    <section className="card training-card" aria-label="Training">
      <div className="block-head">
        {icon && <img src={iconUrl(icon)} alt="" width={22} height={22} />}
        <span>Training</span>
      </div>
      {activities.length > 1 && (
        <div className="tabs" role="tablist" aria-label="Activities of the day">
          {activities.map((a) => {
            const sportIcon = sport.icon(a.sport);
            return (
              <button
                type="button"
                role="tab"
                key={a.activity_id}
                aria-selected={a.activity_id === selected?.activity_id}
                className={a.activity_id === selected?.activity_id ? "tab-btn active" : "tab-btn"}
                onClick={() => setSelectedId(a.activity_id)}
              >
                {sportIcon && <img src={iconUrl(sportIcon)} alt="" width={20} height={20} />}
                {sport.label(a.sport)} · {timeOf(a.start_time)}
              </button>
            );
          })}
        </div>
      )}
      {selected ? (
        <ActivityView
          key={selected.activity_id}
          activity={selected}
          data={data}
          first={selected.activity_id === activities[0].activity_id}
          comment={comment}
          sport={sport}
          theme={theme}
        />
      ) : (
        <div className="rest-day">
          <div className="training-head">
            {restIcon && <img src={iconUrl(restIcon)} alt="" width={44} height={44} />}
            <h2>Rest day</h2>
          </div>
          {comment && <div className="prose">{markdown(comment)}</div>}
        </div>
      )}
    </section>
  );
}
