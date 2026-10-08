// La pagina Day (todo 33), come `app_pages/activities.py` della Streamlit:
// filtri, tabella dei giorni con la scheda sotto e il report accanto, poi
// grafico e mappa a tutta larghezza.
//
// Una differenza voluta: si apre sugli ultimi 28 giorni (il default di
// `/api/activities`) e non su tutto lo storico, che sono quasi mille righe
// da scaricare a ogni apertura.
import { useEffect, useMemo, useState } from "react";

import { api, type Activity, type ActivityDetail, type Report, type SportList } from "../api/client";
import { addDays, today } from "../format";
import { useColorScheme } from "../useColorScheme";
import { ActivityCard } from "./ActivityCard";
import { DailyReport } from "./DailyReport";
import { buildRows, DayTable } from "./DayTable";
import { Filters } from "./Filters";
import { RouteMap } from "./RouteMap";
import { RunChart } from "./RunChart";

const DEFAULT_WINDOW_DAYS = 27;

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function DayPage() {
  const theme = useColorScheme();
  const now = today();
  const [start, setStart] = useState(() => addDays(now, -DEFAULT_WINDOW_DAYS));
  const [end, setEnd] = useState(now);
  const [sports, setSports] = useState<string[]>([]);
  const [sportList, setSportList] = useState<SportList | null>(null);
  const [activities, setActivities] = useState<Activity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [detail, setDetail] = useState<ActivityDetail | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const invalidRange = start > end;
  const apiDown = "Cannot reach the API. Is it running (make api)?";

  useEffect(() => {
    const controller = new AbortController();
    api
      .sports(controller.signal)
      .then(setSportList)
      .catch((e: unknown) => !isAbort(e) && setError(apiDown));
    return () => controller.abort();
  }, []);

  // A ogni cambio di filtro si ricaricano le attivita' e si sceglie la prima
  // riga con un'attivita', non la prima riga: spesso e' un giorno vuoto, come
  // oggi prima di allenarsi.
  useEffect(() => {
    if (invalidRange) return;
    const controller = new AbortController();
    setActivities(null);
    api
      .activities(start, end, sports, controller.signal)
      .then((list) => {
        setError(null);
        setActivities(list);
        const first = buildRows(list, start, end).find((r) => r.activity);
        setSelectedKey(first ? first.key : null);
      })
      .catch((e: unknown) => !isAbort(e) && setError(apiDown));
    return () => controller.abort();
  }, [start, end, sports, invalidRange]);

  const rows = useMemo(() => (activities ? buildRows(activities, start, end) : []), [activities, start, end]);
  const selected = rows.find((r) => r.key === selectedKey) ?? null;
  const selectedId = selected?.activity?.activity_id ?? null;
  const selectedDay = selected?.day ?? null;

  useEffect(() => {
    setDetail(null);
    if (selectedId == null) return;
    const controller = new AbortController();
    api
      .activity(selectedId, controller.signal)
      .then(setDetail)
      .catch((e: unknown) => !isAbort(e) && setError(apiDown));
    return () => controller.abort();
  }, [selectedId]);

  // Il report c'e' anche per un giorno senza attivita': il riposo e' proprio
  // il giorno in cui serve.
  useEffect(() => {
    setReport(null);
    if (selectedDay == null) return;
    const controller = new AbortController();
    setReportLoading(true);
    api
      .dailyReport(selectedDay, controller.signal)
      .then((r) => {
        setReport(r);
        setReportLoading(false);
      })
      .catch((e: unknown) => {
        if (!isAbort(e)) {
          setError(apiDown);
          setReportLoading(false);
        }
      });
    return () => controller.abort();
  }, [selectedDay]);

  const sportIcons = useMemo(
    () => new Map((sportList?.sports ?? []).map((s) => [s.sport, s.icon ?? null])),
    [sportList],
  );
  const sportLabel = (sport: string | null | undefined) =>
    sportList?.sports.find((s) => s.sport === sport)?.label ?? sport ?? "?";

  return (
    <main className="page">
      <h1>Day</h1>
      <Filters
        sports={sportList?.sports ?? []}
        selectedSports={sports}
        onSportsChange={setSports}
        start={start}
        end={end}
        maxDay={now}
        onStartChange={setStart}
        onEndChange={setEnd}
      />
      {error && <p className="warning">{error}</p>}
      {invalidRange ? (
        <p className="warning">'From' is later than 'To': swap the two dates to see the activities.</p>
      ) : (
        <>
          <p className="caption">Click a row to see the details.</p>
          <div className="day-grid">
            <div className="day-left">
              {activities == null && !error ? (
                <p className="caption">Loading…</p>
              ) : (
                <DayTable
                  rows={rows}
                  selectedKey={selectedKey}
                  onSelect={setSelectedKey}
                  sportIcons={sportIcons}
                  restIcon={sportList?.rest_icon ?? null}
                  showRest={(day) => sports.length === 0 && day !== now}
                />
              )}
              {activities != null && selected == null && (
                <p className="info">
                  {rows.some((r) => r.activity)
                    ? "Select an activity from the table to see its details."
                    : "No activity in the selected period."}
                </p>
              )}
              {selected && !selected.activity && <p className="info">No activity on this day.</p>}
              {detail && detail.activity_id === selectedId && (
                <ActivityCard
                  activity={detail}
                  sportLabel={sportLabel(detail.sport)}
                  sportIcon={sportIcons.get(detail.sport ?? "") ?? null}
                />
              )}
            </div>
            {selected && (
              <aside className="day-right" aria-label="Daily report">
                <div className="report-box">
                  <DailyReport report={report} loading={reportLoading} />
                </div>
              </aside>
            )}
          </div>
          {selectedId != null && (
            <>
              <RunChart activityId={selectedId} theme={theme} />
              <RouteMap activityId={selectedId} />
            </>
          )}
        </>
      )}
    </main>
  );
}
