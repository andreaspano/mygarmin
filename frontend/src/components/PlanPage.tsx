// La pagina Plan: i piani di allenamento scritti a mano in `plan/`.
//
// Gli altri piani del repo guardano indietro — il report di un giorno, quello
// di una settimana — questo guarda avanti: una gara, un bersaglio e le
// settimane che ci portano. Per questo non sta fra Day e Week nella barra ma
// a destra, accanto ad Activities.
//
// La pagina non sa niente dei piani: li chiede all'API (`/api/plans`), che
// legge la cartella. Un file nuovo in `plan/` si vede ricaricando, senza
// toccare niente qui — e' il motivo per cui i numeri in cima stanno nel front
// matter del file e non nel codice.
//
// Il piano aperto sta nell'URL (`?period=plan&plan=half_marathon_2.20`), come
// il giorno nella Day: un piano si apre da un link e il tasto indietro torna
// a quello di prima.
import { useEffect, useState } from "react";

import {
  api,
  isAbort,
  type Plan,
  type PlanSummary,
} from "../api/client";
import { dayDiff, raceLabel, shortDayLabel, targetLabel, today } from "../format";
import { markdown } from "../markdown";
import { paramFromUrl, pushUrl } from "../navigation";
import { CardHead, Stat, WrittenAt, num } from "./Stat";
import { TopBar } from "./TopBar";

const API_DOWN = "Cannot reach the API. Is it running (make api)?";
// L'icona di Next: il riquadro che dice cosa fare dopo. Un piano e' la stessa
// domanda, solo su quattro mesi invece che su domani.
const PLAN_ICON = "next.png";

/** Il piano scelto: quello dell'URL se c'e' ancora fra i file, se no il
 * primo, cioe' quello della gara piu' vicina. */
function chosen(plans: PlanSummary[]): string | null {
  const wanted = paramFromUrl("plan");
  if (wanted && plans.some((p) => p.slug === wanted)) return wanted;
  return plans[0]?.slug ?? null;
}

/** Il selettore: un bottone per piano, col bersaglio grande e sotto il ritmo
 * e la gara. Fra piani della stessa gara il bersaglio e' l'unica cosa che li
 * distingue, ed e' per questo che sta nel numero grande. */
function PlanPicker({
  plans,
  slug,
  onSelect,
}: {
  plans: PlanSummary[];
  slug: string | null;
  onSelect: (slug: string) => void;
}) {
  if (plans.length < 2) return null;
  return (
    <nav className="week-strip" aria-label="Plans">
      {plans.map((plan) => {
        const picked = plan.slug === slug;
        return (
          <button
            type="button"
            key={plan.slug}
            className={picked ? "strip-plan selected" : "strip-plan"}
            onClick={() => onSelect(plan.slug)}
            aria-current={picked ? "page" : undefined}
            title={plan.title}
          >
            <span className="strip-number">{targetLabel(plan.target_time)}</span>
            <span className="strip-dates">
              {plan.target_pace ? `${plan.target_pace} /km` : plan.file}
              <br />
              {plan.race ? raceLabel(plan.race) : "no race day"}
            </span>
          </button>
        );
      })}
    </nav>
  );
}

/** I numeri del piano, sopra il testo: la gara, quanto manca, il bersaglio.
 * Quelli che il front matter non ha restano un trattino, come in tutte le
 * altre pagine. */
function PlanStats({ plan, now }: { plan: Plan; now: string }) {
  const toGo = plan.race ? dayDiff(now, plan.race) : null;
  const from = plan.block_start;
  return (
    <div className="stats">
      <Stat
        label="Race"
        value={plan.race ? raceLabel(plan.race) : "–"}
        sub={plan.race_name ? <span className="muted">{plan.race_name}</span> : undefined}
      />
      <Stat
        label={toGo != null && toGo < 0 ? "Days since" : "Days to go"}
        value={toGo == null ? "–" : Math.abs(toGo)}
        sub={
          plan.weeks != null ? (
            <span className="muted">
              {plan.weeks} weeks{from ? ` from ${shortDayLabel(from)}` : ""}
            </span>
          ) : undefined
        }
      />
      <Stat label="Target" value={targetLabel(plan.target_time)} />
      <Stat label="Pace" value={plan.target_pace ?? "–"} unit={plan.target_pace ? "/km" : undefined} />
      <Stat label="Speed" value={num(plan.target_speed_kmh, 2)} unit="km/h" />
      <Stat label="Peak week" value={num(plan.peak_weekly_km)} unit="km" />
    </div>
  );
}

export function PlanPage() {
  const now = today();
  const [plans, setPlans] = useState<PlanSummary[] | null>(null);
  const [slug, setSlug] = useState<string | null>(() => paramFromUrl("plan"));
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  const open = (next: string) => {
    if (next === slug) return;
    pushUrl({ period: "plan", page: null, view: null, plan: next });
    setSlug(next);
  };

  useEffect(() => {
    const onPop = () => setSlug(paramFromUrl("plan"));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // L'elenco dei piani. Da qui esce anche il piano da aprire quando l'URL non
  // ne chiede uno, o ne chiede uno che non c'e' piu'.
  useEffect(() => {
    const controller = new AbortController();
    api
      .plans(controller.signal)
      .then((list) => {
        setPlans(list.plans);
        setError(null);
        setSlug((current) =>
          current && list.plans.some((p) => p.slug === current) ? current : chosen(list.plans),
        );
      })
      .catch((e) => !isAbort(e) && setError(API_DOWN));
    return () => controller.abort();
  }, []);

  // Il testo del piano scelto.
  useEffect(() => {
    if (!slug) return;
    const controller = new AbortController();
    setPlan(null);
    api
      .plan(slug, controller.signal)
      .then(setPlan)
      .catch((e) => !isAbort(e) && setError(API_DOWN));
    return () => controller.abort();
  }, [slug]);

  useEffect(() => {
    document.title = plan ? `Training · ${plan.title}` : "Training · Plan";
  }, [plan]);

  const empty = plans !== null && plans.length === 0;

  return (
    <>
      <TopBar current="plan" />
      <main className="page">
        <div className="day-header">
          <div className="day-title">
            <h1>{plan?.title ?? "Plan"}</h1>
          </div>
        </div>
        {error && <p className="warning">{error}</p>}
        {empty && (
          <p className="info">
            No plans yet. A plan is a Markdown file in <code>plan/</code>: a YAML front
            matter with the race and the target, then the text.
          </p>
        )}
        <PlanPicker plans={plans ?? []} slug={slug} onSelect={open} />
        {plan && (
          <section className="card plan-card" aria-label="Plan">
            <CardHead icon={PLAN_ICON} title="Plan" />
            <PlanStats plan={plan} now={now} />
            <div className="prose plan-prose">{markdown(plan.body)}</div>
            <p className="caption plan-file">plan/{plan.file}</p>
            <WrittenAt when={plan.written_at} day={plan.race ?? ""} />
          </section>
        )}
      </main>
    </>
  );
}
