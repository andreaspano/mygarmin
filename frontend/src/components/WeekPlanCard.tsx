// Il piano della settimana (todo 60): la vista Plan della Week.
//
// Il file e' `summary/05.plan/<lunedi>.md`, uno per settimana del blocco. Lo
// scriveva solo l'agente Next, dentro il prompt, e all'utente arrivava di
// rimbalzo nella prosa di qualcun altro: qui si legge per quello che e', le
// sette sedute della settimana con i ritmi e i segnali per scaricare.
//
// **Non e' il piano di `plan/`**, che sta nella pagina a destra: quello dura
// un blocco e parla di una gara, questo dura sette giorni e dice cosa fare.
// I numeri in cima li tiene insieme: da che blocco viene, a che settimana
// siamo, quale gara e con che bersaglio.
//
// Una settimana senza file non e' un errore — prima dell'inizio del blocco
// non ce n'e' nessuno — e la vista lo dice invece di restare muta.
import { type WeekPlan } from "../api/client";
import { raceLabel, shortDayLabel, targetLabel } from "../format";
import { markdown } from "../markdown";
import { CardHead, Stat, WrittenAt } from "./Stat";

// L'icona di Next, come nella pagina Plan: il riquadro che dice cosa fare
// dopo. Un piano e' la stessa domanda, su sette giorni invece che su domani.
const PLAN_ICON = "next.png";

/** I numeri del piano, sopra il testo: dove sta questa settimana nel blocco e
 * verso cosa. Quelli che il front matter non ha restano un trattino, come in
 * tutte le altre card.
 *
 * Tutti e quattro **su una riga sola** (`stats four`, la stessa griglia della
 * card Training): si leggono come una didascalia del titolo — fase, settimana
 * del blocco, gara, bersaglio — e su due righe la griglia a tre colonne ne
 * lasciava uno spaiato in fondo. */
function WeekPlanStats({ plan }: { plan: WeekPlan }) {
  const of =
    plan.block_week != null && plan.block_weeks != null
      ? `${plan.block_week} of ${plan.block_weeks}`
      : plan.block_week != null
        ? `${plan.block_week}`
        : "–";
  return (
    <div className="stats four">
      <Stat label="Phase" value={plan.phase ?? "–"} />
      <Stat
        label="Block week"
        value={of}
        sub={plan.plan ? <span className="muted">{plan.plan}</span> : undefined}
      />
      <Stat label="Race" value={plan.race ? raceLabel(plan.race) : "–"} />
      <Stat label="Target" value={targetLabel(plan.target_time)} />
    </div>
  );
}

export function WeekPlanCard({
  plan,
  monday,
  loading,
}: {
  plan: WeekPlan | null;
  monday: string;
  loading: boolean;
}) {
  if (plan === null) {
    // Finche' la chiamata e' in volo non si dice ancora che il piano non
    // c'e': "Loading…" e "no plan" sono due cose diverse, e scambiarle fa
    // lampeggiare un errore che non e' vero.
    if (loading) return <p className="caption">Loading…</p>;
    return (
      <p className="info">
        No plan for the week of {shortDayLabel(monday)}. The weeks of a block are files in{" "}
        <code>summary/05.plan/</code>, named after their Monday; the weeks before a block
        starts do not have one.
      </p>
    );
  }
  return (
    <section className="card plan-card" aria-label="Weekly plan">
      <CardHead icon={PLAN_ICON} title={plan.title} />
      <WeekPlanStats plan={plan} />
      <div className="prose plan-prose">{markdown(plan.body)}</div>
      <p className="caption plan-file">summary/05.plan/{plan.file}</p>
      <WrittenAt when={plan.written_at} day={monday} />
    </section>
  );
}
