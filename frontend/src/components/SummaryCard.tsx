// Il riquadro "Summary", accanto a Next: lo stesso fondo scuro, un accento
// suo (viola, contro l'arancio di Next) perche' i due si leggano come una
// coppia e non come la stessa cosa.
//
// Dal todo 49 il verdetto del giorno e' in due pezzi: il sole lo scrive il
// giro del mattino, la luna quello della sera. La mattina si vede solo il
// sole — la luna non esiste ancora, e non serve nessuna regola sull'orario
// per saperlo: basta mostrare quello che c'e'.
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
      <span className={tone ? `next-icon ${tone}` : "next-icon"} aria-hidden="true">
        {glyph}
      </span>
      <div>
        <div className="eyebrow">
          Summary · {when}
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
}: {
  morning: SummaryPart;
  evening: SummaryPart;
  day: string;
}) {
  return (
    <section className="next-card summary-card" aria-label="Summary">
      <Part part={morning} day={day} glyph="☀" when="morning" />
      <Part part={evening} day={day} glyph="☾" when="evening" tone="moon" />
      {!morning.body && !evening.body && (
        <div className="next-main">
          <span className="next-icon" aria-hidden="true">
            ≡
          </span>
          <div>
            <div className="eyebrow">Summary</div>
            <p className="next-reason">No summary for this day.</p>
          </div>
        </div>
      )}
    </section>
  );
}
