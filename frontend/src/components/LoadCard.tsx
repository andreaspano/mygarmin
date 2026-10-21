// "Load" (todo 34, rifatta sullo stampo di Health): il carico di Garmin. Il
// titolo e' lo stato del carico detto a parole (la prima frase del report era
// troppo lunga per un titolo), poi le tre parti del carico mensile, ognuna
// con la barra della **fascia obiettivo di Garmin** e il valore di oggi come
// tacca, e il rapporto fra carico recente e abituale, che una fascia non ce
// l'ha. Sotto, il testo della sezione Load del report. Il VO2max e' passato
// alla card Fitness (todo 37).
import type { ReactNode } from "react";

import type { DailyData } from "../api/client";
import { markdown } from "../markdown";
import { CardHead, RangeBar, Stat, WrittenAt, num } from "./Stat";

type Key = "load_aerobic_low" | "load_aerobic_high" | "load_anaerobic";

const ROWS: { key: Key; label: string; help: string }[] = [
  {
    key: "load_aerobic_low",
    label: "Low aerobic",
    help: "Garmin's monthly load from easy aerobic work, against the range Garmin wants you in.",
  },
  {
    key: "load_aerobic_high",
    label: "High aerobic",
    help: "Garmin's monthly load from harder aerobic work, against the range Garmin wants you in.",
  },
  {
    key: "load_anaerobic",
    label: "Anaerobic",
    help: "Garmin's monthly load from efforts above threshold, against the range Garmin wants you in.",
  },
];

// Lo stato del carico di Garmin (`acwr_status`), come titolo del riquadro.
const STATUS_TITLES: Record<string, string> = {
  LOW: "Below your usual load",
  OPTIMAL: "In a healthy range",
  HIGH: "Above your usual load",
  VERY_HIGH: "Well above your usual load",
};

/** Dove sta il carico rispetto alla fascia obiettivo, accanto al numero come
 * il "+1.2 in 28 days" di Fitness. */
function Against({ value, min, max }: { value: number; min: number; max: number }): ReactNode {
  const word = value < min ? "short" : value > max ? "above target" : "in range";
  return <span className="delta muted">{word}</span>;
}

export function LoadCard({
  data,
  text,
  writtenAt,
  day,
  icon,
  refresh,
}: {
  data: DailyData;
  text: string | null;
  writtenAt: string | null;
  day: string;
  icon: string | null;
  refresh?: ReactNode;
}) {
  const now = data.load.now;
  const targets = data.load.targets;
  const title = (now?.acwr_status && STATUS_TITLES[now.acwr_status]) ?? "Load";
  return (
    <section className="card load-card" aria-label="Load">
      <CardHead icon={icon} title="Load" refresh={refresh} />
      <h2>{title}</h2>
      {/* La fascia e' il bersaglio di Garmin, non una media nostra: ha un
          livello solo, quindi `outer` coincide con gli estremi e la barra
          non ha la tinta piu' chiara delle altre card. */}
      <div className="stats two">
        {ROWS.map(({ key, label, help }) => {
          const value = now?.[key] ?? null;
          const target = targets?.[key];
          return (
            <Stat
              key={key}
              label={label}
              help={help}
              value={
                <>
                  {num(value)}
                  {value != null && target && <Against value={value} min={target.min} max={target.max} />}
                </>
              }
              sub={
                value != null &&
                target && (
                  <RangeBar
                    value={value}
                    band={{ low: target.min, high: target.max, outer_low: target.min, outer_high: target.max }}
                    tick={(v) => v.toFixed(0)}
                  />
                )
              }
            />
          );
        })}
        <Stat
          label="Load ratio"
          value={num(now?.acwr, 1)}
          help="Garmin's acute-to-chronic load ratio: the last week of training against the last four. Around 1 means you are carrying what you usually carry."
        />
      </div>
      {text && <div className="prose">{markdown(text)}</div>}
      <WrittenAt when={writtenAt} day={day} />
    </section>
  );
}
