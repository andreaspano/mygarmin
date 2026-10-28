// La seduta prevista di un giorno, come si legge e come si disegna (todo
// 71). Sta in un file suo perche' la vogliono in due: la card Plan della Day,
// che ne mostra una sola e grande, e quella della Week, che ne mette sette in
// fila. Prima la composizione del testo era scritta dentro la prima, e la
// seconda avrebbe dovuto copiarla.
import { iconUrl, type PlannedSession } from "../api/client";

/** Lo sport e l'icona con cui la pagina lo mostra: l'adattatore che le
 * pagine costruiscono da `/api/sports` e passano alle card. */
export type Sport = {
  label: (sport: string | null | undefined) => string;
  icon: (sport: string | null | undefined) => string | null;
};

/** La seduta in una riga di testo: sport, tipo e distanza separati da un
 * punto mediano, come nelle schede delle attivita'.
 *
 * Un riposo con uno sport ammesso comunque lo dice — "Rest · or Cycling" —
 * perche' un riposo facoltativo e un riposo secco sono due giornate diverse.
 * E `rest` **non e' uno sport**: non sta in `/api/sports`, quindi
 * `sport.label` renderebbe la chiave cruda, "rest" minuscolo. Il nome e'
 * scritto qui come lo scrive `TrainingCard` nel suo stato di riposo. */
export function sessionLabel(plan: PlannedSession, sport: Sport): string {
  const rest = plan.sport === "rest";
  const parts = [
    rest ? "Rest" : plan.sport ? sport.label(plan.sport) : null,
    plan.kind,
    plan.distance_label,
    rest && plan.optional ? `or ${sport.label(plan.optional)}` : null,
  ].filter((part): part is string => Boolean(part));
  return parts.join(" · ") || "Nothing planned";
}

/** L'icona della seduta: quella dello sport, o quella del riposo, che sta a
 * parte in `/api/sports` (`rest_icon`). */
export function sessionIcon(
  plan: PlannedSession,
  sport: Sport,
  restIcon: string | null,
): string | null {
  return plan.sport === "rest" ? restIcon : sport.icon(plan.sport);
}

/** La seduta come **titolo**: e' la forma della card Plan della Day, che di
 * sedute ne mostra una.
 *
 * Cornice e carattere sono quelli della card della seduta — `training-head` e
 * un `h2` — e non una regola di qui: le due card stanno una sopra l'altra
 * nella stessa vista, e due titoli di corpo diverso si leggono come due cose
 * di peso diverso. Prendendo le stesse classi restano uguali anche dopo,
 * senza che nessuno si ricordi di cambiarle in due posti. */
export function PlanLine({
  plan,
  sport,
  restIcon,
}: {
  plan: PlannedSession;
  sport: Sport;
  restIcon: string | null;
}) {
  const icon = sessionIcon(plan, sport, restIcon);
  return (
    <div className="training-head">
      {icon && <img src={iconUrl(icon)} alt="" width={44} height={44} />}
      <h2>{sessionLabel(plan, sport)}</h2>
    </div>
  );
}
