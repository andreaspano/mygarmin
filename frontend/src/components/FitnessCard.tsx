// "Fitness" (todo 37): cosa Andrea e' capace di fare, che cambia piano nelle
// settimane. Il VO2max (prima in fondo a "Load") e la frequenza di soglia, da
// `fitness` di `/api/daily/{day}`. Il report non ha una sezione Fitness: solo
// numeri. Un valore che manca e' "–", la card resta.
import type { DailyData } from "../api/client";
import { shortDayLabel } from "../format";
import { CardHead, num, Stat } from "./Stat";

export function FitnessCard({ data }: { data: DailyData }) {
  const vo2 = data.fitness.vo2max;
  const threshold = data.fitness.threshold_hr;
  return (
    <section className="card" aria-label="Fitness">
      <CardHead icon={null} title="Fitness" />
      <div className="stats two">
        <Stat
          label="VO2max"
          value={
            <>
              {num(vo2?.now, 1)}
              {vo2?.change != null && (
                <span className={vo2.change >= 0 ? "delta up" : "delta down"}>
                  {vo2.change >= 0 ? "+" : ""}
                  {vo2.change.toFixed(1)} in 28 days
                </span>
              )}
            </>
          }
          sub={
            vo2 &&
            `Measured ${shortDayLabel(vo2.as_of)}` +
              (vo2.days_ago_28 != null ? ` · ${vo2.days_ago_28.toFixed(1)} four weeks ago` : "")
          }
        />
        <Stat
          label="Threshold heart rate"
          value={num(threshold?.value)}
          unit="bpm"
          sub={threshold && `From the activity of ${shortDayLabel(threshold.as_of)}`}
        />
      </div>
    </section>
  );
}
