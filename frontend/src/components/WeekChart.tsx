// Il lavoro della settimana per sport (todo 52): la specifica Vega-Lite di
// `/api/weekly/{monday}/chart/vega`, disegnata com'e' con vega-embed. Non si
// riscrive: la disegna Altair (`run_chart.week_sports_chart`).
//
// Stesso schema di `RunChart`, da cui prende anche i colori di assi e
// legende: vega-embed si carica solo qui e in RunChart, perche' e' la parte
// piu' grande dell'app e il resto della pagina non deve aspettarla.
import { useEffect, useRef, useState } from "react";
import type { Result, VisualizationSpec } from "vega-embed";

import { api, isAbort } from "../api/client";
import type { ColorScheme } from "../useColorScheme";
import { themeConfig } from "./RunChart";

export function WeekChart({ monday, theme }: { monday: string; theme: ColorScheme }) {
  const box = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    let view: Result | null = null;
    let cancelled = false;
    setState("loading");
    api
      .weeklyChartVega(monday, theme, controller.signal)
      .then(async (spec) => {
        if (cancelled || !box.current) return;
        if (!spec) {
          setState("empty");
          return;
        }
        const { default: embed } = await import("vega-embed");
        if (cancelled || !box.current) return;
        view = await embed(box.current, spec as VisualizationSpec, {
          actions: false,
          renderer: "svg",
          config: themeConfig(theme),
        });
        if (cancelled) view.finalize();
        else setState("ready");
      })
      .catch((error: unknown) => {
        if (!cancelled && !isAbort(error)) {
          console.error(error);
          setState("error");
        }
      });
    return () => {
      cancelled = true;
      controller.abort();
      view?.finalize();
    };
  }, [monday, theme]);

  return (
    <section className="chart week-chart" aria-label="The week's work by sport">
      {state === "error" && <p className="warning">The chart could not be loaded.</p>}
      <div ref={box} className="chart-box" hidden={state !== "ready"} />
    </section>
  );
}
