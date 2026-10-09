// Il Markdown dei report in elementi React, e le sezioni del report
// giornaliero divise per riquadro (todo 34).
//
// I report usano solo paragrafi, elenchi e grassetto/corsivo: bastano poche
// righe di conversione, senza una libreria in piu' e senza
// `dangerouslySetInnerHTML`.
import type { ReactNode } from "react";

import type { Report } from "./api/client";

/** Grassetto (`**...**`), corsivo (`*...*` o `_..._`) e codice (`` `...` ``)
 * dentro una riga. Il resto resta testo. */
export function inline(text: string): ReactNode[] {
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

/** I blocchi del testo, separati da righe vuote. */
function blocks(body: string): string[] {
  return body.split(/\n\s*\n/).filter((b) => b.trim());
}

/** Le voci di un blocco elenco: una riga che non inizia con il segno
 * continua la voce prima. `null` se il blocco non e' un elenco. */
function listItems(block: string): { ordered: boolean; items: string[] } | null {
  const lines = block.split("\n");
  const marker = BULLET.test(lines[0]) ? BULLET : NUMBERED.test(lines[0]) ? NUMBERED : null;
  if (!marker) return null;
  const items: string[] = [];
  for (const line of lines) {
    if (marker.test(line)) items.push(line.replace(marker, ""));
    else items[items.length - 1] += ` ${line.trim()}`;
  }
  return { ordered: marker === NUMBERED, items };
}

/** Il testo come paragrafi ed elenchi. */
export function markdown(body: string): ReactNode[] {
  return blocks(body).map((block, i) => {
    const list = listItems(block);
    if (!list) return <p key={i}>{inline(block.split("\n").join(" "))}</p>;
    const children = list.items.map((item, j) => <li key={j}>{inline(item)}</li>);
    return list.ordered ? <ol key={i}>{children}</ol> : <ul key={i}>{children}</ul>;
  });
}

/** Il corpo della sezione `title` del report, o `null`. */
export function sectionBody(report: Report | null, title: string): string | null {
  return report?.sections.find((s) => s.title?.toLowerCase() === title.toLowerCase())?.body ?? null;
}

/** Il testo prima della prima sezione ("Data: local cache, ..."). */
export function preamble(report: Report | null): string | null {
  return report?.sections.find((s) => s.title == null)?.body ?? null;
}

export type NextParts = { title: string | null; reason: string; steps: string[] };

/** La sezione Next nel formato del todo 34: un titolo in grassetto da solo
 * sulla prima riga, il perche', i passi della seduta come elenco. I report
 * vecchi non hanno ne' titolo ne' elenco: tutto resta nel perche'. */
export function nextParts(body: string): NextParts {
  const parts = blocks(body);
  let title: string | null = null;
  const titleMatch = parts[0]?.trim().match(/^\*\*([^*]+)\*\*$/);
  if (titleMatch) {
    title = titleMatch[1].trim();
    parts.shift();
  }
  const steps: string[] = [];
  const reason: string[] = [];
  for (const block of parts) {
    const list = listItems(block);
    if (list) steps.push(...list.items);
    else reason.push(block);
  }
  return { title, reason: reason.join("\n\n"), steps };
}

/** L'icona della sezione `title` del report (il nome lo da' l'API), o
 * `null`. */
export function sectionIcon(report: Report | null, title: string): string | null {
  return report?.sections.find((s) => s.title?.toLowerCase() === title.toLowerCase())?.icon ?? null;
}
