// Il riquadro "Summary": fondo scuro e un accento suo, il viola, nato per
// stare accanto all'arancio di Next.
//
// **Due pezzi o uno, e li decide chi la usa.** La settimana ne ha due veri —
// l'apertura del lunedi e la chiusura della domenica (todo 53) — e li tiene.
// Il giorno dal todo 66 ne ha **uno**: un giro solo, la mattina, e un
// soggetto solo, il corpo. Prima erano due anche li' (il sole e la luna del
// todo 49), perche' i giri erano due e ognuno scriveva mezzo verdetto.
//
// Senza `evening` la card e' un pezzo solo e l'occhiello dice "Summary"
// senza aggiungere altro: non c'e' niente da cui distinguerlo.
import type { ReactNode } from "react";

import { markdown } from "../markdown";
import { WrittenAt } from "./Stat";

export type SummaryPart = {
  body: string | null;
  writtenAt: string | null;
  refresh?: ReactNode;
};

function Part({
  part,
  day,
  glyph,
  when,
  tone,
}: {
  part: SummaryPart;
  day: string;
  glyph: string;
  when: string;
  tone?: string;
}) {
  if (!part.body) return null;
  return (
    <div className="next-main">
      <span
        className={tone ? `next-icon ${tone}` : "next-icon"}
        aria-hidden="true"
      >
        {glyph}
      </span>
      <div>
        <div className="eyebrow">
          Summary{when && ` · ${when}`}
          {part.refresh}
        </div>
        <div className="next-reason">{markdown(part.body)}</div>
        <WrittenAt when={part.writtenAt} day={day} />
      </div>
    </div>
  );
}

export function SummaryCard({
  morning,
  evening,
  day,
  week,
}: {
  morning: SummaryPart;
  // Senza di lui la card e' un pezzo solo: e' il caso del giorno (todo 66).
  evening?: SummaryPart;
  day: string;
  // Il verdetto della settimana (todo 53): gli stessi due blocchi, e anche
  // qui il primo e' di mattina (il lunedi) e il secondo di sera (la
  // domenica), quindi i due glifi restano il sole e la luna.
  week?: boolean;
}) {
  return (
    <section className="next-card summary-card" aria-label="Summary">
      <Part
        part={morning}
        day={day}
        glyph="☀"
        when={evening ? (week ? "week start" : "morning") : ""}
      />
      {evening && (
        <Part
          part={evening}
          day={day}
          glyph="☾"
          when={week ? "week end" : "evening"}
          tone="moon"
        />
      )}
      {!morning.body && !evening?.body && (
        <div className="next-main">
          <span className="next-icon" aria-hidden="true">
            ≡
          </span>
          <div>
            <div className="eyebrow">Summary</div>
            <p className="next-reason">
              {week ? "No summary for this week." : "No summary for this day."}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
