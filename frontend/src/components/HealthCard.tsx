// "Health" (todo 37, prima un blocco di "This morning"): frequenza a riposo,
// HRV, respiro e stress da `/api/daily/{day}`, sotto la sezione Health del
// report. Il frontend non fa conti: medie e fasce vengono dall'API.
import type { DailyData } from "../api/client";
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

export function HealthCard({ data, text, icon }: { data: DailyData; text: string | null; icon: string | null }) {
  const m = data.morning;
  const baseline = m.hrv_baseline;
  // La fascia d'abitudine del battito a riposo: la calcola l'API dai 28
  // giorni prima (media piu' e meno uno scarto tipo), perche' Garmin non ne
  // manda una come fa per l'HRV.
  const restingBand = m.resting_hr_band;
  return (
    <section className="card" aria-label="Health">
      <CardHead icon={icon} title="Health" />
      <div className="stats two">
        <Stat
          label="Resting heart rate"
          value={num(m.resting_hr.value)}
          unit="bpm"
          sub={
            <>
              {restingBand && <RangeBar value={m.resting_hr.value} low={restingBand.low} high={restingBand.high} />}
              {restingBand && `Usual range ${num(restingBand.low, 1)}–${num(restingBand.high, 1)} · `}
              28-day avg {num(m.resting_hr.avg_28d.mean, 1)}
            </>
          }
        />
        <Stat
          label="HRV, weekly average"
          value={num(m.hrv_weekly_avg.value)}
          unit="ms"
          sub={
            <>
              {baseline && <RangeBar value={m.hrv_weekly_avg.value} low={baseline.low} high={baseline.high} />}
              {baseline && `Balanced range ${baseline.low}–${baseline.high} · `}
              28-day avg {num(m.hrv_weekly_avg.avg_28d.mean, 1)} · last night {num(m.hrv_last_night.value)} ms
            </>
          }
        />
        <Stat
          label="Breathing in sleep"
          value={num(m.resp_sleep.value, 1)}
          unit="/min"
          sub={`28-day avg ${num(m.resp_sleep.avg_28d.mean, 1)}`}
        />
        <Stat
          label="Stress, yesterday"
          value={num(m.stress_avg_yesterday.value)}
          sub={`28-day avg ${num(m.stress_avg_yesterday.avg_28d.mean, 1)}`}
        />
      </div>
      {text && <div className="prose">{markdown(text)}</div>}
    </section>
  );
}
