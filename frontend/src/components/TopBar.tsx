// La barra in alto (todo 34): il nome dell'app e le pagine. C'e' solo la
// Day: le altre si vedono, disattivate, per dare la forma della barra.
// "Profile" non c'e' finche' non c'e' il login.
const PAGES = ["Day", "Week", "Month", "Recovery", "Activities"];

export function TopBar() {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <span className="brand">Training</span>
        <nav aria-label="Pages">
          {PAGES.map((page) =>
            page === "Day" ? (
              <a key={page} className="tab active" href="?" aria-current="page">
                {page}
              </a>
            ) : (
              <span key={page} className="tab disabled" aria-disabled="true" title="Coming soon">
                {page}
              </span>
            ),
          )}
        </nav>
      </div>
    </header>
  );
}
