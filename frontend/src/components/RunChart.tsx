// Il grafico a tre fasce: la specifica Vega-Lite di
// `/api/activities/{id}/chart/vega`, disegnata com'e' con vega-embed. Non si
// riscrive: lo disegna Altair (`run_chart.run_analysis_chart`).
import { useEffect, useRef, useState } from "react";
import type { Result, VisualizationSpec } from "vega-embed";

import { api } from "../api/client";
import type { ColorScheme } from "../useColorScheme";

// I colori di assi, legende e griglia. La specifica di Altair non li fissa
// (nella Streamlit li mette il tema di Streamlit): senza, sul fondo scuro le
// scritte di Vega restano grigio scuro e non si leggono.
const TEXT_COLORS: Record<ColorScheme, { text: string; muted: string; grid: string }> = {
  light: { text: "#31333f", muted: "#6b7280", grid: "rgba(49, 51, 63, 0.1)" },
  dark: { text: "#fafafa", muted: "#9ca3af", grid: "rgba(250, 250, 250, 0.12)" },
};

function themeConfig(theme: ColorScheme) {
  const c = TEXT_COLORS[theme];
  return {
    // Il fondo lo da' la pagina, nei due temi.
    background: "transparent",
    axis: { labelColor: c.muted, titleColor: c.text, gridColor: c.grid, domainColor: c.muted, tickColor: c.muted },
    legend: { labelColor: c.text, titleColor: c.text },
    title: { color: c.text },
    view: { stroke: c.grid },
    // Assi e titoli dentro la larghezza del riquadro, non in piu': senza,
    // l'SVG sporgeva di una cinquantina di pixel a destra della scheda.
    autosize: { type: "fit-x" as const, contains: "padding" as const },
  };
}

export function RunChart({ activityId, theme }: { activityId: number; theme: ColorScheme }) {
  const box = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    let view: Result | null = null;
    let cancelled = false;
    setState("loading");
    api
      .chartVega(activityId, theme, controller.signal)
      .then(async (spec) => {
        if (cancelled || !box.current) return;
        if (!spec) {
          setState("empty");
          return;
        }
        // `width: "container"` prende la larghezza del riquadro, che c'e'
        // gia' quando si chiama `embed`; vega-embed lo segue se cambia.
        // vega-embed si carica solo qui: Vega e' la parte piu' grande
        // dell'app, e la tabella non deve aspettarla.
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
        if (!cancelled && !(error instanceof DOMException && error.name === "AbortError")) {
          console.error(error);
          setState("error");
        }
      });
    return () => {
      cancelled = true;
      controller.abort();
      view?.finalize();
    };
  }, [activityId, theme]);

  return (
    <section className="chart" aria-label="Activity chart">
      {state === "empty" && <p className="info">No heart rate or speed to plot for this activity.</p>}
      {state === "error" && <p className="warning">The chart could not be loaded.</p>}
      <div ref={box} className="chart-box" hidden={state === "empty" || state === "error"} />
    </section>
  );
}
