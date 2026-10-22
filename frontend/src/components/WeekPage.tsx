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

import { api, iconUrl, isAbort, type Activity, type SportList } from "../api/client";
import { addDays, durationLabel, fixed, mondayOf, timeOf, today, weekLabel, weekRangeLabel } from "../format";
import { paramFromUrl, pushUrl } from "../navigation";
import { TopBar } from "./TopBar";
import { WeekStrip } from "./WeekStrip";

const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const API_DOWN = "Cannot reach the API. Is it running (make api)?";

/** Il lunedi dell'URL, se e' una data valida e non nel futuro; se no quello
 * della settimana di oggi. Un giorno qualunque viene riportato al suo
 * lunedi, cosi' un link storto apre comunque la settimana giusta. */
function mondayFromUrl(now: string): string {
  const value = paramFromUrl("monday");
  const current = mondayOf(now);
  if (!value || !DAY_PATTERN.test(value) || Number.isNaN(Date.parse(value))) return current;
  const monday = mondayOf(value);
  return monday > current ? current : monday;
}

export function WeekPage() {
  const now = today();
  const currentMonday = mondayOf(now);
  const [monday, setMonday] = useState(() => mondayFromUrl(now));
  const [sportList, setSportList] = useState<SportList | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
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

  const sportIcons = useMemo(
    () => new Map((sportList?.sports ?? []).map((s) => [s.sport, s.icon ?? null])),
    [sportList],
  );
  const sportLabel = (key: string | null | undefined) =>
    sportList?.sports.find((s) => s.sport === key)?.label ?? key ?? "?";

  // Dalla piu' vecchia alla piu' recente: una settimana si legge in avanti.
  const ordered = useMemo(
    () => [...activities].sort((a, b) => a.start_time.localeCompare(b.start_time)),
    [activities],
  );
  const totalMin = ordered.reduce((sum, a) => sum + (a.total_time_min ?? 0), 0);
  const restDays = 7 - new Set(ordered.map((a) => a.start_time.slice(0, 10))).size;

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
            <p className="caption">
              {weekRangeLabel(monday)} · {ordered.length}
              {ordered.length === 1 ? " session" : " sessions"} · {durationLabel(totalMin)} ·{" "}
              {restDays} {restDays === 1 ? "rest day" : "rest days"}
            </p>
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
            </div>
          </div>
          <WeekStrip
            start={monday}
            end={sunday}
            selected=""
            today={now}
            activities={activities}
            sportIcons={sportIcons}
            restIcon={sportList?.rest_icon ?? null}
            onSelect={openDay}
          />
        </div>
        {error && <p className="warning">{error}</p>}
        <section className="card" aria-label="Training">
          <div className="block-head">
            <span>Training</span>
          </div>
          {ordered.length === 0 ? (
            <p className="caption">No sessions this week.</p>
          ) : (
            <ul className="week-sessions">
              {ordered.map((a) => {
                const icon = sportIcons.get(a.sport ?? "") ?? null;
                const day = a.start_time.slice(0, 10);
                return (
                  <li key={a.activity_id}>
                    <button type="button" className="week-session" onClick={() => openDay(day)}>
                      {icon && <img src={iconUrl(icon)} alt="" width={30} height={30} />}
                      <span className="week-session-name">
                        {a.activity_name ?? sportLabel(a.sport)}
                        <span className="muted">
                          {sportLabel(a.sport)} · {day} · {timeOf(a.start_time)}
                        </span>
                      </span>
                      <span className="week-session-size">
                        {a.total_distance_km != null ? fixed(a.total_distance_km, 1, " km") : "–"}
                        <span className="muted">{durationLabel(a.total_time_min)}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
