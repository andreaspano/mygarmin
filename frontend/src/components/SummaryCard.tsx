// Il riquadro "Summary", accanto a Next: lo stesso fondo scuro, un accento
// suo (viola, contro l'arancio di Next) perche' i due si leggano come una
// coppia e non come la stessa cosa. Dentro c'e' la sezione Summary del
// report, il verdetto sulla salute in una frase sola.
import type { ReactNode } from "react";

import { markdown } from "../markdown";

export function SummaryCard({ body, refresh }: { body: string | null; refresh?: ReactNode }) {
  return (
    <section className="next-card summary-card" aria-label="Summary">
      <div className="next-main">
        <span className="next-icon" aria-hidden="true">
          ≡
        </span>
        <div>
          <div className="eyebrow">
            Summary
            {refresh}
          </div>
          {body ? (
            <div className="next-reason">{markdown(body)}</div>
          ) : (
            <p className="next-reason">No summary for this day.</p>
          )}
        </div>
      </div>
    </section>
  );
}
