// La seduta prevista per un giorno (todo 63): la card Plan della vista
// Training.
//
// Il file e' lo stesso del piano della settimana, `summary/05.plan/<lunedi>.md`,
// e fino a qui si leggeva solo tutto insieme nella vista Plan della Week: per
// sapere cosa era previsto **oggi** si apriva la Week e si cercava la riga a
// occhio. Qui c'e' la riga di quel giorno, accanto alla card della seduta che
// si e' fatta: prima quello che era previsto, poi quello che e' successo.
//
// Due cose in una: la **riga strutturata** dal front matter — sport, tipo,
// distanza — e sotto il **testo di quel giorno**, che e' dove sta il perche'
// («la quality e' giovedi e non martedi: la readiness di oggi vuole prima due
// giorni tranquilli»). I campi li manda l'API gia' fatti, etichetta della
// distanza compresa.
//
// **La card c'e' sempre, e un giorno senza piano la lascia vuota.** La
// cornice resta perche' la vista Training ha due riquadri a qualunque data, e
// uno che va e viene si legge come un errore; dentro non ci va niente perche'
// la cornice vuota lo dice gia' — un paragrafo che spiega dove stanno i file
// del piano e' documentazione, e si leggeva ogni volta che si apre un giorno
// fuori dal blocco.
import { iconUrl, type DayPlan } from "../api/client";
import { inline } from "../markdown";
import { CardHead, WrittenAt } from "./Stat";

// L'icona di Next, la stessa che `WeekPlanCard` e la pagina Plan danno a un
// piano: il riquadro che dice cosa fare. Un piano del giorno e' la stessa
// domanda, su un giorno invece che su sette.
const PLAN_ICON = "next.png";

/** Lo sport e l'icona con cui la pagina lo mostra. La stessa forma che vuole
 * `TrainingCard`, cosi' la `DayPage` passa l'adattatore che ha gia'. */
type Sport = {
  label: (sport: string | null | undefined) => string;
  icon: (sport: string | null | undefined) => string | null;
};

/** La seduta in una riga: l'icona dello sport, poi il tipo e la distanza
 * separati da un punto mediano, come nelle schede delle attivita'.
 *
 * Cornice e carattere sono quelli della card Training — `training-head` e un
 * `h2` — e non una regola di qui: le due card stanno una sopra l'altra nella
 * stessa vista, e due titoli di corpo diverso si leggono come due cose di
 * peso diverso. Prendendo le stesse classi restano uguali anche dopo, senza
 * che nessuno si ricordi di cambiarle in due posti.
 *
 * Il riposo ha l'icona sua (`restIcon`, da `/api/sports`) e non sta fra gli
 * sport: e' lo stesso trattamento che gli da' `TrainingCard`. Un riposo con
 * uno sport ammesso comunque lo dice — "Rest · or cycling" — perche' un
 * riposo facoltativo e un riposo secco sono due giornate diverse. */
function PlanLine({
  plan,
  sport,
  restIcon,
}: {
  plan: DayPlan;
  sport: Sport;
  restIcon: string | null;
}) {
  const rest = plan.sport === "rest";
  const icon = rest ? restIcon : sport.icon(plan.sport);
  const parts = [
    // `rest` non e' uno sport e non sta in `/api/sports`: `sport.label` ci
    // renderebbe la chiave cruda, "rest" minuscolo. Il nome e' scritto qui
    // come lo scrive `TrainingCard` nel suo stato di riposo.
    rest ? "Rest" : plan.sport ? sport.label(plan.sport) : null,
    plan.kind,
    plan.distance_label,
    rest && plan.optional ? `or ${sport.label(plan.optional)}` : null,
  ].filter((part): part is string => Boolean(part));
  return (
    <div className="training-head">
      {icon && <img src={iconUrl(icon)} alt="" width={44} height={44} />}
      <h2>{parts.join(" · ") || "Nothing planned"}</h2>
    </div>
  );
}

export function DayPlanCard({
  plan,
  day,
  loading,
  sport,
  restIcon,
}: {
  plan: DayPlan | null;
  day: string;
  loading: boolean;
  sport: Sport;
  restIcon: string | null;
}) {
  return (
    <section className="card plan-card day-plan-card" aria-label="Plan">
      <CardHead icon={PLAN_ICON} title="Plan" />
      {plan === null ? (
        // Finche' la chiamata e' in volo si dice che si sta cercando: senza,
        // la cornice vuota del caricamento e quella del giorno senza piano
        // sarebbero identiche, e la prima diventa la seconda un istante dopo.
        // E' la stessa distinzione di `WeekPlanCard`, con l'altro capo muto.
        loading ? <p className="caption">Loading…</p> : null
      ) : (
        <>
          <PlanLine plan={plan} sport={sport} restIcon={restIcon} />
          {plan.text && <div className="prose">{inline(plan.text)}</div>}
          {/* Senza `plan-file`, che e' monospaziato: nella card Training
              c'e' un carattere solo, e questa gli sta accanto. */}
          <p className="caption plan-path">summary/05.plan/{plan.file}</p>
          <WrittenAt when={plan.written_at} day={day} />
        </>
      )}
    </section>
  );
}
