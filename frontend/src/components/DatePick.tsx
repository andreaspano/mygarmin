// Il calendario delle intestazioni: l'icona sola, senza scritta, con sopra
// un `input[type=date]` che copre tutto il riquadro — il nome del campo lo
// da' il suo `aria-label`. Lo usano la Day, dove la data scelta e' il
// giorno da aprire, e la Week, dove e' un giorno qualunque della settimana
// da aprire (todo 51).

/** `onPick` riceve la data scelta, mai vuota e mai oltre `max`. */
export function DatePick({
  value,
  max,
  onPick,
  label,
}: {
  value: string;
  max: string;
  onPick: (day: string) => void;
  label: string;
}) {
  return (
    <label className="btn icon-btn date-pick" title={label}>
      <svg aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">
        <rect
          x="1.5"
          y="3"
          width="13"
          height="11.5"
          rx="2"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <path
          d="M1.5 7h13M5 1.5v3M11 1.5v3"
          stroke="currentColor"
          strokeWidth="1.5"
        />
      </svg>
      <input
        type="date"
        value={value}
        max={max}
        onChange={(e) =>
          e.target.value && e.target.value <= max && onPick(e.target.value)
        }
        aria-label={label}
      />
    </label>
  );
}
