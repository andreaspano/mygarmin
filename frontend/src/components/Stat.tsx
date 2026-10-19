// Un numero con etichetta, unita' e riga sotto: lo usano Recovery, Health e
// Fitness (todo 37, prima stava in "This morning").
import type { ReactNode } from "react";

import { iconUrl } from "../api/client";

export function num(value: number | null | undefined, digits = 0): string {
  return value == null ? "–" : value.toFixed(digits);
}

export function Stat({
  label,
  value,
  unit,
  sub,
  help,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  sub?: ReactNode;
  /** La spiegazione nel tooltip del riquadro. */
  help?: string;
}) {
  return (
    <div className="stat" title={help}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {value}
        {unit && <span className="stat-unit"> {unit}</span>}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

/** Il titolo piccolo di un riquadro, con l'icona della sua sezione del report. */
export function CardHead({ icon, title }: { icon: string | null; title: string }) {
  return (
    <div className="block-head">
      {icon && <img src={iconUrl(icon)} alt="" width={22} height={22} />}
      <span>{title}</span>
    </div>
  );
}
