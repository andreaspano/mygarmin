// Il report giornaliero del giorno scelto, come `report_view.show_report`:
// le sezioni con l'icona accanto al titolo, su fondo grigio.
//
// Il testo e' Markdown, ma i report usano solo paragrafi, elenchi e
// grassetto/corsivo: bastano poche righe di conversione in elementi React,
// senza una libreria in piu' e senza `dangerouslySetInnerHTML`.
import type { ReactNode } from "react";

import { iconUrl, type Report } from "../api/client";

/** Grassetto (`**...**`), corsivo (`*...*` o `_..._`) e codice (`` `...` ``)
 * dentro una riga. Il resto resta testo. */
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const pattern = /\*\*(.+?)\*\*|`([^`]+)`|\*([^*\s][^*]*?)\*|\b_([^_]+?)_\b/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    const at = match.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    const key = out.length;
    if (match[1] != null) out.push(<strong key={key}>{inline(match[1])}</strong>);
    else if (match[2] != null) out.push(<code key={key}>{match[2]}</code>);
    else out.push(<em key={key}>{inline(match[3] ?? match[4] ?? "")}</em>);
    last = at + match[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const BULLET = /^\s*[-*+]\s+/;
const NUMBERED = /^\s*\d+\.\s+/;

/** Blocchi separati da righe vuote; un blocco di righe che iniziano con "- "
 * (o "1. ") e' un elenco, una riga che non inizia cosi' continua la voce
 * prima. Il resto e' un paragrafo. */
function markdown(body: string): ReactNode[] {
  const blocks = body.split(/\n\s*\n/).filter((b) => b.trim());
  return blocks.map((block, i) => {
    const lines = block.split("\n");
    const kind = BULLET.test(lines[0]) ? "ul" : NUMBERED.test(lines[0]) ? "ol" : "p";
    if (kind === "p") return <p key={i}>{inline(lines.join(" "))}</p>;
    const marker = kind === "ul" ? BULLET : NUMBERED;
    const items: string[] = [];
    for (const line of lines) {
      if (marker.test(line)) items.push(line.replace(marker, ""));
      else items[items.length - 1] += ` ${line.trim()}`;
    }
    const children = items.map((item, j) => <li key={j}>{inline(item)}</li>);
    return kind === "ul" ? <ul key={i}>{children}</ul> : <ol key={i}>{children}</ol>;
  });
}

export function DailyReport({ report, loading }: { report: Report | null; loading: boolean }) {
  if (loading) return <p className="caption">Loading the daily report…</p>;
  if (!report) return <p className="caption">No daily report for this day.</p>;
  return (
    <div className="report">
      {report.sections.map((section, i) => (
        <section key={i}>
          {section.title && (
            <div className="report-head">
              {section.icon && <img src={iconUrl(section.icon)} alt="" width={28} height={28} />}
              <strong>{section.title}</strong>
            </div>
          )}
          {markdown(section.body)}
        </section>
      ))}
    </div>
  );
}
