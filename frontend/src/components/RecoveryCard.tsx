// "Recovery" (todo 37, prima un blocco di "This morning"): readiness, sonno e
// body battery della mattina da `/api/daily/{day}`, sotto la sezione Recovery
// del report. Il frontend non fa conti: medie e conteggi vengono dall'API.
import type { ReactNode } from "react";

import type { DailyData, Measure } from "../api/client";
import { markdown } from "../markdown";
import { CardHead, num, Stat } from "./Stat";

function avgs(m: Measure, digits = 1): string {
  return `7-day avg ${num(m.avg_7d.mean, digits)} · 28-day avg ${num(m.avg_28d.mean, digits)}`;
}

/** "8h04", dai minuti dell'API. */
function sleepValue(minutes: number | null): ReactNode {
  if (minutes == null) return "–";
  return (
    <>
      {Math.floor(minutes / 60)}
      <span className="stat-unit">h</span>
      {String(minutes % 60).padStart(2, "0")}
    </>
  );
}

export function RecoveryCard({
  data,
  text,
  icon,
  refresh,
}: {
  data: DailyData;
  text: string | null;
  icon: string | null;
  refresh?: ReactNode;
}) {
  const m = data.morning;
  const sleep = data.sleep_last_7;
  return (
    <section className="card" aria-label="Recovery">
      <CardHead icon={icon} title="Recovery" refresh={refresh} />
      <div className="stats">
        <Stat label="Readiness" value={num(m.readiness.value)} sub={avgs(m.readiness)} />
        <Stat
          label="Sleep"
          value={sleepValue(data.sleep_minutes)}
          sub={`Score ${num(m.sleep_score.value)} · ${sleep.short_nights} of ${sleep.nights_measured} nights under 7 h`}
        />
        <Stat
          label="Body battery at wake-up"
          value={num(m.body_battery_morning.value)}
          sub={`Yesterday's low ${num(m.body_battery_low_yesterday.value)}`}
        />
      </div>
      {text && <div className="prose">{markdown(text)}</div>}
    </section>
  );
}
