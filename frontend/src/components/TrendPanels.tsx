// Il Trend della Day (todo 55): le misure giorno per giorno in una finestra
// che si sceglie col cursore, da 5 a 365 giorni.
//
// Un grafico **per misura** e non per pannello: dentro un pannello le unita'
// non sono le stesse (il VO2max sta a 42, il punteggio di resistenza a
// 5000), e su un asse solo la linea bassa verrebbe piatta. I pannelli sono
// nell'ordine delle card del Report: le stesse cose nello stesso ordine,
// disegnate invece che raccontate.
//
// Niente conti qui dentro: le serie, le fasce e le specifiche Vega-Lite
// arrivano gia' pronte dall'API, come per `RunChart` e `WeekChart`.
import { useEffect, useRef, useState } from "react";
import type { Result, VisualizationSpec } from "vega-embed";

import { api, isAbort, type TrendChart, type TrendData } from "../api/client";
import { addDays, shortDayLabel } from "../format";
import { MAX_DAYS, MIN_DAYS } from "../navigation";
import type { ColorScheme } from "../useColorScheme";
import { themeConfig } from "./RunChart";

// Quanto si aspetta che il cursore stia fermo prima di chiedere: senza,
// trascinandolo partirebbe una richiesta per ogni valore attraversato.
const SETTLE_MS = 250;

const PANELS = ["health", "recovery", "load", "fitness", "training"] as const;

/** Il primo giorno della finestra: `to` meno l'ampiezza, estremi compresi. */
function startOf(to: string, days: number): string {
  return addDays(to, -(days - 1));
}

/** Gli estremi della finestra, "28 Sep - 25 Oct". Con l'anno sul primo
 * quando la finestra lo scavalca: a 365 giorni "26 Oct - 25 Oct" sembrava
 * un intervallo di un giorno. */
function rangeLabel(from: string, to: string): string {
  const anno = from.slice(0, 4) === to.slice(0, 4) ? "" : ` ${from.slice(0, 4)}`;
  return `${shortDayLabel(from)}${anno} \u2013 ${shortDayLabel(to)}`;
}

function OneChart({ chart, theme }: { chart: TrendChart; theme: ColorScheme }) {
  const box = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let view: Result | null = null;
    let cancelled = false;
    setFailed(false);
    void (async () => {
      try {
        const { default: embed } = await import("vega-embed");
        if (cancelled || !box.current) return;
        view = await embed(box.current, chart.spec as VisualizationSpec, {
          actions: false,
          renderer: "svg",
          config: themeConfig(theme),
        });
        if (cancelled) view.finalize();
      } catch (error) {
        console.error(error);
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      view?.finalize();
    };
  }, [chart, theme]);

  return (
    <figure className="trend-chart">
      {failed && <p className="warning">The chart could not be drawn.</p>}
      <div ref={box} className="chart-box" />
    </figure>
  );
}

function Panel({
  panel,
  title,
  from,
  to,
  theme,
}: {
  panel: string;
  title: string;
  from: string;
  to: string;
  theme: ColorScheme;
}) {
  const [charts, setCharts] = useState<TrendChart[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    api
      .trendCharts(from, to, panel, theme, controller.signal)
      .then(setCharts)
      .catch((e: unknown) => {
        if (!isAbort(e)) {
          console.error(e);
          setError(true);
        }
      });
    return () => controller.abort();
  }, [panel, from, to, theme]);

  return (
    <section className="card trend-panel" aria-label={title}>
      <h2 className="card-title">{title}</h2>
      {error && <p className="warning">The charts could not be loaded.</p>}
      {!error && charts === null && <p className="caption">Loading…</p>}
      {charts !== null && charts.length === 0 && (
        <p className="caption">Nothing measured in this window.</p>
      )}
      <div className="trend-grid">
        {(charts ?? []).map((chart) => (
          <OneChart key={chart.key} chart={chart} theme={theme} />
        ))}
      </div>
    </section>
  );
}

export function TrendPanels({
  day,
  days,
  onDays,
  theme,
}: {
  day: string;
  days: number;
  onDays: (days: number) => void;
  theme: ColorScheme;
}) {
  // Il cursore si muove subito, la richiesta aspetta: `pending` e' dove sta
  // la manopola, `days` quello che e' gia' stato chiesto.
  const [pending, setPending] = useState(days);
  const [data, setData] = useState<TrendData | null>(null);

  useEffect(() => setPending(days), [days]);

  useEffect(() => {
    if (pending === days) return;
    const timer = window.setTimeout(() => onDays(pending), SETTLE_MS);
    return () => window.clearTimeout(timer);
  }, [pending, days, onDays]);

  const from = startOf(day, days);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    api
      .trend(from, day, controller.signal)
      .then(setData)
      .catch((e: unknown) => !isAbort(e) && console.error(e));
    return () => controller.abort();
  }, [from, day]);

  // Le fasce vogliono un minimo di giorni misurati: sotto non si disegnano,
  // e senza una riga che lo dica sembra che manchi meta' del grafico.
  const minBand = data?.min_band_days ?? 14;
  const titles = new Map((data?.panels ?? []).map((p) => [p.key, p.title]));

  return (
    <>
      <div className="trend-window">
        <label className="trend-slider">
          <span className="caption">Window</span>
          <input
            type="range"
            min={MIN_DAYS}
            max={MAX_DAYS}
            value={pending}
            onChange={(e) => setPending(Number(e.target.value))}
            aria-label="Days shown"
          />
        </label>
        <p className="caption trend-range">
          <strong>{pending} days</strong> · {rangeLabel(startOf(day, pending), day)}
        </p>
      </div>
      {pending < minBand && (
        <p className="caption">
          Under {minBand} measured days there is no band: the lines are drawn on their own.
        </p>
      )}
      {PANELS.map((panel) => (
        <Panel
          key={panel}
          panel={panel}
          title={titles.get(panel) ?? panel}
          from={from}
          to={day}
          theme={theme}
        />
      ))}
    </>
  );
}
