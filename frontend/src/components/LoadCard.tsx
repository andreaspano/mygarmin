// "Load" (todo 34): il carico di Garmin. Il titolo e' lo stato del carico di
// Garmin detto a parole (la prima frase del report era troppo lunga per un
// titolo), il testo e' la sezione Load del report; il bilancio del lavoro come tre
// barre, con la fascia obiettivo di Garmin quando i file di salute ce
// l'hanno; riposi, ultima seduta dura e VO2max da `/api/daily/{day}`.
import { iconUrl, type DailyData } from "../api/client";
import { shortDayLabel } from "../format";
import { markdown } from "../markdown";

type Row = { key: "load_aerobic_low" | "load_aerobic_high" | "load_anaerobic"; label: string; tone: string };

const ROWS: Row[] = [
  { key: "load_aerobic_low", label: "Low aerobic", tone: "low" },
  { key: "load_aerobic_high", label: "High aerobic", tone: "high" },
  { key: "load_anaerobic", label: "Anaerobic", tone: "anaerobic" },
];

// Lo stato del carico di Garmin (`acwr_status`), come titolo del riquadro.
const STATUS_TITLES: Record<string, string> = {
  LOW: "Below your usual load",
  OPTIMAL: "In a healthy range",
  HIGH: "Above your usual load",
  VERY_HIGH: "Well above your usual load",
};

/** Dove sta il carico rispetto alla fascia obiettivo. */
function targetStatus(value: number, min: number, max: number): string {
  if (value < min) return "short";
  if (value > max) return "above target";
  return "in range";
}

function Balance({ data }: { data: DailyData }) {
  const now = data.load.now;
  if (!now) return null;
  const targets = data.load.targets;
  // Una scala per le tre barre, cosi' si confrontano fra loro.
  const top = Math.max(
    ...ROWS.map((r) => now[r.key] ?? 0),
    ...(targets ? ROWS.map((r) => targets[r.key].max) : [0]),
    1,
  );
  const pct = (v: number) => `${(v / top) * 100}%`;
  return (
    <div className="balance">
      <div className="balance-title">
        Balance of the work
        <span className="muted"> · monthly load{targets ? ", Garmin's target shaded" : ""}</span>
      </div>
      {ROWS.map((r) => {
        const value = now[r.key];
        const target = targets?.[r.key];
        return (
          <div className="balance-row" key={r.key}>
            <div className="balance-label">
              <span className={`swatch ${r.tone}`} />
              {r.label}
            </div>
            <div className="balance-bar" aria-hidden="true">
              {target && (
                <div
                  className="balance-target"
                  style={{ left: pct(target.min), width: pct(target.max - target.min) }}
                />
              )}
              {value != null && <div className={`balance-fill ${r.tone}`} style={{ width: pct(value) }} />}
            </div>
            <div className="balance-value">
              {value != null ? Math.round(value) : "–"}
              {value != null && target && <span className="muted"> {targetStatus(value, target.min, target.max)}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function LoadCard({ data, text, icon }: { data: DailyData; text: string | null; icon: string | null }) {
  const status = data.load.now?.acwr_status;
  const title = (status && STATUS_TITLES[status]) ?? "Load";
  const recent = data.recent;
  const vo2 = data.load.vo2max_change;
  return (
    <section className="card load-card" aria-label="Load">
      <div className="block-head">
        {icon && <img src={iconUrl(icon)} alt="" width={22} height={22} />}
        <span>Load</span>
      </div>
      <h2>{title}</h2>
      {text && <div className="prose">{markdown(text)}</div>}
      <Balance data={data} />
      <div className="load-facts">
        <div className="stat">
          <div className="stat-label">Rest days, last 7</div>
          <div className="stat-value">{recent.rest_days_last_7}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Last hard session</div>
          <div className="stat-value small">
            {recent.last_hard_session_before_today ? shortDayLabel(recent.last_hard_session_before_today) : "–"}
          </div>
          {recent.days_since_last_hard_session_before_today != null && (
            <div className="stat-sub">{recent.days_since_last_hard_session_before_today} days before</div>
          )}
        </div>
      </div>
      {vo2 && (
        <div className="stat vo2">
          <div className="stat-label">VO2max</div>
          <div className="stat-value">
            {vo2.now.toFixed(1)}
            <span className={vo2.change >= 0 ? "delta up" : "delta down"}>
              {vo2.change >= 0 ? "+" : ""}
              {vo2.change.toFixed(1)} in 28 days
            </span>
          </div>
          <div className="stat-sub">From {vo2.days_ago_28.toFixed(1)} four weeks ago</div>
        </div>
      )}
    </section>
  );
}
