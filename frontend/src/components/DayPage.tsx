// La pagina Day (todo 34), sul mockup `todo/assets/34_day_mockup.jpeg`: un
// giorno alla volta. Intestazione con la striscia della settimana, il
// riquadro "Next", i segnali d'allarme, la griglia 2x2 (todo 37): Health e
// Load sopra, Recovery e Fitness sotto, poi "Training" con grafico e mappa.
// I numeri vengono da `/api/daily/{day}` e `/api/activities`, i testi dalle
// sezioni del report giornaliero. Il tasto Refresh (todo 41) aggiorna i dati e
// riscrive il report: alla fine la pagina li richiede.
//
// Il giorno sta nell'URL (`?day=2026-10-07`): un giorno si apre da un link e
// il tasto indietro torna a quello prima. Senza router: `URLSearchParams` e
// `history.pushState`.
//
// Dal todo 55 la pagina ha due viste, che il menu sceglie con `?view=`: il
// Report (le card) e il Trend (i grafici della finestra scelta col cursore).
// L'intestazione e la scelta del giorno sono le stesse, che il giorno serve
// a tutte e due.
import { useCallback, useEffect, useMemo, useState } from "react";

import { api, isAbort, type Activity, type DailyData, type RefreshStatus, type Report, type SportList } from "../api/client";
import { addDays, dayOf, today } from "../format";
import { preamble, sectionBody, sectionIcon, sectionWrittenAt } from "../markdown";
import { daysFromUrl, type View } from "../navigation";
import { useColorScheme } from "../useColorScheme";
import { DayHeader } from "./DayHeader";
import { FitnessCard } from "./FitnessCard";
import { HealthCard } from "./HealthCard";
import { LoadCard } from "./LoadCard";
import { NextCard } from "./NextCard";
import { RecoveryCard } from "./RecoveryCard";
import { SectionRefresh } from "./SectionRefresh";
import { SummaryCard } from "./SummaryCard";
import { TopBar } from "./TopBar";
import { TrainingCard } from "./TrainingCard";
import { TrendPanels } from "./TrendPanels";
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

const API_DOWN = "Cannot reach the API. Is it running (make api)?";

// Ogni quanto si chiede lo stato del Refresh mentre gira.
const REFRESH_POLL_MS = 3000;

export function DayPage({ view = "report" }: { view?: View }) {
  const theme = useColorScheme();
  const now = today();
  const [day, setDay] = useState(() => dayFromUrl(now));
  const [days, setDays] = useState(() => daysFromUrl());
  const [sportList, setSportList] = useState<SportList | null>(null);
  const [stripActivities, setStripActivities] = useState<Activity[]>([]);
  const [data, setData] = useState<DailyData | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState<RefreshStatus | null>(null);
  // Sale a ogni Refresh finito bene: dati e report si richiedono.
  const [reloads, setReloads] = useState(0);
  // Un errore del Refresh si mostra solo se questa pagina l'ha visto girare,
  // non per un lavoro fallito ore prima.
  const [watched, setWatched] = useState(false);
  const [stripStart, stripEnd] = stripRange(day, now);

  // Il tasto di una card: rifa' solo quella sezione, le altre tengono il
  // testo che hanno. Lo stato arriva dallo stesso `GET /api/refresh`.
  const refreshSection = (section: string) => {
    api
      .startSectionRefresh(day, section)
      .then((status) => {
        setWatched(true);
        setRefresh(status);
      })
      .catch(() => setError(API_DOWN));
  };

  const sectionButton = (key: string) => (
    <SectionRefresh section={key} state={refresh?.sections?.[key]} onRefresh={refreshSection} />
  );

  const startRefresh = () => {
    api
      .startRefresh(day)
      .then((status) => {
        setWatched(true);
        setRefresh(status);
      })
      .catch(() => setError(API_DOWN));
  };

  const changeDay = (next: string) => {
    if (next === day || next > now) return;
    const url = new URL(window.location.href);
    url.searchParams.set("day", next);
    window.history.pushState({ day: next }, "", url);
    setDay(next);
  };

  // L'ampiezza del Trend va nell'URL, cosi' un link se la porta dietro, ma
  // **senza lasciare una voce nella cronologia**: il cursore ne
  // attraverserebbe decine, e il tasto indietro non tornerebbe piu' al
  // giorno di prima.
  const changeDays = useCallback((next: number) => {
    const url = new URL(window.location.href);
    url.searchParams.set("days", String(next));
    window.history.replaceState(window.history.state, "", url);
    setDays(next);
  }, []);

  useEffect(() => {
    const onPop = () => {
      setDay(dayFromUrl(today()));
      setDays(daysFromUrl());
    };
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
      .refresh(controller.signal)
      .then((status) => {
        if (status.status === "running") setWatched(true);
        setRefresh(status);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  const running = refresh?.status === "running";
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      api
        .refresh()
        .then((status) => {
          setRefresh(status);
          if (status.status === "done") setReloads((n) => n + 1);
        })
        .catch(() => undefined);
    }, REFRESH_POLL_MS);
    return () => window.clearInterval(timer);
  }, [running]);

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
  }, [stripStart, stripEnd, reloads]);

  useEffect(() => {
    if (view !== "report") return;
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
  }, [day, reloads, view]);

  useEffect(() => {
    document.title = view === "trend" ? `Training · ${day} · Trend` : `Training · ${day}`;
  }, [day, view]);

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
      <TopBar view={view} />
      <main className="page">
        <DayHeader
          day={day}
          maxDay={now}
          onChange={changeDay}
          refreshing={running ? (refresh?.started ?? null) : null}
          onRefresh={startRefresh}
        >
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
        {watched && refresh?.status === "failed" && (
          <p className="warning multiline">
            Refresh of {refresh.day} failed: {refresh.message}
          </p>
        )}
        {/* Lo scaricamento che fallisce non ferma il lavoro: il testo si
            scrive sui dati che ci sono gia'. Ma va detto, perche' da quando
            a lanciare sono i timer non c'e' nessuno a guardare (todo 47). */}
        {watched && refresh?.download && !refresh.download.ok && (
          <p className="warning multiline">
            Garmin was not reached: the text of {refresh.day} was written on the data already here.
            {refresh.download.message && ` ${refresh.download.message}`}
          </p>
        )}
        {view === "trend" ? (
          <TrendPanels day={day} days={days} onDays={changeDays} theme={theme} />
        ) : (
        <>
        <div className="head-row">
          <NextCard
            body={sectionBody(report, "Next")}
            writtenAt={sectionWrittenAt(report, "Next")}
            day={day}
            tomorrow={data?.recent.trained_today ?? true}
            refresh={sectionButton("next")}
          />
          <SummaryCard
            day={day}
            morning={{
              body: sectionBody(report, "Morning summary"),
              writtenAt: sectionWrittenAt(report, "Morning summary"),
              refresh: sectionButton("summary_morning"),
            }}
            evening={{
              body: sectionBody(report, "Evening summary"),
              writtenAt: sectionWrittenAt(report, "Evening summary"),
              refresh: sectionButton("summary_evening"),
            }}
          />
        </div>
        {data ? (
          <>
            <div className="cards-grid">
              <HealthCard
                data={data}
                text={sectionBody(report, "Health")}
                writtenAt={sectionWrittenAt(report, "Health")}
                day={day}
                icon={sectionIcon(report, "Health")}
                refresh={sectionButton("health")}
              />
              <LoadCard
                data={data}
                text={sectionBody(report, "Load")}
                writtenAt={sectionWrittenAt(report, "Load")}
                day={day}
                icon={sectionIcon(report, "Load")}
                refresh={sectionButton("load")}
              />
              <RecoveryCard
                data={data}
                text={sectionBody(report, "Recovery")}
                writtenAt={sectionWrittenAt(report, "Recovery")}
                day={day}
                icon={sectionIcon(report, "Recovery")}
                refresh={sectionButton("recovery")}
              />
              <FitnessCard
                data={data}
                text={sectionBody(report, "Fitness")}
                writtenAt={sectionWrittenAt(report, "Fitness")}
                day={day}
                icon={sectionIcon(report, "Fitness")}
                refresh={sectionButton("fitness")}
              />
            </div>
          </>
        ) : (
          !error && <p className="caption">Loading…</p>
        )}
        <TrainingCard
          activities={dayActivities}
          data={data}
          comment={sectionBody(report, "Training")}
          commentWrittenAt={sectionWrittenAt(report, "Training")}
          day={day}
          icon={sectionIcon(report, "Training")}
          restIcon={sportList?.rest_icon ?? null}
          sport={sport}
          theme={theme}
          refresh={sectionButton("training")}
        />
        {dataNote && <p className="caption">{dataNote}</p>}
        </>
        )}
      </main>
    </>
  );
}
