// "Fitness" (todo 37 e 38, rifatta dal 48 sullo stampo di Health): cosa
// Andrea e' capace di fare, che cambia piano nelle settimane. VO2max (prima
// in fondo a "Load"), endurance e hill score di Garmin e la soglia del
// lattato (o, prima che Garmin ne rilevi una, la frequenza di soglia del
// FIT), da `fitness` di `/api/daily/{day}`. Il testo lo scrive l'agente
// `04_fitness` (todo 44). Un valore che manca e' "–", la card resta.
//
// Accanto al numero non va niente: la variazione in 28 giorni ("+1.2 in 28
// days") raccontava un andamento, e queste card dicono com'e' oggi. Dove sta
// la misura lo fa vedere la barra.
import type { ReactNode } from "react";

import type { DailyData } from "../api/client";
import { markdown } from "../markdown";
import { CardHead, RangeBar, Stat, WrittenAt, num } from "./Stat";

export function FitnessCard({
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
  const vo2 = data.fitness.vo2max;
  const endurance = data.fitness.endurance;
  const hill = data.fitness.hill;
  const lactate = data.fitness.lactate_threshold;
  const threshold = data.fitness.threshold_hr;
  // Sotto ogni numero solo la barra della sua fascia, come in Health e
  // Recovery. Qui pero' **sopra la fascia e' buono**: queste misure si
  // muovono in settimane, e stare sopra l'ultimo mese vuol dire che stanno
  // ancora salendo. La soglia non ha fascia (e' un valore solo, rilevato di
  // rado) e resta un numero nudo.
  return (
    <section className="card fitness-card" aria-label="Fitness">
      <CardHead icon={icon} title="Fitness" refresh={refresh} />
      <div className="stats two">
        <Stat
          label="VO2max"
          value={num(vo2?.now, 1)}
          sub={vo2?.band && <RangeBar value={vo2.now} band={vo2.band} />}
        />
        <Stat
          label="Endurance score"
          value={num(endurance?.now)}
          sub={endurance?.band && <RangeBar value={endurance.now} band={endurance.band} />}
        />
        <Stat
          label="Hill score"
          value={num(hill?.now)}
          sub={hill?.band && <RangeBar value={hill.now} band={hill.band} />}
        />
        {lactate ? (
          <Stat label="Lactate threshold" value={num(lactate.heart_rate)} unit="bpm" />
        ) : (
          <Stat label="Threshold heart rate" value={num(threshold?.value)} unit="bpm" />
        )}
      </div>
      {text && <div className="prose">{markdown(text)}</div>}
      <WrittenAt when={writtenAt} day={day} />
    </section>
  );
}
