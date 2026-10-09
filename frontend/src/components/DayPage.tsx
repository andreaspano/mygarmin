// La pagina Day (todo 34), sul mockup `todo/assets/34_day_mockup.jpeg`: un
// giorno alla volta. Intestazione con la striscia della settimana, il
// riquadro "Next", "This morning" e "Load", poi "Training" con grafico e
// mappa. I numeri vengono da `/api/daily/{day}` e `/api/activities`, i testi
// dalle sezioni del report giornaliero.
//
// Il giorno sta nell'URL (`?day=2026-10-07`): un giorno si apre da un link e
// il tasto indietro torna a quello prima. Senza router: `URLSearchParams` e
// `history.pushState`.
import { useEffect, useMemo, useState } from "react";

import { api, type Activity, type DailyData, type Report, type SportList } from "../api/client";
import { addDays, dayOf, today } from "../format";
import { preamble, sectionBody, sectionIcon } from "../markdown";
import { useColorScheme } from "../useColorScheme";
import { DayHeader } from "./DayHeader";
import { LoadCard } from "./LoadCard";
import { MorningCard } from "./MorningCard";
import { NextCard } from "./NextCard";
import { TopBar } from "./TopBar";
import { TrainingCard } from "./TrainingCard";
import { WeekStrip } from "./WeekStrip";

// La striscia: otto giorni. Finisce oggi finche' il giorno scelto ci sta
// dentro; per un giorno piu' vecchio finisce qualche giorno dopo di lui, cosi'
// si vede anche cosa e' venuto dopo.
const STRIP_DAYS = 8;
const STRIP_AFTER = 3;

const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

/** Il giorno dell'URL, se e' una data valida e non nel futuro; se no oggi. */
function dayFromUrl(now: string): string {
  const day = new URLSearchParams(window.location.search).get("day");
  if (!day || !DAY_PATTERN.test(day) || Number.isNaN(Date.parse(day)) || day > now) return now;
  return day;
}

function stripRange(day: string, now: string): [string, string] {
  const end = day >= addDays(now, -(STRIP_DAYS - 1)) ? now : addDays(day, STRIP_AFTER);
  return [addDays(end, -(STRIP_DAYS - 1)), end];
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

const API_DOWN = "Cannot reach the API. Is it running (make api)?";

export function DayPage() {
  const theme = useColorScheme();
  const now = today();
  const [day, setDay] = useState(() => dayFromUrl(now));
  const [sportList, setSportList] = useState<SportList | null>(null);
  const [stripActivities, setStripActivities] = useState<Activity[]>([]);
  const [data, setData] = useState<DailyData | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stripStart, stripEnd] = stripRange(day, now);

  const changeDay = (next: string) => {
    if (next === day || next > now) return;
    const url = new URL(window.location.href);
    url.searchParams.set("day", next);
    window.history.pushState({ day: next }, "", url);
    setDay(next);
  };

  useEffect(() => {
    const onPop = () => setDay(dayFromUrl(today()));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    api
      .sports(controller.signal)
      .then(setSportList)
      .catch((e: unknown) => !isAbort(e) && setError(API_DOWN));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    api
      .activities(stripStart, stripEnd, [], controller.signal)
      .then((list) => {
        setError(null);
        setStripActivities(list);
      })
      .catch((e: unknown) => !isAbort(e) && setError(API_DOWN));
    return () => controller.abort();
  }, [stripStart, stripEnd]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setReport(null);
    api
      .daily(day, controller.signal)
      .then(setData)
      .catch((e: unknown) => !isAbort(e) && setError(API_DOWN));
    api
      .dailyReport(day, controller.signal)
      .then(setReport)
      .catch((e: unknown) => !isAbort(e) && setError(API_DOWN));
    return () => controller.abort();
  }, [day]);

  useEffect(() => {
    document.title = `Training · ${day}`;
  }, [day]);

  const dayActivities = useMemo(
    () =>
      stripActivities
        .filter((a) => dayOf(a.start_time) === day)
        .sort((a, b) => a.start_time.localeCompare(b.start_time)),
    [stripActivities, day],
  );

  const sportIcons = useMemo(
    () => new Map((sportList?.sports ?? []).map((s) => [s.sport, s.icon ?? null])),
    [sportList],
  );
  const sport = {
    label: (key: string | null | undefined) => sportList?.sports.find((s) => s.sport === key)?.label ?? key ?? "?",
    icon: (key: string | null | undefined) => sportIcons.get(key ?? "") ?? null,
  };
  const dataNote = preamble(report);

  return (
    <>
      <TopBar />
      <main className="page">
        <DayHeader day={day} maxDay={now} onChange={changeDay}>
          <WeekStrip
            start={stripStart}
            end={stripEnd}
            selected={day}
            today={now}
            activities={stripActivities}
            sportIcons={sportIcons}
            restIcon={sportList?.rest_icon ?? null}
            onSelect={changeDay}
          />
        </DayHeader>
        {error && <p className="warning">{error}</p>}
        <NextCard body={sectionBody(report, "Next")} tomorrow={data?.recent.trained_today ?? true} />
        {data ? (
          <div className="cards-row">
            <MorningCard
              data={data}
              recovery={sectionBody(report, "Recovery")}
              health={sectionBody(report, "Health")}
              icons={{ recovery: sectionIcon(report, "Recovery"), health: sectionIcon(report, "Health") }}
            />
            <LoadCard data={data} text={sectionBody(report, "Load")} icon={sectionIcon(report, "Load")} />
          </div>
        ) : (
          !error && <p className="caption">Loading…</p>
        )}
        <TrainingCard
          activities={dayActivities}
          data={data}
          comment={sectionBody(report, "Training")}
          icon={sectionIcon(report, "Training")}
          restIcon={sportList?.rest_icon ?? null}
          sport={sport}
          theme={theme}
        />
        {dataNote && <p className="caption">{dataNote}</p>}
      </main>
    </>
  );
}
