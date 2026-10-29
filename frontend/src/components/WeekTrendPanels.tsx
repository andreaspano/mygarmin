// Il Trend della Week (todo 78): la fila delle settimane, un punto per
// settimana ISO, in una finestra che si sceglie col cursore da 4 a 52.
//
// E' il gemello del Trend della Day, e il meccanismo e' letteralmente lo
// stesso: `OneChart`, `Panel`, `TrendWindow` e i cinque pannelli vengono da
// li'. Qui dentro sta solo quello che cambia, che sono le **parole** —
// l'ampiezza in settimane, l'intervallo scritto per settimane, le due
// didascalie — piu' una cosa che non e' una parola: dove porta un clic.
//
// Niente conti: medie, somme, fasce e specifiche Vega-Lite arrivano pronte
// dall'API, come per la Day.
import { useCallback, useEffect, useState } from "react";

import { api, isAbort, type WeekTrendData } from "../api/client";
import { addDays, isoWeek, mondayOf, shortDayLabel } from "../format";
import { MAX_WEEKS, MIN_WEEKS, pushUrl } from "../navigation";
import type { ColorScheme } from "../useColorScheme";
import { PANELS, Panel, TrendWindow } from "./TrendPanels";

/** Il lunedi' della prima settimana della finestra. */
function startOf(monday: string, weeks: number): string {
  return addDays(monday, -(weeks - 1) * 7);
}

/** Gli estremi della finestra a settimane, "W33 10 Aug - W44 26 Oct". Il
 * numero della settimana sta davanti alla sua data, che qui l'unita' e' la
 * settimana e il lunedi' e' solo il modo di nominarla. L'anno compare sul
 * primo estremo quando la finestra lo scavalca, come nella Day. */
function weekRangeLabel(from: string, to: string): string {
  const anno = from.slice(0, 4) === to.slice(0, 4) ? "" : ` ${from.slice(0, 4)}`;
  return `W${isoWeek(from)} ${shortDayLabel(from)}${anno} \u2013 W${isoWeek(to)} ${shortDayLabel(to)}`;
}

/** Il lunedi' **piu' vicino** al giorno cliccato, che e' la settimana che la
 * barra grigia sta indicando.
 *
 * Non `mondayOf`: i punti di questa vista sono lunedi' distanti sette giorni,
 * e la barra segue il punto piu' vicino (`nearest`). Cliccando da giovedi' in
 * poi `mondayOf` aprirebbe la settimana **prima** di quella evidenziata. E' lo
 * stesso motivo per cui `dayAt` arrotonda al giorno vicino invece che a quello
 * in cui il clic e' caduto. */
function nearestMonday(day: string): string {
  const monday = mondayOf(day);
  const avanti = Math.round((Date.parse(day) - Date.parse(monday)) / 86400000);
  return avanti >= 4 ? addDays(monday, 7) : monday;
}

export function WeekTrendPanels({
  monday,
  weeks,
  onWeeks,
  theme,
}: {
  monday: string;
  weeks: number;
  onWeeks: (weeks: number) => void;
  theme: ColorScheme;
}) {
  const [data, setData] = useState<WeekTrendData | null>(null);

  // Un clic apre lo Snap di quella settimana, senza ricaricare la pagina.
  // Mai oltre la settimana in corso, che l'API quella la rifiuta.
  const onPick = useCallback((day: string) => {
    const scelto = nearestMonday(day);
    const corrente = mondayOf(new Date().toISOString().slice(0, 10));
    pushUrl({ period: "week", page: null, monday: scelto > corrente ? corrente : scelto, view: null });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    api
      .weekTrend(monday, weeks, controller.signal)
      .then(setData)
      .catch((e: unknown) => !isAbort(e) && console.error(e));
    return () => controller.abort();
  }, [monday, weeks]);

  const heads = new Map((data?.panels ?? []).map((p) => [p.key, p]));
  const minDays = data?.min_week_days ?? 3;
  // Quanti giorni ha l'ultima settimana: lo dice un pannello a media
  // qualunque, che il conto e' lo stesso su tutti.
  const ultima = data?.panels[0]?.series[0]?.points.at(-1);
  const aperta = ultima !== undefined && ultima.days > 0 && ultima.days < 7;

  return (
    <>
      <TrendWindow
        min={MIN_WEEKS}
        max={MAX_WEEKS}
        value={weeks}
        onChange={onWeeks}
        label={(pending) => `${pending} weeks`}
        range={(pending) => weekRangeLabel(startOf(monday, pending), monday)}
      />
      {/* Due didascalie, tutte e due per cose che si leggerebbero male da
          sole. La fascia di qui non e' quella delle altre viste e va detto
          cosa misura; e una settimana aperta spiega da se' perche' l'ultimo
          punto cala e la sua fascia e' larga. */}
      <p className="caption">
        It reads as a control chart. The dashed line is the window&rsquo;s centre, the mean of
        the weekly means; the band around it is one and two standard errors, built from the
        typical scatter inside a week and divided by the root of the days each week was
        measured on &mdash; so it widens where an average rests on fewer days.{" "}
        <strong>A point outside the band is a week that did something different.</strong> A
        week with fewer than {minDays} measured days has no band, and Training has none at all.
      </p>
      {aperta && (
        <p className="caption">
          This week is still running: {ultima.days} of 7 days. Its averages are made of fewer
          days and its totals are partial.
        </p>
      )}
      {PANELS.map((panel) => (
        <Panel
          key={panel}
          panel={panel}
          period="week"
          title={heads.get(panel)?.title ?? panel}
          icon={heads.get(panel)?.icon ?? null}
          anchor={monday}
          span={weeks}
          theme={theme}
          onPick={onPick}
        />
      ))}
    </>
  );
}
