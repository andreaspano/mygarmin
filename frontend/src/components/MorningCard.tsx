// "This morning" (todo 34): recupero e salute della mattina, con i numeri di
// `/api/daily/{day}` e sotto i testi delle sezioni Recovery e Health del
// report. Il frontend non fa conti: medie e conteggi vengono dall'API.
import type { ReactNode } from "react";

import { iconUrl, type DailyData, type Measure } from "../api/client";
import { markdown } from "../markdown";

function num(value: number | null | undefined, digits = 0): string {
  return value == null ? "–" : value.toFixed(digits);
}

function Stat({ label, value, unit, sub }: { label: string; value: ReactNode; unit?: string; sub?: ReactNode }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {value}
        {unit && <span className="stat-unit"> {unit}</span>}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

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

/** La fascia equilibrata dell'HRV e il valore della settimana, come nel
 * mockup. La scala va un po' oltre la fascia, per vedere anche un valore
 * fuori. */
function HrvRange({ value, low, high }: { value: number | null; low: number; high: number }) {
  const pad = (high - low) * 0.6;
  const min = Math.min(low - pad, value ?? low);
  const max = Math.max(high + pad, value ?? high);
  const at = (v: number) => `${((v - min) / (max - min)) * 100}%`;
  return (
    <div className="hrv-range" aria-hidden="true">
      <div className="hrv-track">
        <div className="hrv-band" style={{ left: at(low), width: `calc(${at(high)} - ${at(low)})` }} />
        {value != null && <div className="hrv-marker" style={{ left: at(value) }} />}
      </div>
      <div className="hrv-ticks">
        <span style={{ left: at(low) }}>{low}</span>
        <span style={{ left: at(high) }}>{high}</span>
      </div>
    </div>
  );
}

function Block({ icon, title, children }: { icon: string | null; title: string; children: ReactNode }) {
  return (
    <div className="morning-block">
      <div className="block-head">
        {icon && <img src={iconUrl(icon)} alt="" width={22} height={22} />}
        <span>{title}</span>
      </div>
      {children}
    </div>
  );
}

export function MorningCard({
  data,
  recovery,
  health,
  icons,
}: {
  data: DailyData;
  recovery: string | null;
  health: string | null;
  icons: { recovery: string | null; health: string | null };
}) {
  const m = data.morning;
  const sleep = data.sleep_last_7;
  const baseline = m.hrv_baseline;
  const alerts = data.alerts;
  return (
    <section className="card morning-card" aria-label="This morning">
      <div className="card-title-row">
        <h2>This morning</h2>
        {alerts.length === 0 ? (
          <span className="badge ok">✓ No warning signs</span>
        ) : (
          <span className="badge warn" title={alerts.map((a) => a.detail).join("\n")}>
            {alerts.length === 1 ? "1 warning sign" : `${alerts.length} warning signs`}
          </span>
        )}
      </div>
      {alerts.length > 0 && (
        <ul className="alerts">
          {alerts.map((a) => (
            <li key={a.kind}>{a.detail}</li>
          ))}
        </ul>
      )}

      <Block icon={icons.recovery} title="Recovery">
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
        {recovery && <div className="prose">{markdown(recovery)}</div>}
      </Block>

      <Block icon={icons.health} title="Health">
        <div className="stats four">
          <Stat
            label="Resting heart rate"
            value={num(m.resting_hr.value)}
            unit="bpm"
            sub={`28-day avg ${num(m.resting_hr.avg_28d.mean, 1)}`}
          />
          <Stat
            label="HRV, weekly average"
            value={num(m.hrv_weekly_avg.value)}
            unit="ms"
            sub={
              <>
                {baseline && <HrvRange value={m.hrv_weekly_avg.value} low={baseline.low} high={baseline.high} />}
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
        {health && <div className="prose">{markdown(health)}</div>}
      </Block>
    </section>
  );
}
