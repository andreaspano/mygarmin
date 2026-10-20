// Il riquadro "Summary", accanto a Next: lo stesso fondo scuro, un accento
// suo (viola, contro l'arancio di Next) perche' i due si leggano come una
// coppia e non come la stessa cosa. Cosa ci va dentro lo decide Andrea: per
// ora il riquadro c'e' e aspetta il testo.
export function SummaryCard({ body }: { body: string | null }) {
  return (
    <section className="next-card summary-card" aria-label="Summary">
      <div className="next-main">
        <span className="next-icon" aria-hidden="true">
          ≡
        </span>
        <div>
          <div className="eyebrow">Summary</div>
          {body ? (
            <div className="next-reason">{body}</div>
          ) : (
            <p className="next-reason">Nothing here yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}
