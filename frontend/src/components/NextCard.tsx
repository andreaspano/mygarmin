// Il riquadro scuro "Next" (todo 34): cosa fare dopo, dalla sezione Next del
// report. Il titolo e i passi della seduta (i chip) ci sono solo nei report
// scritti col formato nuovo; i vecchi mostrano il testo com'e'.
import { inline, markdown, nextParts } from "../markdown";

export function NextCard({ body, tomorrow }: { body: string | null; tomorrow: boolean }) {
  const parts = body ? nextParts(body) : null;
  return (
    <section className="next-card" aria-label="Next session">
      <div className="next-main">
        <span className="next-icon" aria-hidden="true">
          →
        </span>
        <div>
          <div className="eyebrow">Next · {tomorrow ? "tomorrow" : "today"}</div>
          <h2>{parts?.title ? inline(parts.title) : "Next"}</h2>
          {parts ? (
            <div className="next-reason">{markdown(parts.reason)}</div>
          ) : (
            <p className="next-reason">No daily report for this day.</p>
          )}
        </div>
      </div>
      {parts && parts.steps.length > 0 && (
        <div className="next-session">
          <div className="next-session-label">Example session</div>
          <ul className="chips">
            {parts.steps.map((step, i) => (
              <li key={i}>{inline(step)}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
