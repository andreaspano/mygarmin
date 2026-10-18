// I segnali d'allarme (todo 37): prima nel titolo di "This morning", ora in
// una riga sopra la griglia, perche' riguardano sia Recovery sia Health.
import type { DailyData } from "../api/client";

export function Alerts({ alerts }: { alerts: DailyData["alerts"] }) {
  return (
    <div className="alerts-row">
      {alerts.length === 0 ? (
        <span className="badge ok">✓ No warning signs</span>
      ) : (
        <span className="badge warn" title={alerts.map((a) => a.detail).join("\n")}>
          {alerts.length === 1 ? "1 warning sign" : `${alerts.length} warning signs`}
        </span>
      )}
      {alerts.length > 0 && (
        <ul className="alerts">
          {alerts.map((a) => (
            <li key={a.kind}>{a.detail}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
