// I filtri della Day: sport (scelta multipla, "All" se vuota) e le date
// "From" / "To", come nella pagina Streamlit.
import { useEffect, useRef, useState } from "react";

import type { Sport } from "../api/client";

type Props = {
  sports: Sport[];
  selectedSports: string[];
  onSportsChange: (sports: string[]) => void;
  start: string;
  end: string;
  maxDay: string;
  onStartChange: (day: string) => void;
  onEndChange: (day: string) => void;
};

export function Filters(props: Props) {
  return (
    <div className="filters">
      <SportPicker sports={props.sports} selected={props.selectedSports} onChange={props.onSportsChange} />
      <label className="field">
        <span>From</span>
        <input
          type="date"
          value={props.start}
          max={props.maxDay}
          onChange={(e) => e.target.value && props.onStartChange(e.target.value)}
        />
      </label>
      <label className="field">
        <span>To</span>
        <input
          type="date"
          value={props.end}
          max={props.maxDay}
          onChange={(e) => e.target.value && props.onEndChange(e.target.value)}
        />
      </label>
    </div>
  );
}

function SportPicker({
  sports,
  selected,
  onChange,
}: {
  sports: Sport[];
  selected: string[];
  onChange: (sports: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  // Un click fuori, o Esc, chiude l'elenco.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const labels = sports.filter((s) => selected.includes(s.sport)).map((s) => s.label);
  const toggle = (sport: string) =>
    onChange(selected.includes(sport) ? selected.filter((s) => s !== sport) : [...selected, sport]);

  return (
    <div className="field sport-picker" ref={box}>
      <span id="sport-label">Sport</span>
      <button
        type="button"
        className="picker-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-labelledby="sport-label"
        onClick={() => setOpen(!open)}
      >
        <span className={labels.length ? "" : "placeholder"}>{labels.length ? labels.join(", ") : "All"}</span>
        <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="picker-list" role="listbox" aria-multiselectable="true">
          {sports.map((s) => (
            <label key={s.sport} className="picker-option">
              <input type="checkbox" checked={selected.includes(s.sport)} onChange={() => toggle(s.sport)} />
              {s.label}
            </label>
          ))}
          {selected.length > 0 && (
            <button type="button" className="picker-clear" onClick={() => onChange([])}>
              Clear
            </button>
          )}
        </div>
      )}
    </div>
  );
}
