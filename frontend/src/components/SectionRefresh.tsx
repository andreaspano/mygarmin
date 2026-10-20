// Il tasto che rifa' una sola sezione del report (todo 44): gira il suo
// agente e lascia le altre com'erano. Stessa icona del Refresh generale,
// piu' piccola, in fondo all'intestazione della card; mentre il suo agente
// lavora ruota e non si clicca.
import type { SectionRefresh as Status } from "../api/client";

export function SectionRefresh({
  section,
  state,
  onRefresh,
}: {
  section: string;
  state: Status | undefined;
  onRefresh: (section: string) => void;
}) {
  const running = state?.status === "running";
  const failed = state?.status === "failed";
  const label = running
    ? `Rewriting the ${section} section…`
    : failed
      ? `The ${section} section failed and kept its text: ${state?.message ?? ""}`
      : `Rewrite the ${section} section`;
  return (
    <button
      type="button"
      className={failed ? "section-refresh failed" : "section-refresh"}
      onClick={() => onRefresh(section)}
      disabled={running}
      aria-busy={running}
      aria-label={label}
      title={label}
    >
      <svg aria-hidden="true" viewBox="0 0 16 16" width="12" height="12">
        <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <path d="M12.5 1.5v3h-3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}
