// "Fitness" (todo 37 e 38): cosa Andrea e' capace di fare, che cambia piano
// nelle settimane. VO2max (prima in fondo a "Load"), endurance e hill score di
// Garmin e la soglia del lattato (o, prima che Garmin ne rilevi una, la
// frequenza di soglia del FIT), da `fitness` di `/api/daily/{day}`. Il report non ha una sezione Fitness: solo
// numeri. Un valore che manca e' "–", la card resta.
import type { ReactNode } from "react";

import type { DailyData } from "../api/client";
import { shortDayLabel } from "../format";
import { CardHead, num, Stat } from "./Stat";

// Il report non ha una sezione Fitness, quindi l'icona non viene dalle sue
// sezioni come per le altre card: e' fissa, in `icons/` con le altre.
const FITNESS_ICON = "fitness.png";

/** "6:00", dai secondi al km dell'API. */
function paceLabel(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/** "+1.0 in 28 days", verde o rosso; niente se 28 giorni fa non c'era un valore. */
function Change({ value, digits }: { value: number | null | undefined; digits: number }): ReactNode {
  if (value == null) return null;
  return (
    <span className={value >= 0 ? "delta up" : "delta down"}>
      {value >= 0 ? "+" : ""}
      {value.toFixed(digits)} in 28 days
    </span>
  );
}

export function FitnessCard({ data }: { data: DailyData }) {
  const vo2 = data.fitness.vo2max;
  const endurance = data.fitness.endurance;
  const hill = data.fitness.hill;
  const lactate = data.fitness.lactate_threshold;
  const threshold = data.fitness.threshold_hr;
  return (
    <section className="card" aria-label="Fitness">
      <CardHead icon={FITNESS_ICON} title="Fitness" />
      <div className="stats two">
        <Stat
          label="VO2max"
          value={
            <>
              {num(vo2?.now, 1)}
              <Change value={vo2?.change} digits={1} />
            </>
          }
          sub={
            vo2 &&
            `Measured ${shortDayLabel(vo2.as_of)}` +
              (vo2.days_ago_28 != null ? ` · ${vo2.days_ago_28.toFixed(1)} four weeks ago` : "")
          }
        />
        <Stat
          label="Endurance score"
          value={
            <>
              {num(endurance?.now)}
              <Change value={endurance?.change} digits={0} />
            </>
          }
          sub={endurance && [endurance.level, shortDayLabel(endurance.as_of)].filter(Boolean).join(" · ")}
        />
        <Stat
          label="Hill score"
          value={
            <>
              {num(hill?.now)}
              <Change value={hill?.change} digits={0} />
            </>
          }
          sub={hill && shortDayLabel(hill.as_of)}
        />
        {lactate ? (
          <Stat
            label="Lactate threshold"
            value={num(lactate.heart_rate)}
            unit="bpm"
            sub={[
              lactate.pace_s_per_km != null && `${paceLabel(lactate.pace_s_per_km)} /km`,
              lactate.speed_kmh != null && `${lactate.speed_kmh.toFixed(1)} km/h`,
              `Detected ${shortDayLabel(lactate.as_of)}`,
            ]
              .filter(Boolean)
              .join(" · ")}
          />
        ) : (
          <Stat
            label="Threshold heart rate"
            value={num(threshold?.value)}
            unit="bpm"
            sub={threshold && `From the activity of ${shortDayLabel(threshold.as_of)}`}
          />
        )}
      </div>
    </section>
  );
}
