// La pagina Week (todo 51): una settimana ISO alla volta, dal lunedi alla
// domenica. Per ora e' il guscio — l'intestazione, la striscia dei sette
// giorni e le sedute — e usa solo quello che l'API gia' offre
// (`/api/activities` e `/api/sports`). I numeri della settimana con le loro
// fasce arrivano col todo 52, i testi col 53.
//
// Il lunedi sta nell'URL (`?page=week&monday=2026-10-19`), come il giorno
// nella Day: una settimana si apre da un link e il tasto indietro torna a
// quella prima.
import { useEffect, useMemo, useState } from "react";

import {
  api,
  iconUrl,
  isAbort,
  type Activity,
  type Band,
  type SportList,
  type WeeklyData,
  type WeekMeasure,
} from "../api/client";
import {
  addDays,
  durationLabel,
  fixed,
  mondayOf,
  timeOf,
  today,
  weekLabel,
} from "../format";
import { paramFromUrl, pushUrl } from "../navigation";
import { useColorScheme } from "../useColorScheme";
import { WeekCalendar } from "./WeekCalendar";
import { CardHead, EmptyBar, RangeBar, Stat, num } from "./Stat";
import { TopBar } from "./TopBar";
import { WeekChart } from "./WeekChart";
import { WeekPicker } from "./WeekPicker";

const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const API_DOWN = "Cannot reach the API. Is it running (make api)?";

/** Il lunedi dell'URL, se e' una data valida e non nel futuro; se no quello
 * della settimana di oggi. Un giorno qualunque viene riportato al suo
 * lunedi, cosi' un link storto apre comunque la settimana giusta. */
function mondayFromUrl(now: string): string {
  const value = paramFromUrl("monday");
  const current = mondayOf(now);
  if (!value || !DAY_PATTERN.test(value) || Number.isNaN(Date.parse(value)))
    return current;
  const monday = mondayOf(value);
  return monday > current ? current : monday;
}

/** Quanti decimali vuole una misura: dall'unita', come fa la Day. */
function digitsOf(m: WeekMeasure): number {
  return m.unit === "h" || m.unit === "/min" ? 1 : 0;
}

/** Un riquadro della settimana: il numero e, sotto, la barra della fascia
 * delle dodici settimane. Gli stessi mattoni della Day (`Stat`, `RangeBar`),
 * guidati da quello che l'API manda: etichetta, unita', valore e fascia. */
function WeekStat({ m }: { m: WeekMeasure }) {
  const digits = digitsOf(m);
  const fmt = (v: number) => v.toFixed(digits);
  return (
    <Stat
      label={m.label}
      value={num(m.value, digits)}
      unit={m.unit || undefined}
      sub={
        m.band ? (
          <RangeBar value={m.value} band={m.band} tick={fmt} />
        ) : (
          <EmptyBar />
        )
      }
    />
  );
}

/** Una card di misure settimanali: Health o Recovery. */
function MeasureCard({
  title,
  icon,
  cls,
  measures,
}: {
  title: string;
  icon: string | null;
  cls?: string;
  measures: WeekMeasure[];
}) {
  return (
    <section className={cls ? `card ${cls}` : "card"} aria-label={title}>
      <CardHead icon={icon} title={title} />
      <div className="stats two">
        {measures.map((m) => (
          <WeekStat key={m.label} m={m} />
        ))}
      </div>
    </section>
  );
}

/** Le misure di una card, nell'ordine in cui l'API le manda. */
function byCard(data: WeeklyData, card: "health" | "recovery"): WeekMeasure[] {
  return Object.values(data.measures).filter((m) => m.card === card);
}

/** L'icona di una card: gli stessi file della Day, che l'API serve sotto
 * /icons. Qui non passano dal report, perche' la Week un report non ce l'ha
 * ancora (todo 53). */
const CARD_ICONS: Record<string, string> = {
  health: "health.png",
  load: "trend.png",
  recovery: "recovery.png",
  fitness: "fitness.png",
};
const sectionIconFile = (card: string) => CARD_ICONS[card] ?? null;

/** Un punteggio di forma con la sua barra: la fascia e' quella delle dodici
 * settimane, e **sopra vuol dire che stai migliorando**, come nella Day. */
function ScoreStat({
  label,
  score,
  digits = 0,
}: {
  label: string;
  score: { now: number; band?: Band | null } | null;
  digits?: number;
}) {
  return (
    <Stat
      label={label}
      value={num(score?.now, digits)}
      sub={
        score?.band ? (
          <RangeBar value={score.now} band={score.band} />
        ) : (
          <EmptyBar />
        )
      }
    />
  );
}

const LOAD_ROWS: {
  key: "load_aerobic_low" | "load_aerobic_high" | "load_anaerobic";
  label: string;
}[] = [
  { key: "load_aerobic_low", label: "Low aerobic" },
  { key: "load_aerobic_high", label: "High aerobic" },
  { key: "load_anaerobic", label: "Anaerobic" },
];

export function WeekPage() {
  const theme = useColorScheme();
  const now = today();
  const currentMonday = mondayOf(now);
  const [monday, setMonday] = useState(() => mondayFromUrl(now));
  const [sportList, setSportList] = useState<SportList | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [data, setData] = useState<WeeklyData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sunday = addDays(monday, 6);

  const changeWeek = (next: string) => {
    if (next === monday || next > currentMonday) return;
    pushUrl({ page: "week", monday: next });
    setMonday(next);
  };

  useEffect(() => {
    const onPop = () => setMonday(mondayFromUrl(today()));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    document.title = `Training · ${weekLabel(monday)}`;
  }, [monday]);

  useEffect(() => {
    const controller = new AbortController();
    api
      .sports(controller.signal)
      .then(setSportList)
      .catch((e) => !isAbort(e) && setError(API_DOWN));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    api
      .activities(monday, sunday, [], controller.signal)
      .then((list) => {
        setActivities(list);
        setError(null);
      })
      .catch((e) => !isAbort(e) && setError(API_DOWN));
    return () => controller.abort();
  }, [monday, sunday]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    api
      .weekly(monday, controller.signal)
      .then(setData)
      .catch((e) => !isAbort(e) && setError(API_DOWN));
    return () => controller.abort();
  }, [monday]);

  const sportIcons = useMemo(
    () =>
      new Map((sportList?.sports ?? []).map((s) => [s.sport, s.icon ?? null])),
    [sportList],
  );
  const sportLabel = (key: string | null | undefined) =>
    sportList?.sports.find((s) => s.sport === key)?.label ?? key ?? "?";

  // Dalla piu' vecchia alla piu' recente: una settimana si legge in avanti.
  const ordered = useMemo(
    () =>
      [...activities].sort((a, b) => a.start_time.localeCompare(b.start_time)),
    [activities],
  );
  // Un giorno della striscia, o una seduta, aprono la Day di quel giorno:
  // `pushUrl` cambia l'URL e avvisa `App`, che scambia la pagina senza
  // ricaricare niente.
  const openDay = (day: string) => pushUrl({ page: null, monday: null, day });

  return (
    <>
      <TopBar current="week" />
      <main className="page">
        <div className="day-header">
          <div className="day-title">
            <h1>{weekLabel(monday)}</h1>
            <div className="day-nav">
              <button
                type="button"
                className="btn icon-btn"
                onClick={() => changeWeek(addDays(monday, -7))}
                aria-label="Previous week"
                title="Previous week"
              >
                ‹
              </button>
              <button
                type="button"
                className="btn icon-btn"
                onClick={() => changeWeek(addDays(monday, 7))}
                disabled={monday >= currentMonday}
                aria-label="Next week"
                title="Next week"
              >
                ›
              </button>
              <button
                type="button"
                className="btn icon-btn"
                onClick={() => changeWeek(currentMonday)}
                disabled={monday === currentMonday}
                aria-label="This week"
                title="This week"
              >
                ›|
              </button>
              <WeekCalendar
                monday={monday}
                current={currentMonday}
                onSelect={changeWeek}
              />
            </div>
          </div>
          <WeekPicker
            monday={monday}
            current={currentMonday}
            onSelect={changeWeek}
          />
        </div>
        {error && <p className="warning">{error}</p>}
        {data && (
          <div className="cards-grid">
            <MeasureCard
              title="Health"
              icon={sectionIconFile("health")}
              measures={byCard(data, "health")}
            />
            <section className="card load-card" aria-label="Load">
              <CardHead icon={sectionIconFile("load")} title="Load" />
              <div className="stats two">
                {LOAD_ROWS.map(({ key, label }) => {
                  const value = data.load?.[key] ?? null;
                  const target = data.load_targets?.[key];
                  return (
                    <Stat
                      key={key}
                      label={label}
                      value={num(value)}
                      sub={
                        target ? (
                          <RangeBar
                            value={value}
                            band={{
                              low: target.min,
                              high: target.max,
                              outer_low: target.min,
                              outer_high: target.max,
                            }}
                            tick={(v) => v.toFixed(0)}
                          />
                        ) : (
                          <EmptyBar />
                        )
                      }
                    />
                  );
                })}
                <Stat label="Load ratio" value={num(data.load?.acwr, 1)} />
              </div>
            </section>
            <MeasureCard
              title="Recovery"
              icon={sectionIconFile("recovery")}
              cls="recovery-card"
              measures={byCard(data, "recovery")}
            />
            <section className="card fitness-card" aria-label="Fitness">
              <CardHead icon={sectionIconFile("fitness")} title="Fitness" />
              <div className="stats">
                <ScoreStat
                  label="VO2max"
                  score={data.fitness.vo2max}
                  digits={1}
                />
                <ScoreStat
                  label="Endurance score"
                  score={data.fitness.endurance}
                />
                <ScoreStat label="Hill score" score={data.fitness.hill} />
                <Stat
                  label={
                    data.fitness.lactate_threshold
                      ? "Lactate threshold"
                      : "Threshold heart rate"
                  }
                  value={num(
                    data.fitness.lactate_threshold?.heart_rate ??
                      data.fitness.threshold_hr?.value,
                  )}
                  unit="bpm"
                />
                <Stat
                  label="Altitude acclimation"
                  value={num(data.fitness.altitude_acclimation?.metres)}
                  unit="m"
                />
                <Stat
                  label="Heat acclimation"
                  value={num(data.fitness.heat_acclimation?.percent)}
                  unit="%"
                />
              </div>
            </section>
          </div>
        )}
        <section className="card" aria-label="Training">
          <div className="block-head">
            <span>Training</span>
          </div>
          {ordered.length === 0 ? (
            <p className="caption">No sessions this week.</p>
          ) : (
            <>
              <WeekChart monday={monday} theme={theme} />
              <ul className="week-sessions">
                {ordered.map((a) => {
                  const icon = sportIcons.get(a.sport ?? "") ?? null;
                  const day = a.start_time.slice(0, 10);
                  return (
                    <li key={a.activity_id}>
                      <button
                        type="button"
                        className="week-session"
                        onClick={() => openDay(day)}
                      >
                        {icon && (
                          <img
                            src={iconUrl(icon)}
                            alt=""
                            width={30}
                            height={30}
                          />
                        )}
                        <span className="week-session-name">
                          {a.activity_name ?? sportLabel(a.sport)}
                          <span className="muted">
                            {sportLabel(a.sport)} · {day} ·{" "}
                            {timeOf(a.start_time)}
                          </span>
                        </span>
                        <span className="week-session-size">
                          {a.total_distance_km != null
                            ? fixed(a.total_distance_km, 1, " km")
                            : "–"}
                          <span className="muted">
                            {durationLabel(a.total_time_min)}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </section>
      </main>
    </>
  );
}
