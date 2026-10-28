// Il giudizio sulla seduta (todo 66): la terza card della vista Training.
//
// E' il testo della sezione Training del report, che fino a ieri stava
// **dentro** la card della seduta, nella colonna di destra accanto ai menu.
// Li' era una didascalia dei numeri; qui e' quello che e': il verdetto
// dell'allenatore, che dal todo 64 guarda sia il piano del giorno sia come
// l'hai eseguito. Lo scrive il giro della sera, alle nove.
//
// La cornice c'e' sempre, anche senza testo: la vista Training ha tre
// riquadri a qualunque data, e uno che va e viene si legge come un errore.
// Lo stesso ragionamento della card Plan (todo 63), e come quella un giorno
// senza testo resta vuoto invece di spiegare perche'.
import type { ReactNode } from "react";

import { markdown } from "../markdown";
import { CardHead, WrittenAt } from "./Stat";

export function TrainingCommentCard({
  comment,
  writtenAt,
  day,
  icon,
  refresh,
}: {
  comment: string | null;
  writtenAt: string | null;
  day: string;
  icon: string | null;
  refresh?: ReactNode;
}) {
  return (
    <section className="card comment-card" aria-label="Comment">
      <CardHead icon={icon} title="Comment" refresh={refresh} />
      {comment && <div className="prose">{markdown(comment)}</div>}
      <WrittenAt when={writtenAt} day={day} />
    </section>
  );
}
