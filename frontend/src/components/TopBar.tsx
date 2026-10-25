// La barra in alto (todo 34): il nome dell'app e le pagine. Dal todo 51 la
// Day e la Week sono collegamenti veri; Month e Activities si
// vedono ancora disattivate, per dare la forma della barra. "Profile" non
// c'e' finche' non c'e' il login.
import { hrefFor, type Page } from "../navigation";

const PRONTE: { page: Page; label: string }[] = [
  { page: "day", label: "Day" },
  { page: "week", label: "Week" },
];
const DA_FARE = ["Month", "Activities"];

export function TopBar({ current = "day" }: { current?: Page }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <span className="brand">Training</span>
        <nav aria-label="Pages">
          {PRONTE.map(({ page, label }) => (
            <a
              key={page}
              className={page === current ? "tab active" : "tab"}
              href={hrefFor(page)}
              aria-current={page === current ? "page" : undefined}
            >
              {label}
            </a>
          ))}
          {DA_FARE.map((label) => (
            <span key={label} className="tab disabled" aria-disabled="true" title="Coming soon">
              {label}
            </span>
          ))}
        </nav>
      </div>
    </header>
  );
}
