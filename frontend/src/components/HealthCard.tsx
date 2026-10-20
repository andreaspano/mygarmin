// "Health" (todo 37, prima un blocco di "This morning"): frequenza a riposo,
// HRV, respiro e stress da `/api/daily/{day}`, sotto la sezione Health del
// report. Il frontend non fa conti: medie e fasce vengono dall'API.
import type { Band, DailyData, Measure } from "../api/client";
import { markdown } from "../markdown";
import { CardHead, num, Stat } from "./Stat";

/** Una fascia e il valore di oggi dentro (come nel mockup): la fascia
 * equilibrata dell'HRV secondo Garmin, e la fascia d'abitudine del battito a
 * riposo che calcola l'API. La scala va un po' oltre la fascia, per vedere
 * anche un valore fuori. */
function RangeBar({ value, band }: { value: number | null; band: Band }) {
  const { low, high, outer_low: outerLow, outer_high: outerHigh } = band;
  const pad = (outerHigh - outerLow) * 0.12;
  const min = Math.min(outerLow - pad, value ?? outerLow);
  const max = Math.max(outerHigh + pad, value ?? outerHigh);
  const at = (v: number) => `${((v - min) / (max - min)) * 100}%`;
  const span = (a: number, b: number) => ({ left: at(a), width: `calc(${at(b)} - ${at(a)})` });
  return (
    <div className="range-bar" aria-hidden="true">
      <div className="range-track">
        <div className="range-wide" style={span(outerLow, outerHigh)} />
        <div className="range-band" style={span(low, high)} />
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
  return <RangeBar value={measure.value} band={measure.band} />;
}

export function HealthCard({ data, text, icon }: { data: DailyData; text: string | null; icon: string | null }) {
  const m = data.morning;
  // Sotto ogni numero solo la barra della sua fascia: dice da sola dove sta
  // il valore, e gli estremi sono scritti sulle tacche. Tutte e quattro le
  // fasce sono quelle dell'API (`band`): media dei 28 giorni prima piu' e
  // meno uno scarto tipo. La fascia equilibrata di Garmin (`hrv_baseline`)
  // resta nei dati e la usano il report e l'allarme dell'HRV, non la card.
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
          label="HRV, last night"
          value={num(m.hrv_last_night.value)}
          unit="ms"
          sub={<MeasureBar measure={m.hrv_last_night} />}
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
