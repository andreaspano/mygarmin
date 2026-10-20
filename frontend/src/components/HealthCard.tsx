// "Health" (todo 37, prima un blocco di "This morning"): frequenza a riposo,
// HRV, respiro e stress da `/api/daily/{day}`, sotto la sezione Health del
// report. Il frontend non fa conti: medie e fasce vengono dall'API.
import type { DailyData, Measure } from "../api/client";
import { markdown } from "../markdown";
import { CardHead, num, Stat } from "./Stat";

/** Una fascia e il valore di oggi dentro (come nel mockup): la fascia
 * equilibrata dell'HRV secondo Garmin, e la fascia d'abitudine del battito a
 * riposo che calcola l'API. La scala va un po' oltre la fascia, per vedere
 * anche un valore fuori. */
function RangeBar({ value, low, high }: { value: number | null; low: number; high: number }) {
  const pad = (high - low) * 0.6;
  const min = Math.min(low - pad, value ?? low);
  const max = Math.max(high + pad, value ?? high);
  const at = (v: number) => `${((v - min) / (max - min)) * 100}%`;
  return (
    <div className="range-bar" aria-hidden="true">
      <div className="range-track">
        <div className="range-band" style={{ left: at(low), width: `calc(${at(high)} - ${at(low)})` }} />
        {value != null && <div className="range-marker" style={{ left: at(value) }} />}
      </div>
      <div className="range-ticks">
        <span style={{ left: at(low) }}>{low}</span>
        <span style={{ left: at(high) }}>{high}</span>
      </div>
    </div>
  );
}

/** La barra della fascia di una misura, o niente se la fascia non c'e'
 * (pochi giorni misurati). */
function MeasureBar({ measure }: { measure: Measure }) {
  if (!measure.band) return null;
  return <RangeBar value={measure.value} low={measure.band.low} high={measure.band.high} />;
}

export function HealthCard({ data, text, icon }: { data: DailyData; text: string | null; icon: string | null }) {
  const m = data.morning;
  // Sotto ogni numero solo la barra della sua fascia: dice da sola dove sta
  // il valore, e gli estremi sono scritti sulle tacche. Quella dell'HRV e'
  // di Garmin (`hrv_baseline`), le altre le calcola l'API dai 28 giorni
  // prima e stanno dentro la misura (`band`).
  const baseline = m.hrv_baseline;
  return (
    <section className="card" aria-label="Health">
      <CardHead icon={icon} title="Health" />
      <div className="stats two">
        <Stat
          label="Resting heart rate"
          value={num(m.resting_hr.value)}
          unit="bpm"
          // Sotto il numero solo la barra: la fascia dice da sola dove sta
          // il valore, e i suoi estremi sono scritti sulle tacche.
          sub={<MeasureBar measure={m.resting_hr} />}
        />
        <Stat
          label="HRV, weekly average"
          value={num(m.hrv_weekly_avg.value)}
          unit="ms"
          sub={baseline && <RangeBar value={m.hrv_weekly_avg.value} low={baseline.low} high={baseline.high} />}
        />
        <Stat
          label="Breathing in sleep"
          value={num(m.resp_sleep.value, 1)}
          unit="/min"
          sub={<MeasureBar measure={m.resp_sleep} />}
        />
        <Stat label="Stress, yesterday" value={num(m.stress_avg_yesterday.value)} sub={<MeasureBar measure={m.stress_avg_yesterday} />} />
      </div>
      {text && <div className="prose">{markdown(text)}</div>}
    </section>
  );
}
